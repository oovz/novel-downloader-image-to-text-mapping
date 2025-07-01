"""
域名配置模块

定义各个网站域名的图片下载配置，包括URL模式、请求头、限流等设置。
支持扩展新的域名配置。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from urllib.parse import urljoin

from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class DomainConfig:
    """
    域名配置数据类
    """
    domain: str
    image_url_pattern: str
    headers: Dict[str, str] = field(default_factory=dict)
    rate_limit_delay: float = 1.0  # 请求间隔秒数
    max_retries: int = 3
    timeout: int = 30
    referrer_required: bool = False
    user_agent: Optional[str] = None
    
    def __post_init__(self):
        """初始化后处理"""
        if self.user_agent is None:
            self.user_agent = (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/91.0.4472.124 Safari/537.36"
            )
        
        # 设置默认请求头
        if 'User-Agent' not in self.headers:
            self.headers['User-Agent'] = self.user_agent
            
        if self.referrer_required and 'Referer' not in self.headers:
            self.headers['Referer'] = f"https://{self.domain}/"
    
    def build_image_url(self, filename: str) -> str:
        """
        根据文件名构建完整的图片URL
        
        Args:
            filename: 图片文件名
            
        Returns:
            str: 完整的图片URL
        """
        try:
            # 如果模式包含占位符，替换文件名
            if '{filename}' in self.image_url_pattern:
                url = self.image_url_pattern.format(filename=filename)
            else:
                # 否则直接拼接
                url = urljoin(self.image_url_pattern, filename)
            
            logger.debug(f"构建图片URL: {filename} -> {url}")
            return url
            
        except Exception as e:
            logger.error(f"构建图片URL失败 {filename}: {e}")
            return ""
    
    def get_request_headers(self, image_url: str = "") -> Dict[str, str]:
        """
        获取请求头
        
        Args:
            image_url: 图片URL（用于动态设置Referer）
            
        Returns:
            Dict[str, str]: 请求头字典
        """
        headers = self.headers.copy()
        
        # 如果需要Referer但未设置，使用域名主页
        if self.referrer_required and 'Referer' not in headers:
            headers['Referer'] = f"https://{self.domain}/"
        
        return headers


# 预定义的域名配置
DOMAIN_CONFIGS: Dict[str, DomainConfig] = {
    'www.xiguashuwu.com': DomainConfig(
        domain='www.xiguashuwu.com',
        image_url_pattern='https://www.xiguashuwu.com/wzbodyimg/{filename}',
        headers={
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
        },
        rate_limit_delay=1.5,
        max_retries=3,
        timeout=30,
        referrer_required=True
    ),
    
    # 示例配置 - 可以根据实际需要添加更多域名
    'example.com': DomainConfig(
        domain='example.com',
        image_url_pattern='https://example.com/static/images/{filename}',
        headers={
            'Accept': 'image/*',
        },
        rate_limit_delay=0.5,
        max_retries=2,
        timeout=20,
        referrer_required=False
    )
}


def get_domain_config(domain: str) -> Optional[DomainConfig]:
    """
    获取指定域名的配置
    
    Args:
        domain: 域名
        
    Returns:
        DomainConfig: 域名配置，未找到返回None
    """
    config = DOMAIN_CONFIGS.get(domain)
    if config:
        logger.debug(f"获取域名配置: {domain}")
    else:
        logger.warning(f"未找到域名配置: {domain}")
    return config


def register_domain_config(config: DomainConfig) -> bool:
    """
    注册新的域名配置
    
    Args:
        config: 域名配置
        
    Returns:
        bool: 注册成功返回True
    """
    try:
        if not config.domain:
            logger.error("域名不能为空")
            return False
            
        if not config.image_url_pattern:
            logger.error("图片URL模式不能为空")
            return False
            
        DOMAIN_CONFIGS[config.domain] = config
        logger.info(f"已注册域名配置: {config.domain}")
        return True
        
    except Exception as e:
        logger.error(f"注册域名配置失败: {e}")
        return False


def get_all_domains() -> List[str]:
    """
    获取所有已配置的域名列表
    
    Returns:
        List[str]: 域名列表
    """
    domains = list(DOMAIN_CONFIGS.keys())
    logger.debug(f"获取所有域名: {domains}")
    return domains


def validate_domain_config(config: DomainConfig) -> List[str]:
    """
    验证域名配置
    
    Args:
        config: 要验证的域名配置
        
    Returns:
        List[str]: 验证错误列表，空列表表示验证通过
    """
    errors = []
    
    try:
        # 验证必填字段
        if not config.domain:
            errors.append("域名不能为空")
            
        if not config.image_url_pattern:
            errors.append("图片URL模式不能为空")
        
        # 验证URL模式格式
        if config.image_url_pattern and not (
            config.image_url_pattern.startswith('http://') or 
            config.image_url_pattern.startswith('https://')
        ):
            errors.append("图片URL模式必须以http://或https://开头")
        
        # 验证数值范围
        if config.rate_limit_delay < 0:
            errors.append("限流延迟不能为负数")
            
        if config.max_retries < 0:
            errors.append("最大重试次数不能为负数")
            
        if config.timeout <= 0:
            errors.append("超时时间必须大于0")
        
        # 验证请求头格式
        if config.headers:
            for key, value in config.headers.items():
                if not isinstance(key, str) or not isinstance(value, str):
                    errors.append(f"请求头格式错误: {key}={value}")
        
        if errors:
            logger.warning(f"域名配置验证失败 {config.domain}: {errors}")
        else:
            logger.debug(f"域名配置验证通过: {config.domain}")
            
    except Exception as e:
        errors.append(f"配置验证异常: {e}")
        logger.error(f"域名配置验证异常: {e}")
    
    return errors


def create_domain_config_from_dict(domain: str, config_dict: Dict) -> Optional[DomainConfig]:
    """
    从字典创建域名配置
    
    Args:
        domain: 域名
        config_dict: 配置字典
        
    Returns:
        DomainConfig: 域名配置对象，创建失败返回None
    """
    try:
        config = DomainConfig(
            domain=domain,
            image_url_pattern=config_dict.get('image_url_pattern', ''),
            headers=config_dict.get('headers', {}),
            rate_limit_delay=config_dict.get('rate_limit_delay', 1.0),
            max_retries=config_dict.get('max_retries', 3),
            timeout=config_dict.get('timeout', 30),
            referrer_required=config_dict.get('referrer_required', False),
            user_agent=config_dict.get('user_agent')
        )
        
        # 验证配置
        errors = validate_domain_config(config)
        if errors:
            logger.error(f"从字典创建域名配置失败 {domain}: {errors}")
            return None
            
        logger.debug(f"从字典创建域名配置成功: {domain}")
        return config
        
    except Exception as e:
        logger.error(f"从字典创建域名配置异常 {domain}: {e}")
        return None


def load_domain_configs_from_file(file_path: str) -> bool:
    """
    从JSON文件加载域名配置
    
    Args:
        file_path: 配置文件路径
        
    Returns:
        bool: 加载成功返回True
    """
    try:
        from ..utils.file_utils import read_json_file
        
        config_data = read_json_file(file_path)
        if not config_data:
            logger.error(f"读取域名配置文件失败: {file_path}")
            return False
        
        loaded_count = 0
        for domain, config_dict in config_data.items():
            config = create_domain_config_from_dict(domain, config_dict)
            if config and register_domain_config(config):
                loaded_count += 1
        
        logger.info(f"从文件加载域名配置完成: {file_path}, 成功加载 {loaded_count} 个配置")
        return loaded_count > 0
        
    except Exception as e:
        logger.error(f"从文件加载域名配置失败 {file_path}: {e}")
        return False


def save_domain_configs_to_file(file_path: str, domains: Optional[List[str]] = None) -> bool:
    """
    保存域名配置到JSON文件
    
    Args:
        file_path: 目标文件路径
        domains: 要保存的域名列表，None表示保存所有
        
    Returns:
        bool: 保存成功返回True
    """
    try:
        from ..utils.file_utils import write_json_file
        
        if domains is None:
            domains = get_all_domains()
        
        config_data = {}
        for domain in domains:
            config = get_domain_config(domain)
            if config:
                config_data[domain] = {
                    'image_url_pattern': config.image_url_pattern,
                    'headers': config.headers,
                    'rate_limit_delay': config.rate_limit_delay,
                    'max_retries': config.max_retries,
                    'timeout': config.timeout,
                    'referrer_required': config.referrer_required,
                    'user_agent': config.user_agent
                }
        
        success = write_json_file(file_path, config_data)
        if success:
            logger.info(f"域名配置已保存到文件: {file_path}, 包含 {len(config_data)} 个配置")
        else:
            logger.error(f"保存域名配置到文件失败: {file_path}")
            
        return success
        
    except Exception as e:
        logger.error(f"保存域名配置到文件异常 {file_path}: {e}")
        return False

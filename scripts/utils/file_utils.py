"""
文件工具模块

提供标准化的文件操作功能，包括JSON文件读写、目录管理和路径验证。
支持UTF-8编码，专门处理包含中文字符的JSON文件。
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional, Union

from .logger import get_logger

logger = get_logger(__name__)


def ensure_directory(path: Union[str, Path]) -> bool:
    """
    确保目录存在，如果不存在则创建
    
    Args:
        path: 目录路径
        
    Returns:
        bool: 创建成功返回True，失败返回False
    """
    try:
        path_obj = Path(path)
        path_obj.mkdir(parents=True, exist_ok=True)
        logger.debug(f"目录已确保存在: {path_obj}")
        return True
    except Exception as e:
        logger.error(f"创建目录失败 {path}: {e}")
        return False


def read_json_file(file_path: Union[str, Path]) -> Optional[Dict[str, Any]]:
    """
    读取JSON文件
    
    Args:
        file_path: JSON文件路径
        
    Returns:
        Dict[str, Any]: JSON数据，读取失败返回None
    """
    try:
        path_obj = Path(file_path)
        
        if not path_obj.exists():
            logger.error(f"文件不存在: {file_path}")
            return None
            
        if not path_obj.is_file():
            logger.error(f"路径不是文件: {file_path}")
            return None
            
        with open(path_obj, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        logger.debug(f"成功读取JSON文件: {file_path} (包含 {len(data)} 项)")
        return data
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON解析错误 {file_path}: {e}")
        return None
    except Exception as e:
        logger.error(f"读取文件失败 {file_path}: {e}")
        return None


def write_json_file(file_path: Union[str, Path], data: Dict[str, Any], 
                   indent: Optional[int] = 2, ensure_ascii: bool = False) -> bool:
    """
    写入JSON文件
    
    Args:
        file_path: 目标文件路径
        data: 要写入的JSON数据
        indent: 缩进空格数，None表示压缩格式
        ensure_ascii: 是否转义非ASCII字符
        
    Returns:
        bool: 写入成功返回True，失败返回False
    """
    try:
        path_obj = Path(file_path)
        
        # 确保目录存在
        if not ensure_directory(path_obj.parent):
            return False
            
        # 原子写入：先写入临时文件，再重命名
        temp_path = path_obj.with_suffix(path_obj.suffix + '.tmp')
        
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=ensure_ascii, 
                     separators=(',', ': ') if indent else (',', ':'))
            
        # 重命名临时文件
        temp_path.replace(path_obj)
        
        logger.debug(f"成功写入JSON文件: {file_path} (包含 {len(data)} 项)")
        return True
        
    except Exception as e:
        logger.error(f"写入文件失败 {file_path}: {e}")
        # 清理临时文件
        temp_path = Path(file_path).with_suffix(Path(file_path).suffix + '.tmp')
        if temp_path.exists():
            try:
                temp_path.unlink()
            except:
                pass
        return False


def validate_file_path(file_path: Union[str, Path], 
                      must_exist: bool = True) -> bool:
    """
    验证文件路径
    
    Args:
        file_path: 要验证的文件路径
        must_exist: 是否要求文件必须存在
        
    Returns:
        bool: 路径有效返回True，无效返回False
    """
    try:
        path_obj = Path(file_path)
        
        # 检查路径格式
        if not str(path_obj).strip():
            logger.error("文件路径不能为空")
            return False
            
        # 检查是否为目录
        if path_obj.exists() and path_obj.is_dir():
            logger.error(f"路径是目录而不是文件: {file_path}")
            return False
            
        # 检查文件是否存在（如果要求）
        if must_exist and not path_obj.exists():
            logger.error(f"文件不存在: {file_path}")
            return False
            
        return True
        
    except Exception as e:
        logger.error(f"路径验证失败 {file_path}: {e}")
        return False


def get_file_size(file_path: Union[str, Path]) -> Optional[int]:
    """
    获取文件大小
    
    Args:
        file_path: 文件路径
        
    Returns:
        int: 文件大小（字节），获取失败返回None
    """
    try:
        path_obj = Path(file_path)
        
        if not path_obj.exists():
            logger.error(f"文件不存在: {file_path}")
            return None
            
        size = path_obj.stat().st_size
        logger.debug(f"文件大小: {file_path} = {size} 字节")
        return size
        
    except Exception as e:
        logger.error(f"获取文件大小失败 {file_path}: {e}")
        return None


def find_json_files(directory: Union[str, Path], 
                   pattern: str = "*.json") -> list[Path]:
    """
    查找目录中的JSON文件
    
    Args:
        directory: 搜索目录
        pattern: 文件名模式
        
    Returns:
        list[Path]: 找到的JSON文件路径列表
    """
    try:
        dir_obj = Path(directory)
        
        if not dir_obj.exists():
            logger.error(f"目录不存在: {directory}")
            return []
            
        if not dir_obj.is_dir():
            logger.error(f"路径不是目录: {directory}")
            return []
            
        json_files = list(dir_obj.glob(pattern))
        json_files.sort()  # 按文件名排序
        
        logger.debug(f"在目录 {directory} 中找到 {len(json_files)} 个JSON文件")
        return json_files
        
    except Exception as e:
        logger.error(f"搜索JSON文件失败 {directory}: {e}")
        return []


def is_json_file(file_path: Union[str, Path]) -> bool:
    """
    检查文件是否为JSON文件
    
    Args:
        file_path: 文件路径
        
    Returns:
        bool: 是JSON文件返回True，否则返回False
    """
    try:
        path_obj = Path(file_path)
        
        # 检查文件扩展名
        if path_obj.suffix.lower() not in ['.json']:
            return False
            
        # 检查文件是否存在且可读
        if not path_obj.exists() or not path_obj.is_file():
            return False
            
        # 尝试解析JSON内容
        try:
            with open(path_obj, 'r', encoding='utf-8') as f:
                json.load(f)
            return True
        except json.JSONDecodeError:
            return False
            
    except Exception as e:
        logger.error(f"检查JSON文件失败 {file_path}: {e}")
        return False


def safe_file_operation(operation_func, *args, **kwargs):
    """
    安全执行文件操作的装饰器函数
    
    Args:
        operation_func: 要执行的文件操作函数
        *args: 位置参数
        **kwargs: 关键字参数
        
    Returns:
        操作结果，失败时返回None
    """
    try:
        return operation_func(*args, **kwargs)
    except PermissionError as e:
        logger.error(f"权限不足: {e}")
        return None
    except FileNotFoundError as e:
        logger.error(f"文件未找到: {e}")
        return None
    except OSError as e:
        logger.error(f"系统错误: {e}")
        return None
    except Exception as e:
        logger.error(f"文件操作失败: {e}")
        return None

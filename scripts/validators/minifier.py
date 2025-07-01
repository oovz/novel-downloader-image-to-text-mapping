"""
JSON压缩器模块

生成JSON文件的压缩版本，移除空格和格式化，减少文件大小。
支持批量处理和详细的压缩统计。
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any

from ..models.validation_result import ValidationResult, create_success_result, create_error_result
from ..utils.logger import get_logger
from ..utils.file_utils import read_json_file, write_json_file, get_file_size, ensure_directory

logger = get_logger(__name__)


class JsonMinifier:
    """JSON压缩器类"""
    
    def __init__(self, minified_suffix: str = ".min"):
        self.minified_suffix = minified_suffix
    
    def minify_json_data(self, data: Dict[str, str]) -> str:
        """
        压缩JSON数据
        
        Args:
            data: JSON数据字典
            
        Returns:
            str: 压缩后的JSON字符串
        """
        try:
            # 使用json.dumps生成压缩格式
            minified_json = json.dumps(
                data,
                ensure_ascii=False,  # 保持中文字符
                separators=(',', ':'),  # 使用最紧凑的分隔符
                sort_keys=False  # 保持原始顺序
            )
            
            logger.debug(f"JSON数据已压缩，条目数: {len(data)}")
            return minified_json
            
        except Exception as e:
            logger.error(f"压缩JSON数据异常: {e}")
            return ""
    
    def generate_minified_file(self, source_file: str, 
                              target_file: Optional[str] = None) -> ValidationResult:
        """
        生成压缩的JSON文件
        
        Args:
            source_file: 源JSON文件路径
            target_file: 目标压缩文件路径，None时自动生成
            
        Returns:
            ValidationResult: 处理结果
        """
        logger.info(f"开始生成压缩文件: {source_file}")
        
        try:
            # 读取源文件
            source_data = read_json_file(source_file)
            if source_data is None:
                return create_error_result(
                    f"无法读取源文件: {source_file}",
                    file_path=source_file,
                    error_type="source_file_read_error"
                )
            
            # 确定目标文件路径
            if target_file is None:
                source_path = Path(source_file)
                target_file = str(source_path.with_suffix(f"{self.minified_suffix}{source_path.suffix}"))
            
            # 确保目标目录存在
            target_path = Path(target_file)
            if not ensure_directory(target_path.parent):
                return create_error_result(
                    f"无法创建目标目录: {target_path.parent}",
                    file_path=target_file,
                    error_type="target_directory_error"
                )
            
            # 压缩数据
            minified_data = self.minify_json_data(source_data)
            if not minified_data:
                return create_error_result(
                    f"JSON数据压缩失败: {source_file}",
                    file_path=source_file,
                    error_type="minification_error"
                )
            
            # 写入压缩文件
            try:
                with open(target_path, 'w', encoding='utf-8') as f:
                    f.write(minified_data)
                
                logger.info(f"压缩文件已生成: {target_file}")
                
            except Exception as e:
                return create_error_result(
                    f"写入压缩文件失败: {e}",
                    file_path=target_file,
                    error_type="target_file_write_error"
                )
            
            # 计算压缩统计
            source_size = get_file_size(source_file) or 0
            target_size = get_file_size(target_file) or 0
            compression_ratio = 1 - (target_size / source_size) if source_size > 0 else 0
            
            # 创建成功结果
            result = create_success_result(
                processed_files=1,
                total_files=1,
                details={
                    "source_file": source_file,
                    "target_file": target_file,
                    "source_size": source_size,
                    "target_size": target_size,
                    "compression_ratio": compression_ratio,
                    "size_reduction": source_size - target_size,
                    "entry_count": len(source_data)
                }
            )
            
            result.add_warning(
                f"已生成压缩文件: {Path(target_file).name} "
                f"(压缩率: {compression_ratio:.1%})",
                file_path=target_file,
                warning_type="minification_completed"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"生成压缩文件异常 {source_file}: {e}")
            return create_error_result(
                f"处理异常: {e}",
                file_path=source_file,
                error_type="minification_exception"
            )
    
    def minify_multiple_files(self, source_files: List[str], 
                             target_directory: Optional[str] = None) -> ValidationResult:
        """
        批量生成压缩文件
        
        Args:
            source_files: 源文件路径列表
            target_directory: 目标目录，None时使用源文件目录
            
        Returns:
            ValidationResult: 批量处理结果
        """
        logger.info(f"开始批量生成压缩文件: {len(source_files)} 个文件")
        
        overall_result = ValidationResult(success=True, total_files=len(source_files))
        total_size_reduction = 0
        total_compression_ratio = 0.0
        
        for source_file in source_files:
            try:
                # 确定目标文件路径
                if target_directory:
                    source_path = Path(source_file)
                    target_file = str(Path(target_directory) / f"{source_path.stem}{self.minified_suffix}{source_path.suffix}")
                else:
                    target_file = None
                
                # 处理单个文件
                file_result = self.generate_minified_file(source_file, target_file)
                overall_result.merge(file_result)
                
                if file_result.success:
                    overall_result.processed_files += 1
                    
                    # 累积统计
                    size_reduction = file_result.details.get("size_reduction", 0)
                    compression_ratio = file_result.details.get("compression_ratio", 0)
                    total_size_reduction += size_reduction
                    total_compression_ratio += compression_ratio
                    
            except Exception as e:
                logger.error(f"处理文件异常 {source_file}: {e}")
                overall_result.add_error(
                    f"处理文件异常: {e}",
                    file_path=source_file,
                    error_type="file_processing_exception"
                )
        
        # 计算平均压缩率
        avg_compression_ratio = total_compression_ratio / len(source_files) if source_files else 0
        
        overall_result.details = {
            "total_size_reduction": total_size_reduction,
            "average_compression_ratio": avg_compression_ratio,
            "target_directory": target_directory
        }
        
        logger.info(f"批量压缩完成: 成功 {overall_result.processed_files}/{overall_result.total_files}, "
                   f"总节省空间: {total_size_reduction} 字节, 平均压缩率: {avg_compression_ratio:.1%}")
        
        return overall_result
    
    def update_minified_file(self, source_file: str, 
                            target_file: Optional[str] = None,
                            force_update: bool = False) -> ValidationResult:
        """
        更新压缩文件（仅在源文件更新时）
        
        Args:
            source_file: 源JSON文件路径
            target_file: 目标压缩文件路径
            force_update: 是否强制更新
            
        Returns:
            ValidationResult: 处理结果
        """
        logger.info(f"检查压缩文件更新: {source_file}")
        
        try:
            if target_file is None:
                source_path = Path(source_file)
                target_file = str(source_path.with_suffix(f"{self.minified_suffix}{source_path.suffix}"))
            
            target_path = Path(target_file)
            source_path = Path(source_file)
            
            # 检查文件是否需要更新
            if not force_update and target_path.exists():
                source_mtime = source_path.stat().st_mtime
                target_mtime = target_path.stat().st_mtime
                
                if target_mtime >= source_mtime:
                    logger.info(f"压缩文件已是最新: {target_file}")
                    return create_success_result(
                        processed_files=1,
                        total_files=1,
                        details={
                            "source_file": source_file,
                            "target_file": target_file,
                            "action": "skipped",
                            "reason": "target_file_up_to_date"
                        }
                    )
            
            # 生成压缩文件
            return self.generate_minified_file(source_file, target_file)
            
        except Exception as e:
            logger.error(f"更新压缩文件异常 {source_file}: {e}")
            return create_error_result(
                f"更新异常: {e}",
                file_path=source_file,
                error_type="update_exception"
            )
    
    def validate_minified_file(self, source_file: str, 
                              minified_file: str) -> ValidationResult:
        """
        验证压缩文件的正确性
        
        Args:
            source_file: 源文件路径
            minified_file: 压缩文件路径
            
        Returns:
            ValidationResult: 验证结果
        """
        logger.info(f"验证压缩文件: {minified_file}")
        
        try:
            # 读取源文件和压缩文件
            source_data = read_json_file(source_file)
            minified_data = read_json_file(minified_file)
            
            if source_data is None:
                return create_error_result(
                    f"无法读取源文件: {source_file}",
                    file_path=source_file,
                    error_type="source_file_read_error"
                )
            
            if minified_data is None:
                return create_error_result(
                    f"无法读取压缩文件: {minified_file}",
                    file_path=minified_file,
                    error_type="minified_file_read_error"
                )
            
            # 比较数据内容
            if source_data != minified_data:
                return create_error_result(
                    f"压缩文件内容与源文件不一致",
                    file_path=minified_file,
                    error_type="content_mismatch"
                )
            
            # 计算压缩统计
            source_size = get_file_size(source_file) or 0
            minified_size = get_file_size(minified_file) or 0
            compression_ratio = 1 - (minified_size / source_size) if source_size > 0 else 0
            
            result = create_success_result(
                processed_files=1,
                total_files=1,
                details={
                    "source_file": source_file,
                    "minified_file": minified_file,
                    "source_size": source_size,
                    "minified_size": minified_size,
                    "compression_ratio": compression_ratio,
                    "content_match": True
                }
            )
            
            logger.info(f"压缩文件验证通过: {minified_file} (压缩率: {compression_ratio:.1%})")
            return result
            
        except Exception as e:
            logger.error(f"验证压缩文件异常 {minified_file}: {e}")
            return create_error_result(
                f"验证异常: {e}",
                file_path=minified_file,
                error_type="validation_exception"
            )
    
    def get_minification_statistics(self, source_files: List[str]) -> Dict[str, Any]:
        """
        获取压缩统计信息
        
        Args:
            source_files: 源文件路径列表
            
        Returns:
            Dict[str, any]: 压缩统计信息
        """
        logger.debug(f"计算压缩统计，文件数: {len(source_files)}")
        
        stats: Dict[str, Any] = {
            "total_files": len(source_files),
            "minified_files_exist": 0,
            "total_source_size": 0,
            "total_minified_size": 0,
            "total_size_reduction": 0,
            "average_compression_ratio": 0.0,
            "file_details": []
        }
        
        try:
            compression_ratios: List[float] = []
            
            for source_file in source_files:
                source_path = Path(source_file)
                minified_file = str(source_path.with_suffix(f"{self.minified_suffix}{source_path.suffix}"))
                minified_path = Path(minified_file)
                
                source_size = get_file_size(source_file) or 0
                minified_size = get_file_size(minified_file) if minified_path.exists() else 0
                if minified_size is None:
                    minified_size = 0
                
                stats["total_source_size"] += source_size
                
                file_detail: Dict[str, Any] = {
                    "source_file": source_file,
                    "minified_file": minified_file,
                    "source_size": source_size,
                    "minified_size": minified_size,
                    "minified_exists": minified_path.exists()
                }
                
                if minified_path.exists():
                    stats["minified_files_exist"] += 1
                    stats["total_minified_size"] += minified_size
                    
                    compression_ratio: float = 1.0 - (minified_size / source_size) if source_size > 0 else 0.0
                    compression_ratios.append(compression_ratio)
                    
                    file_detail["compression_ratio"] = compression_ratio
                    file_detail["size_reduction"] = source_size - minified_size
                
                stats["file_details"].append(file_detail)
            
            stats["total_size_reduction"] = stats["total_source_size"] - stats["total_minified_size"]
            stats["average_compression_ratio"] = sum(compression_ratios) / len(compression_ratios) if compression_ratios else 0
            
            logger.debug(f"压缩统计完成: {stats}")
            
        except Exception as e:
            logger.error(f"计算压缩统计异常: {e}")
            stats["error"] = str(e)
        
        return stats
    
    def clean_outdated_minified_files(self, source_files: List[str]) -> ValidationResult:
        """
        清理过期的压缩文件
        
        Args:
            source_files: 源文件路径列表
            
        Returns:
            ValidationResult: 清理结果
        """
        logger.info(f"开始清理过期压缩文件: {len(source_files)} 个源文件")
        
        result = ValidationResult(success=True, total_files=len(source_files))
        cleaned_count = 0
        
        try:
            for source_file in source_files:
                source_path = Path(source_file)
                
                if not source_path.exists():
                    # 源文件不存在，查找并删除对应的压缩文件
                    minified_file = str(source_path.with_suffix(f"{self.minified_suffix}{source_path.suffix}"))
                    minified_path = Path(minified_file)
                    
                    if minified_path.exists():
                        try:
                            minified_path.unlink()
                            cleaned_count += 1
                            logger.info(f"已删除过期压缩文件: {minified_file}")
                            
                            result.add_warning(
                                f"删除了过期的压缩文件: {minified_path.name}",
                                file_path=minified_file,
                                warning_type="outdated_file_removed"
                            )
                            
                        except Exception as e:
                            result.add_error(
                                f"删除压缩文件失败: {e}",
                                file_path=minified_file,
                                error_type="file_deletion_error"
                            )
                
                result.processed_files += 1
            
            result.details = {
                "cleaned_files_count": cleaned_count
            }
            
            logger.info(f"清理完成: 删除了 {cleaned_count} 个过期压缩文件")
            
        except Exception as e:
            logger.error(f"清理过期文件异常: {e}")
            result.add_error(
                f"清理异常: {e}",
                error_type="cleanup_exception"
            )
        
        return result


def generate_minified_file(source_file: str, 
                          target_file: Optional[str] = None,
                          minified_suffix: str = ".min") -> ValidationResult:
    """
    生成压缩文件（便捷函数）
    
    Args:
        source_file: 源文件路径
        target_file: 目标文件路径
        minified_suffix: 压缩文件后缀
        
    Returns:
        ValidationResult: 处理结果
    """
    minifier = JsonMinifier(minified_suffix=minified_suffix)
    return minifier.generate_minified_file(source_file, target_file)


def minify_json_files(source_files: List[str], 
                     target_directory: Optional[str] = None,
                     minified_suffix: str = ".min") -> ValidationResult:
    """
    批量生成压缩文件（便捷函数）
    
    Args:
        source_files: 源文件路径列表
        target_directory: 目标目录
        minified_suffix: 压缩文件后缀
        
    Returns:
        ValidationResult: 处理结果
    """
    minifier = JsonMinifier(minified_suffix=minified_suffix)
    return minifier.minify_multiple_files(source_files, target_directory)

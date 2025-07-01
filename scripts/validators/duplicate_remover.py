"""
重复项移除器模块

从文件名映射中移除重复的条目，保留第一次出现的条目。
提供详细的移除统计和日志记录。
"""

from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Set, Tuple

from ..models.validation_result import ValidationResult, create_success_result, create_error_result
from ..utils.logger import get_logger
from ..utils.file_utils import read_json_file, write_json_file

logger = get_logger(__name__)


class DuplicateRemover:
    """重复项移除器类"""
    
    def __init__(self, create_backup: bool = True):
        self.create_backup = create_backup
    
    def remove_duplicates(self, mappings: Dict[str, str]) -> Tuple[Dict[str, str], Dict[str, List[str]]]:
        """
        从映射中移除重复项
        
        Args:
            mappings: 原始映射字典
            
        Returns:
            Tuple[Dict[str, str], Dict[str, List[str]]]: 
                (去重后的映射, 移除的重复项统计)
        """
        logger.info(f"开始移除重复项，原始条目数: {len(mappings)}")
        
        # 保持插入顺序的有序字典
        unique_mappings = OrderedDict()
        removed_duplicates = {}
        
        try:
            for filename, character in mappings.items():
                # 检查是否已存在相同的文件名
                if filename in unique_mappings:
                    # 记录重复项
                    if filename not in removed_duplicates:
                        removed_duplicates[filename] = []
                    removed_duplicates[filename].append(character)
                    logger.debug(f"发现重复文件名: {filename} -> {character}")
                else:
                    # 保留第一次出现的映射
                    unique_mappings[filename] = character
            
            logger.info(f"重复项移除完成，保留条目数: {len(unique_mappings)}, 移除重复项: {len(removed_duplicates)}")
            return dict(unique_mappings), removed_duplicates
            
        except Exception as e:
            logger.error(f"移除重复项异常: {e}")
            return mappings, {}
    
    def remove_duplicate_values(self, mappings: Dict[str, str]) -> Tuple[Dict[str, str], Dict[str, List[str]]]:
        """
        移除具有相同值的重复项（保留第一个键）
        
        Args:
            mappings: 原始映射字典
            
        Returns:
            Tuple[Dict[str, str], Dict[str, List[str]]]: 
                (去重后的映射, 移除的重复值统计)
        """
        logger.info(f"开始移除重复值，原始条目数: {len(mappings)}")
        
        unique_mappings = OrderedDict()
        seen_values = set()
        removed_duplicate_values = {}
        
        try:
            for filename, character in mappings.items():
                if character in seen_values:
                    # 记录重复值
                    if character not in removed_duplicate_values:
                        removed_duplicate_values[character] = []
                    removed_duplicate_values[character].append(filename)
                    logger.debug(f"发现重复字符值: {filename} -> {character}")
                else:
                    # 保留第一次出现的字符
                    unique_mappings[filename] = character
                    seen_values.add(character)
            
            logger.info(f"重复值移除完成，保留条目数: {len(unique_mappings)}, 移除重复值: {len(removed_duplicate_values)}")
            return dict(unique_mappings), removed_duplicate_values
            
        except Exception as e:
            logger.error(f"移除重复值异常: {e}")
            return mappings, {}
    
    def remove_duplicates_from_file(self, file_path: str, 
                                   remove_duplicate_values: bool = False) -> ValidationResult:
        """
        从JSON文件中移除重复项
        
        Args:
            file_path: JSON文件路径
            remove_duplicate_values: 是否同时移除重复值
            
        Returns:
            ValidationResult: 处理结果
        """
        logger.info(f"开始处理文件重复项: {file_path}")
        
        try:
            # 读取原始数据
            original_data = read_json_file(file_path)
            if original_data is None:
                return create_error_result(
                    f"无法读取文件: {file_path}",
                    file_path=file_path,
                    error_type="file_read_error"
                )
            
            original_count = len(original_data)
            
            # 备份功能已禁用 - 在git环境中不需要备份
            logger.debug("备份功能已禁用（使用git版本控制）")
            
            # 移除重复的键
            cleaned_data, removed_keys = self.remove_duplicates(original_data)
            
            # 可选：移除重复的值
            removed_values = {}
            if remove_duplicate_values:
                cleaned_data, removed_values = self.remove_duplicate_values(cleaned_data)
            
            final_count = len(cleaned_data)
            removed_count = original_count - final_count
            
            # 如果有变化，写入文件
            if removed_count > 0:
                success = write_json_file(file_path, cleaned_data)
                if not success:
                    return create_error_result(
                        f"无法写入文件: {file_path}",
                        file_path=file_path,
                        error_type="file_write_error"
                    )
                
                logger.info(f"重复项移除完成: {file_path}, 移除 {removed_count} 项")
            else:
                logger.info(f"文件无重复项: {file_path}")
            
            # 创建结果
            result = create_success_result(
                processed_files=1,
                total_files=1,
                details={
                    "original_count": original_count,
                    "final_count": final_count,
                    "removed_count": removed_count,
                    "removed_keys": removed_keys,
                    "removed_values": removed_values
                }
            )
            
            # 添加警告信息
            if removed_keys:
                result.add_warning(
                    f"移除了 {len(removed_keys)} 个重复键: {list(removed_keys.keys())}",
                    file_path=file_path,
                    warning_type="duplicate_keys_removed",
                    details={"removed_keys": removed_keys}
                )
            
            if removed_values:
                result.add_warning(
                    f"移除了 {len(removed_values)} 个重复值: {list(removed_values.keys())}",
                    file_path=file_path,
                    warning_type="duplicate_values_removed",
                    details={"removed_values": removed_values}
                )
            
            return result
            
        except Exception as e:
            logger.error(f"处理文件重复项异常 {file_path}: {e}")
            return create_error_result(
                f"处理异常: {e}",
                file_path=file_path,
                error_type="processing_exception"
            )
    
    def process_multiple_files(self, file_paths: List[str], 
                              remove_duplicate_values: bool = False) -> ValidationResult:
        """
        处理多个文件的重复项
        
        Args:
            file_paths: 文件路径列表
            remove_duplicate_values: 是否移除重复值
            
        Returns:
            ValidationResult: 综合处理结果
        """
        logger.info(f"开始批量处理重复项: {len(file_paths)} 个文件")
        
        overall_result = ValidationResult(success=True, total_files=len(file_paths))
        total_removed = 0
        
        for file_path in file_paths:
            file_result = self.remove_duplicates_from_file(file_path, remove_duplicate_values)
            overall_result.merge(file_result)
            
            if file_result.success:
                overall_result.processed_files += 1
                removed_count = file_result.details.get("removed_count", 0)
                total_removed += removed_count
        
        overall_result.details["total_removed_items"] = total_removed
        
        logger.info(f"批量处理完成: 成功 {overall_result.processed_files}/{overall_result.total_files}, 总移除 {total_removed} 项")
        return overall_result
    
    def analyze_duplicates(self, mappings: Dict[str, str]) -> Dict[str, any]:
        """
        分析映射中的重复情况
        
        Args:
            mappings: 映射字典
            
        Returns:
            Dict[str, any]: 重复分析结果
        """
        logger.debug(f"开始分析重复情况，条目数: {len(mappings)}")
        
        analysis = {
            "total_entries": len(mappings),
            "unique_keys": len(set(mappings.keys())),
            "unique_values": len(set(mappings.values())),
            "duplicate_keys": {},
            "duplicate_values": {},
            "character_statistics": {},
            "filename_statistics": {}
        }
        
        try:
            # 分析重复键
            key_counts = {}
            for key in mappings.keys():
                key_counts[key] = key_counts.get(key, 0) + 1
            
            analysis["duplicate_keys"] = {
                key: count for key, count in key_counts.items() if count > 1
            }
            
            # 分析重复值
            value_counts = {}
            value_to_keys = {}
            for key, value in mappings.items():
                value_counts[value] = value_counts.get(value, 0) + 1
                if value not in value_to_keys:
                    value_to_keys[value] = []
                value_to_keys[value].append(key)
            
            analysis["duplicate_values"] = {
                value: {
                    "count": count,
                    "keys": value_to_keys[value]
                }
                for value, count in value_counts.items() if count > 1
            }
            
            # 字符统计
            analysis["character_statistics"] = {
                "total_characters": len(set(mappings.values())),
                "most_common_characters": sorted(
                    [(char, count) for char, count in value_counts.items()],
                    key=lambda x: x[1],
                    reverse=True
                )[:10]
            }
            
            # 文件名统计
            filename_extensions = {}
            for filename in mappings.keys():
                try:
                    ext = Path(filename).suffix.lower()
                    filename_extensions[ext] = filename_extensions.get(ext, 0) + 1
                except:
                    pass
            
            analysis["filename_statistics"] = {
                "extensions": filename_extensions
            }
            
            logger.debug(f"重复分析完成: 重复键 {len(analysis['duplicate_keys'])}, 重复值 {len(analysis['duplicate_values'])}")
            
        except Exception as e:
            logger.error(f"分析重复情况异常: {e}")
            analysis["error"] = str(e)
        
        return analysis
    
    def get_duplicate_files_by_character(self, mappings: Dict[str, str]) -> Dict[str, List[str]]:
        """
        获取每个字符对应的所有文件名
        
        Args:
            mappings: 映射字典
            
        Returns:
            Dict[str, List[str]]: 字符到文件名列表的映射
        """
        char_to_files = {}
        
        try:
            for filename, character in mappings.items():
                if character not in char_to_files:
                    char_to_files[character] = []
                char_to_files[character].append(filename)
            
            # 只返回有多个文件的字符
            return {
                char: files for char, files in char_to_files.items() 
                if len(files) > 1
            }
            
        except Exception as e:
            logger.error(f"获取重复文件异常: {e}")
            return {}


def remove_duplicates_from_file(file_path: str, 
                               create_backup: bool = True,
                               remove_duplicate_values: bool = False) -> ValidationResult:
    """
    从文件中移除重复项（便捷函数）
    
    Args:
        file_path: 文件路径
        create_backup: 是否创建备份
        remove_duplicate_values: 是否移除重复值
        
    Returns:
        ValidationResult: 处理结果
    """
    remover = DuplicateRemover(create_backup=create_backup)
    return remover.remove_duplicates_from_file(file_path, remove_duplicate_values)


def remove_duplicates_from_files(file_paths: List[str], 
                                create_backup: bool = True,
                                remove_duplicate_values: bool = False) -> ValidationResult:
    """
    从多个文件中移除重复项（便捷函数）
    
    Args:
        file_paths: 文件路径列表
        create_backup: 是否创建备份
        remove_duplicate_values: 是否移除重复值
        
    Returns:
        ValidationResult: 处理结果
    """
    remover = DuplicateRemover(create_backup=create_backup)
    return remover.process_multiple_files(file_paths, remove_duplicate_values)

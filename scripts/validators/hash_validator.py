"""
哈希验证器模块

验证哈希映射的唯一性和格式正确性。
检查重复哈希、无效格式和数据一致性。
"""

import re
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any

from ..models.validation_result import ValidationResult, create_success_result, create_error_result
from ..utils.logger import get_logger
from ..utils.file_utils import read_json_file

logger = get_logger(__name__)


class HashValidator:
    """哈希验证器类"""
    
    def __init__(self):
        # 64位二进制哈希模式
        self.hash_pattern = re.compile(r'^[01]{64}$')
        # 中文字符模式
        self.chinese_char_pattern = re.compile(r'[\u4e00-\u9fff]')
    
    def validate_hash_format(self, hash_value: str) -> bool:
        """
        验证哈希格式
        
        Args:
            hash_value: 哈希值
            
        Returns:
            bool: 格式正确返回True
        """
        return bool(self.hash_pattern.match(hash_value))
    
    def validate_hash_uniqueness(self, hash_mappings: Dict[str, str]) -> ValidationResult:
        """
        验证哈希映射的唯一性
        
        Args:
            hash_mappings: 哈希映射字典
            
        Returns:
            ValidationResult: 验证结果
        """
        logger.info(f"开始验证哈希唯一性，条目数: {len(hash_mappings)}")
        
        result = ValidationResult(success=True)
        
        try:
            # 检查重复哈希键
            hash_keys = list(hash_mappings.keys())
            unique_hashes = set(hash_keys)
            
            if len(hash_keys) != len(unique_hashes):
                # 找出重复的哈希
                seen: Set[str] = set()
                duplicates: Set[str] = set()
                for hash_value in hash_keys:
                    if hash_value in seen:
                        duplicates.add(hash_value)
                        result.add_error(
                            f"发现重复的哈希值: {hash_value}",
                            error_type="duplicate_hash",
                            details={"hash": hash_value}
                        )
                    seen.add(hash_value)
                
                logger.error(f"发现 {len(duplicates)} 个重复哈希")
            
            # 检查哈希格式
            invalid_hashes: List[str] = []
            for hash_value in hash_mappings.keys():
                if not self.validate_hash_format(hash_value):
                    invalid_hashes.append(hash_value)
                    result.add_error(
                        f"无效的哈希格式: {hash_value}",
                        error_type="invalid_hash_format",
                        details={"hash": hash_value}
                    )
            
            if invalid_hashes:
                logger.error(f"发现 {len(invalid_hashes)} 个无效哈希格式")
            
            # 检查字符值
            invalid_characters: List[Tuple[str, str]] = []
            empty_characters: List[str] = []
            
            for hash_value, character in hash_mappings.items():
                if not character:
                    empty_characters.append(hash_value)
                    result.add_error(
                        f"哈希 {hash_value} 对应的字符为空",
                        error_type="empty_character",
                        details={"hash": hash_value}
                    )
                elif len(character) != 1:
                    result.add_warning(
                        f"哈希 {hash_value} 对应的字符长度不是1: '{character}'",
                        warning_type="multi_char_value",
                        details={"hash": hash_value, "character": character}
                    )
                elif not self.chinese_char_pattern.match(character):
                    invalid_characters.append((hash_value, character))
                    result.add_warning(
                        f"哈希 {hash_value} 对应的不是中文字符: '{character}'",
                        warning_type="non_chinese_character",
                        details={"hash": hash_value, "character": character}
                    )
            
            if empty_characters:
                logger.error(f"发现 {len(empty_characters)} 个空字符")
            if invalid_characters:
                logger.warning(f"发现 {len(invalid_characters)} 个非中文字符")
            
            # 检查字符到哈希的反向映射重复
            char_to_hashes: Dict[str, List[str]] = {}
            for hash_value, character in hash_mappings.items():
                if character not in char_to_hashes:
                    char_to_hashes[character] = []
                char_to_hashes[character].append(hash_value)
            
            # 报告一个字符对应多个哈希的情况
            multi_hash_chars: List[Tuple[str, List[str]]] = []
            for character, hashes in char_to_hashes.items():
                if len(hashes) > 1:
                    multi_hash_chars.append((character, hashes))
                    result.add_warning(
                        f"字符 '{character}' 对应多个哈希: {len(hashes)} 个",
                        warning_type="multiple_hashes_per_character",
                        details={
                            "character": character, 
                            "hashes": hashes,
                            "count": len(hashes)
                        }
                    )
            
            if multi_hash_chars:
                logger.warning(f"发现 {len(multi_hash_chars)} 个字符对应多个哈希")
            
            # 设置详细统计
            result.details = {
                "total_hashes": len(hash_mappings),
                "unique_hashes": len(unique_hashes),
                "unique_characters": len(set(hash_mappings.values())),
                "duplicate_hash_count": len(hash_keys) - len(unique_hashes),
                "invalid_hash_count": len(invalid_hashes),
                "empty_character_count": len(empty_characters),
                "invalid_character_count": len(invalid_characters),
                "multi_hash_character_count": len(multi_hash_chars)
            }
            
            logger.info(f"哈希唯一性验证完成: {result.details}")
            
        except Exception as e:
            logger.error(f"哈希唯一性验证异常: {e}")
            result.add_error(
                f"验证异常: {e}",
                error_type="validation_exception"
            )
        
        result.processed_files = 1
        result.total_files = 1
        return result
    
    def validate_hash_file(self, file_path: str) -> ValidationResult:
        """
        验证哈希映射文件
        
        Args:
            file_path: 哈希映射文件路径
            
        Returns:
            ValidationResult: 验证结果
        """
        logger.info(f"开始验证哈希文件: {file_path}")
        
        try:
            # 读取文件
            hash_mappings = read_json_file(file_path)
            if hash_mappings is None:
                return create_error_result(
                    f"无法读取哈希文件: {file_path}",
                    file_path=file_path,
                    error_type="file_read_error"
                )
            
            # 验证哈希唯一性
            result = self.validate_hash_uniqueness(hash_mappings)
            
            # 添加文件信息
            if result.success:
                logger.info(f"哈希文件验证通过: {file_path}")
            else:
                logger.error(f"哈希文件验证失败: {file_path}")
            
            return result
            
        except Exception as e:
            logger.error(f"验证哈希文件异常 {file_path}: {e}")
            return create_error_result(
                f"验证异常: {e}",
                file_path=file_path,
                error_type="validation_exception"
            )
    
    def validate_multiple_hash_files(self, file_paths: List[str]) -> ValidationResult:
        """
        验证多个哈希文件
        
        Args:
            file_paths: 哈希文件路径列表
            
        Returns:
            ValidationResult: 综合验证结果
        """
        logger.info(f"开始批量验证哈希文件: {len(file_paths)} 个文件")
        
        overall_result = ValidationResult(success=True, total_files=len(file_paths))
        
        for file_path in file_paths:
            file_result = self.validate_hash_file(file_path)
            overall_result.merge(file_result)
            
            if file_result.success:
                overall_result.processed_files += 1
        
        logger.info(f"批量验证完成: 成功 {overall_result.processed_files}/{overall_result.total_files}")
        return overall_result
    
    def compare_hash_mappings(self, mapping1: Dict[str, str], 
                             mapping2: Dict[str, str],
                             name1: str = "映射1", 
                             name2: str = "映射2") -> ValidationResult:
        """
        比较两个哈希映射
        
        Args:
            mapping1: 第一个哈希映射
            mapping2: 第二个哈希映射
            name1: 第一个映射的名称
            name2: 第二个映射的名称
            
        Returns:
            ValidationResult: 比较结果
        """
        logger.info(f"开始比较哈希映射: {name1} vs {name2}")
        
        result = ValidationResult(success=True)
        
        try:
            hashes1 = set(mapping1.keys())
            hashes2 = set(mapping2.keys())
            
            # 找出差异
            only_in_1 = hashes1 - hashes2
            only_in_2 = hashes2 - hashes1
            common_hashes = hashes1 & hashes2
            
            # 检查共同哈希的字符是否一致
            conflicting_mappings: List[str] = []
            for hash_value in common_hashes:
                if mapping1[hash_value] != mapping2[hash_value]:
                    conflicting_mappings.append(hash_value)
                    result.add_error(
                        f"哈希 {hash_value} 在两个映射中对应不同字符: "
                        f"'{mapping1[hash_value]}' vs '{mapping2[hash_value]}'",
                        error_type="conflicting_mapping",
                        details={
                            "hash": hash_value,
                            f"{name1}_character": mapping1[hash_value],
                            f"{name2}_character": mapping2[hash_value]
                        }
                    )
            
            # 报告差异
            if only_in_1:
                result.add_warning(
                    f"{len(only_in_1)} 个哈希仅在 {name1} 中存在",
                    warning_type="hash_only_in_first",
                    details={"count": len(only_in_1)}
                )
            
            if only_in_2:
                result.add_warning(
                    f"{len(only_in_2)} 个哈希仅在 {name2} 中存在",
                    warning_type="hash_only_in_second",
                    details={"count": len(only_in_2)}
                )
            
            # 设置详细统计
            result.details = {
                f"{name1}_hash_count": len(mapping1),
                f"{name2}_hash_count": len(mapping2),
                "common_hash_count": len(common_hashes),
                "only_in_first_count": len(only_in_1),
                "only_in_second_count": len(only_in_2),
                "conflicting_mapping_count": len(conflicting_mappings)
            }
            
            logger.info(f"哈希映射比较完成: {result.details}")
            
        except Exception as e:
            logger.error(f"比较哈希映射异常: {e}")
            result.add_error(
                f"比较异常: {e}",
                error_type="comparison_exception"
            )
        
        return result
    
    def find_duplicate_character_mappings(self, hash_mappings: Dict[str, str]) -> Dict[str, List[str]]:
        """
        查找重复的字符映射
        
        Args:
            hash_mappings: 哈希映射字典
            
        Returns:
            Dict[str, List[str]]: 字符到哈希列表的映射（仅包含重复的）
        """
        logger.debug(f"查找重复字符映射，条目数: {len(hash_mappings)}")
        
        char_to_hashes: Dict[str, List[str]] = {}
        
        try:
            for hash_value, character in hash_mappings.items():
                if character not in char_to_hashes:
                    char_to_hashes[character] = []
                char_to_hashes[character].append(hash_value)
            
            # 只返回有多个哈希的字符
            duplicate_mappings = {
                char: hashes for char, hashes in char_to_hashes.items() 
                if len(hashes) > 1
            }
            
            logger.debug(f"发现 {len(duplicate_mappings)} 个重复字符映射")
            return duplicate_mappings
            
        except Exception as e:
            logger.error(f"查找重复字符映射异常: {e}")
            return {}
    
    def get_hash_statistics(self, hash_mappings: Dict[str, str]) -> Dict[str, Any]:
        """
        获取哈希映射统计信息
        
        Args:
            hash_mappings: 哈希映射字典
            
        Returns:
            Dict[str, any]: 统计信息
        """
        logger.debug(f"计算哈希统计信息，条目数: {len(hash_mappings)}")
        
        stats = {
            "total_hashes": len(hash_mappings),
            "unique_characters": len(set(hash_mappings.values())),
            "hash_format_valid": 0,
            "hash_format_invalid": 0,
            "chinese_characters": 0,
            "non_chinese_characters": 0,
            "empty_characters": 0,
            "character_distribution": {}
        }
        
        try:
            char_counts: Dict[str, int] = {}
            
            for hash_value, character in hash_mappings.items():
                # 检查哈希格式
                if self.validate_hash_format(hash_value):
                    stats["hash_format_valid"] += 1
                else:
                    stats["hash_format_invalid"] += 1
                
                # 检查字符
                if not character:
                    stats["empty_characters"] += 1
                elif self.chinese_char_pattern.match(character):
                    stats["chinese_characters"] += 1
                else:
                    stats["non_chinese_characters"] += 1
                
                # 字符计数
                char_counts[character] = char_counts.get(character, 0) + 1
            
            # 字符分布（按频率排序）
            stats["character_distribution"] = dict(
                sorted(char_counts.items(), key=lambda x: x[1], reverse=True)
            )
            
            logger.debug(f"哈希统计完成: {stats}")
            
        except Exception as e:
            logger.error(f"计算哈希统计异常: {e}")
            stats["error"] = str(e)
        
        return stats


def validate_hash_uniqueness(hash_mappings: Dict[str, str]) -> ValidationResult:
    """
    验证哈希唯一性（便捷函数）
    
    Args:
        hash_mappings: 哈希映射字典
        
    Returns:
        ValidationResult: 验证结果
    """
    validator = HashValidator()
    return validator.validate_hash_uniqueness(hash_mappings)


def validate_hash_file(file_path: str) -> ValidationResult:
    """
    验证哈希文件（便捷函数）
    
    Args:
        file_path: 哈希文件路径
        
    Returns:
        ValidationResult: 验证结果
    """
    validator = HashValidator()
    return validator.validate_hash_file(file_path)


def validate_hash_files(file_paths: List[str]) -> ValidationResult:
    """
    验证多个哈希文件（便捷函数）
    
    Args:
        file_paths: 哈希文件路径列表
        
    Returns:
        ValidationResult: 验证结果
    """
    validator = HashValidator()
    return validator.validate_multiple_hash_files(file_paths)

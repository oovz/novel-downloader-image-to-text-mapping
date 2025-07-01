"""
JSON验证器模块

检查JSON文件的格式、编码和数据结构有效性。
支持中文字符验证和详细的错误报告。
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from ..models.validation_result import ValidationResult, create_success_result, create_error_result
from ..utils.logger import get_logger
from ..utils.file_utils import read_json_file, validate_file_path

logger = get_logger(__name__)


class JsonValidator:
    """JSON验证器类"""
    
    def __init__(self):
        self.chinese_char_pattern = re.compile(r'[\u4e00-\u9fff]')
        self.special_char_pattern = re.compile(r'[^\w\s\u4e00-\u9fff\.\-_]')
        self.filename_pattern = re.compile(r'^[a-zA-Z0-9\-_\.]+\.(png|jpg|jpeg|gif|bmp|webp)$', re.IGNORECASE)
        self.hash_pattern = re.compile(r'^[01]{64}$')
    
    def validate_json_format(self, file_path: str) -> ValidationResult:
        """
        验证JSON文件格式
        
        Args:
            file_path: JSON文件路径
            
        Returns:
            ValidationResult: 验证结果
        """
        logger.info(f"开始验证JSON格式: {file_path}")
        
        try:
            # 验证文件路径
            if not validate_file_path(file_path, must_exist=True):
                return create_error_result(
                    f"文件路径无效: {file_path}",
                    file_path=file_path,
                    error_type="file_path_error"
                )
            
            path_obj = Path(file_path)
            
            # 检查文件扩展名
            if path_obj.suffix.lower() != '.json':
                return create_error_result(
                    f"文件不是JSON格式: {file_path}",
                    file_path=file_path,
                    error_type="file_extension_error"
                )
            
            # 读取并解析JSON
            try:
                with open(path_obj, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # 检查编码问题
                encoding_result = self._check_encoding(content, file_path)
                if not encoding_result.success:
                    return encoding_result
                
                # 解析JSON
                try:
                    data = json.loads(content)
                except json.JSONDecodeError as e:
                    return create_error_result(
                        f"JSON解析错误: {e.msg}",
                        file_path=file_path,
                        error_type="json_parse_error",
                        details={
                            "line": e.lineno,
                            "column": e.colno,
                            "position": e.pos
                        }
                    )
                
                # 验证JSON结构
                structure_result = self._validate_json_structure(data, file_path)
                if not structure_result.success:
                    return structure_result
                
                # 验证数据内容
                content_result = self._validate_json_content(data, file_path)
                if not content_result.success:
                    return content_result
                
                logger.info(f"JSON格式验证通过: {file_path}")
                return create_success_result(
                    processed_files=1,
                    total_files=1,
                    details={"entry_count": len(data)}
                )
                
            except UnicodeDecodeError as e:
                return create_error_result(
                    f"文件编码错误: {e}",
                    file_path=file_path,
                    error_type="encoding_error"
                )
            except Exception as e:
                return create_error_result(
                    f"文件读取错误: {e}",
                    file_path=file_path,
                    error_type="file_read_error"
                )
                
        except Exception as e:
            logger.error(f"JSON格式验证异常 {file_path}: {e}")
            return create_error_result(
                f"验证过程异常: {e}",
                file_path=file_path,
                error_type="validation_exception"
            )
    
    def _check_encoding(self, content: str, file_path: str) -> ValidationResult:
        """检查文件编码"""
        result = ValidationResult(success=True)
        
        try:
            # 检查是否包含BOM
            if content.startswith('\ufeff'):
                result.add_warning(
                    "文件包含BOM标记，建议移除",
                    file_path=file_path,
                    warning_type="bom_warning"
                )
            
            # 检查常见编码问题
            if '�' in content:
                result.add_error(
                    "文件包含编码错误字符",
                    file_path=file_path,
                    error_type="encoding_error"
                )
            
            # 检查控制字符
            control_chars = [char for char in content if ord(char) < 32 and char not in ['\n', '\r', '\t']]
            if control_chars:
                result.add_warning(
                    f"文件包含控制字符: {[hex(ord(c)) for c in set(control_chars)]}",
                    file_path=file_path,
                    warning_type="control_char_warning"
                )
                
        except Exception as e:
            result.add_error(
                f"编码检查异常: {e}",
                file_path=file_path,
                error_type="encoding_check_error"
            )
        
        return result
    
    def _validate_json_structure(self, data: Any, file_path: str) -> ValidationResult:
        """验证JSON数据结构"""
        result = ValidationResult(success=True)
        
        try:
            # 检查根数据类型
            if not isinstance(data, dict):
                result.add_error(
                    f"JSON根元素必须是对象，当前是: {type(data).__name__}",
                    file_path=file_path,
                    error_type="structure_error"
                )
                return result
            
            # 检查是否为空对象
            if len(data) == 0:
                result.add_warning(
                    "JSON文件为空对象",
                    file_path=file_path,
                    warning_type="empty_data_warning"
                )
            
            # 检查键值对结构
            for key, value in data.items():
                # 检查键类型
                if not isinstance(key, str):
                    result.add_error(
                        f"JSON键必须是字符串，当前键 {key} 是: {type(key).__name__}",
                        file_path=file_path,
                        error_type="key_type_error"
                    )
                
                # 检查值类型
                if not isinstance(value, str):
                    result.add_error(
                        f"JSON值必须是字符串，键 '{key}' 的值是: {type(value).__name__}",
                        file_path=file_path,
                        error_type="value_type_error"
                    )
                
                # 检查空键或空值
                if not key.strip():
                    result.add_error(
                        "JSON不能包含空键",
                        file_path=file_path,
                        error_type="empty_key_error"
                    )
                
                if isinstance(value, str) and not value.strip():
                    result.add_warning(
                        f"键 '{key}' 的值为空字符串",
                        file_path=file_path,
                        warning_type="empty_value_warning"
                    )
                    
        except Exception as e:
            result.add_error(
                f"结构验证异常: {e}",
                file_path=file_path,
                error_type="structure_validation_error"
            )
        
        return result
    
    def _validate_json_content(self, data: Dict[str, str], file_path: str) -> ValidationResult:
        """验证JSON内容"""
        result = ValidationResult(success=True)
        
        try:
            # 根据文件路径判断文件类型
            path_obj = Path(file_path)
            is_filename_mapping = 'filename-mappings' in str(path_obj)
            is_hash_mapping = 'hash-mappings' in str(path_obj)
            
            if is_filename_mapping:
                result = self._validate_filename_mapping_content(data, file_path)
            elif is_hash_mapping:
                result = self._validate_hash_mapping_content(data, file_path)
            else:
                result.add_warning(
                    "无法确定JSON文件类型，跳过内容验证",
                    file_path=file_path,
                    warning_type="unknown_file_type"
                )
                
        except Exception as e:
            result.add_error(
                f"内容验证异常: {e}",
                file_path=file_path,
                error_type="content_validation_error"
            )
        
        return result
    
    def _validate_filename_mapping_content(self, data: Dict[str, str], file_path: str) -> ValidationResult:
        """验证文件名映射内容"""
        result = ValidationResult(success=True)
        
        try:
            for filename, character in data.items():
                # 验证文件名格式
                if not self.filename_pattern.match(filename):
                    result.add_error(
                        f"无效的文件名格式: {filename}",
                        file_path=file_path,
                        error_type="invalid_filename_format"
                    )
                
                # 验证字符
                if not character:
                    result.add_error(
                        f"文件名 '{filename}' 对应的字符为空",
                        file_path=file_path,
                        error_type="empty_character"
                    )
                elif len(character) != 1:
                    result.add_warning(
                        f"文件名 '{filename}' 对应的字符长度不是1: '{character}'",
                        file_path=file_path,
                        warning_type="multi_char_value"
                    )
                elif not self.chinese_char_pattern.match(character):
                    result.add_warning(
                        f"文件名 '{filename}' 对应的不是中文字符: '{character}'",
                        file_path=file_path,
                        warning_type="non_chinese_character"
                    )
                
                # 检查特殊字符
                if self.special_char_pattern.search(filename):
                    result.add_warning(
                        f"文件名包含特殊字符: {filename}",
                        file_path=file_path,
                        warning_type="special_char_in_filename"
                    )
            
            # 检查重复映射
            self._check_duplicate_mappings(data, file_path, result)
            
        except Exception as e:
            result.add_error(
                f"文件名映射验证异常: {e}",
                file_path=file_path,
                error_type="filename_mapping_validation_error"
            )
        
        return result
    
    def _validate_hash_mapping_content(self, data: Dict[str, str], file_path: str) -> ValidationResult:
        """验证哈希映射内容"""
        result = ValidationResult(success=True)
        
        try:
            for hash_value, character in data.items():
                # 验证哈希格式
                if not self.hash_pattern.match(hash_value):
                    result.add_error(
                        f"无效的哈希格式: {hash_value}",
                        file_path=file_path,
                        error_type="invalid_hash_format"
                    )
                
                # 验证字符
                if not character:
                    result.add_error(
                        f"哈希 '{hash_value}' 对应的字符为空",
                        file_path=file_path,
                        error_type="empty_character"
                    )
                elif len(character) != 1:
                    result.add_warning(
                        f"哈希 '{hash_value}' 对应的字符长度不是1: '{character}'",
                        file_path=file_path,
                        warning_type="multi_char_value"
                    )
                elif not self.chinese_char_pattern.match(character):
                    result.add_warning(
                        f"哈希 '{hash_value}' 对应的不是中文字符: '{character}'",
                        file_path=file_path,
                        warning_type="non_chinese_character"
                    )
            
            # 检查重复哈希（应该不存在）
            self._check_duplicate_hashes(data, file_path, result)
            
        except Exception as e:
            result.add_error(
                f"哈希映射验证异常: {e}",
                file_path=file_path,
                error_type="hash_mapping_validation_error"
            )
        
        return result
    
    def _check_duplicate_mappings(self, data: Dict[str, str], file_path: str, result: ValidationResult) -> None:
        """检查重复映射"""
        try:
            # 按字符分组，查找重复
            char_to_files = {}
            for filename, character in data.items():
                if character not in char_to_files:
                    char_to_files[character] = []
                char_to_files[character].append(filename)
            
            # 报告重复映射（这在文件名映射中是正常的）
            for character, filenames in char_to_files.items():
                if len(filenames) > 1:
                    result.add_warning(
                        f"字符 '{character}' 有多个文件名映射: {filenames}",
                        file_path=file_path,
                        warning_type="duplicate_character_mapping",
                        details={"character": character, "filenames": filenames}
                    )
                    
        except Exception as e:
            result.add_error(
                f"重复映射检查异常: {e}",
                file_path=file_path,
                error_type="duplicate_check_error"
            )
    
    def _check_duplicate_hashes(self, data: Dict[str, str], file_path: str, result: ValidationResult) -> None:
        """检查重复哈希"""
        try:
            # 检查是否有重复的哈希值（不应该存在）
            hash_values = list(data.keys())
            unique_hashes = set(hash_values)
            
            if len(hash_values) != len(unique_hashes):
                # 找出重复的哈希
                seen = set()
                duplicates = set()
                for hash_value in hash_values:
                    if hash_value in seen:
                        duplicates.add(hash_value)
                    seen.add(hash_value)
                
                for duplicate_hash in duplicates:
                    result.add_error(
                        f"发现重复的哈希值: {duplicate_hash}",
                        file_path=file_path,
                        error_type="duplicate_hash",
                        details={"hash": duplicate_hash}
                    )
            
            # 检查字符到哈希的反向映射重复
            char_to_hashes = {}
            for hash_value, character in data.items():
                if character not in char_to_hashes:
                    char_to_hashes[character] = []
                char_to_hashes[character].append(hash_value)
            
            for character, hashes in char_to_hashes.items():
                if len(hashes) > 1:
                    result.add_warning(
                        f"字符 '{character}' 有多个哈希映射: {len(hashes)} 个",
                        file_path=file_path,
                        warning_type="multiple_hashes_per_character",
                        details={"character": character, "hash_count": len(hashes)}
                    )
                    
        except Exception as e:
            result.add_error(
                f"重复哈希检查异常: {e}",
                file_path=file_path,
                error_type="duplicate_hash_check_error"
            )
    
    def validate_multiple_files(self, file_paths: List[str]) -> ValidationResult:
        """
        验证多个JSON文件
        
        Args:
            file_paths: JSON文件路径列表
            
        Returns:
            ValidationResult: 综合验证结果
        """
        logger.info(f"开始批量验证JSON文件: {len(file_paths)} 个文件")
        
        overall_result = ValidationResult(success=True, total_files=len(file_paths))
        
        for file_path in file_paths:
            file_result = self.validate_json_format(file_path)
            overall_result.merge(file_result)
            
            if file_result.success:
                overall_result.processed_files += 1
        
        logger.info(f"批量验证完成: 成功 {overall_result.processed_files}/{overall_result.total_files}")
        return overall_result


def validate_json_format(file_path: str) -> ValidationResult:
    """
    验证单个JSON文件格式（便捷函数）
    
    Args:
        file_path: JSON文件路径
        
    Returns:
        ValidationResult: 验证结果
    """
    validator = JsonValidator()
    return validator.validate_json_format(file_path)


def validate_json_files(file_paths: List[str]) -> ValidationResult:
    """
    验证多个JSON文件格式（便捷函数）
    
    Args:
        file_paths: JSON文件路径列表
        
    Returns:
        ValidationResult: 验证结果
    """
    validator = JsonValidator()
    return validator.validate_multiple_files(file_paths)

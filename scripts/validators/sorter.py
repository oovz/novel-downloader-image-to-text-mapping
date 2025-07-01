"""
排序器模块

对映射条目进行排序，按字符分组后再按文件名排序。
提供灵活的排序选项和详细的统计信息。
"""

from collections import OrderedDict, defaultdict
from pathlib import Path
from typing import Dict, List, Tuple, Callable, Any

from ..models.validation_result import ValidationResult, create_success_result, create_error_result
from ..utils.logger import get_logger
from ..utils.file_utils import read_json_file, write_json_file

logger = get_logger(__name__)


class MappingSorter:
    """映射排序器类"""
    
    def __init__(self, create_backup: bool = True):
        self.create_backup = create_backup
    
    def sort_by_character_then_filename(self, mappings: Dict[str, str], 
                                       reverse_char: bool = False,
                                       reverse_filename: bool = False) -> Dict[str, str]:
        """
        按字符分组后按文件名排序
        
        Args:
            mappings: 原始映射字典
            reverse_char: 是否反向排序字符
            reverse_filename: 是否反向排序文件名
            
        Returns:
            Dict[str, str]: 排序后的映射字典
        """
        logger.info(f"开始排序映射，条目数: {len(mappings)}")
        
        try:
            # 按字符分组
            char_groups: Dict[str, List[str]] = defaultdict(list)
            for filename, character in mappings.items():
                char_groups[character].append(filename)
            
            # 对每个组内的文件名排序
            for character in char_groups:
                char_groups[character].sort(reverse=reverse_filename)
            
            # 按字符排序并重建映射
            sorted_mappings: Dict[str, str] = OrderedDict()
            sorted_characters = sorted(char_groups.keys(), reverse=reverse_char)
            
            for character in sorted_characters:
                for filename in char_groups[character]:
                    sorted_mappings[filename] = character
            
            logger.info(f"排序完成，字符组数: {len(char_groups)}")
            return dict(sorted_mappings)
            
        except Exception as e:
            logger.error(f"排序异常: {e}")
            return mappings
    
    def sort_by_filename_only(self, mappings: Dict[str, str], 
                             reverse: bool = False) -> Dict[str, str]:
        """
        仅按文件名排序
        
        Args:
            mappings: 原始映射字典
            reverse: 是否反向排序
            
        Returns:
            Dict[str, str]: 排序后的映射字典
        """
        logger.info(f"按文件名排序，条目数: {len(mappings)}")
        
        try:
            sorted_items = sorted(mappings.items(), key=lambda x: x[0], reverse=reverse)
            return OrderedDict(sorted_items)
            
        except Exception as e:
            logger.error(f"按文件名排序异常: {e}")
            return mappings
    
    def sort_by_character_only(self, mappings: Dict[str, str], 
                              reverse: bool = False) -> Dict[str, str]:
        """
        仅按字符排序
        
        Args:
            mappings: 原始映射字典
            reverse: 是否反向排序
            
        Returns:
            Dict[str, str]: 排序后的映射字典
        """
        logger.info(f"按字符排序，条目数: {len(mappings)}")
        
        try:
            sorted_items = sorted(mappings.items(), key=lambda x: x[1], reverse=reverse)
            return OrderedDict(sorted_items)
            
        except Exception as e:
            logger.error(f"按字符排序异常: {e}")
            return mappings
    
    def sort_by_filename_length(self, mappings: Dict[str, str], 
                               reverse: bool = False) -> Dict[str, str]:
        """
        按文件名长度排序
        
        Args:
            mappings: 原始映射字典
            reverse: 是否反向排序（长度从大到小）
            
        Returns:
            Dict[str, str]: 排序后的映射字典
        """
        logger.info(f"按文件名长度排序，条目数: {len(mappings)}")
        
        try:
            sorted_items = sorted(
                mappings.items(), 
                key=lambda x: (len(x[0]), x[0]),  # 先按长度，再按字母顺序
                reverse=reverse
            )
            return OrderedDict(sorted_items)
            
        except Exception as e:
            logger.error(f"按文件名长度排序异常: {e}")
            return mappings
    
    def sort_by_extension_then_filename(self, mappings: Dict[str, str], 
                                       reverse: bool = False) -> Dict[str, str]:
        """
        按文件扩展名分组后按文件名排序
        
        Args:
            mappings: 原始映射字典
            reverse: 是否反向排序
            
        Returns:
            Dict[str, str]: 排序后的映射字典
        """
        logger.info(f"按扩展名和文件名排序，条目数: {len(mappings)}")
        
        try:
            # 按扩展名分组
            ext_groups: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
            for filename, character in mappings.items():
                try:
                    ext = Path(filename).suffix.lower()
                    ext_groups[ext].append((filename, character))
                except:
                    ext_groups[''].append((filename, character))
            
            # 对每个组内的文件名排序
            for ext in ext_groups:
                ext_groups[ext].sort(key=lambda x: x[0], reverse=reverse)
            
            # 按扩展名排序并重建映射
            sorted_mappings: Dict[str, str] = OrderedDict()
            sorted_extensions = sorted(ext_groups.keys(), reverse=reverse)
            
            for ext in sorted_extensions:
                for filename, character in ext_groups[ext]:
                    sorted_mappings[filename] = character
            
            logger.info(f"按扩展名排序完成，扩展名数: {len(ext_groups)}")
            return dict(sorted_mappings)
            
        except Exception as e:
            logger.error(f"按扩展名排序异常: {e}")
            return mappings
    
    def custom_sort(self, mappings: Dict[str, str], 
                   key_func: Callable[[Tuple[str, str]], Any],
                   reverse: bool = False) -> Dict[str, str]:
        """
        自定义排序
        
        Args:
            mappings: 原始映射字典
            key_func: 排序键函数，接收(filename, character)元组
            reverse: 是否反向排序
            
        Returns:
            Dict[str, str]: 排序后的映射字典
        """
        logger.info(f"自定义排序，条目数: {len(mappings)}")
        
        try:
            sorted_items = sorted(mappings.items(), key=key_func, reverse=reverse)
            return OrderedDict(sorted_items)
            
        except Exception as e:
            logger.error(f"自定义排序异常: {e}")
            return mappings
    
    def sort_mappings_file(self, file_path: str, 
                          sort_method: str = "character_then_filename",
                          reverse_char: bool = False,
                          reverse_filename: bool = False) -> ValidationResult:
        """
        对文件中的映射进行排序
        
        Args:
            file_path: JSON文件路径
            sort_method: 排序方法 ("character_then_filename", "filename_only", 
                        "character_only", "filename_length", "extension_then_filename")
            reverse_char: 是否反向排序字符
            reverse_filename: 是否反向排序文件名
            
        Returns:
            ValidationResult: 处理结果
        """
        logger.info(f"开始排序文件: {file_path}, 方法: {sort_method}")
        
        try:
            # 读取原始数据
            original_data = read_json_file(file_path)
            if original_data is None:
                return create_error_result(
                    f"无法读取文件: {file_path}",
                    file_path=file_path,
                    error_type="file_read_error"
                )
            
            original_order = list(original_data.keys())
            
            # 备份功能已禁用 - 在git环境中不需要备份
            logger.debug("备份功能已禁用（使用git版本控制）")
            
            # 根据方法选择排序
            if sort_method == "character_then_filename":
                sorted_data = self.sort_by_character_then_filename(
                    original_data, reverse_char, reverse_filename
                )
            elif sort_method == "filename_only":
                sorted_data = self.sort_by_filename_only(original_data, reverse_filename)
            elif sort_method == "character_only":
                sorted_data = self.sort_by_character_only(original_data, reverse_char)
            elif sort_method == "filename_length":
                sorted_data = self.sort_by_filename_length(original_data, reverse_filename)
            elif sort_method == "extension_then_filename":
                sorted_data = self.sort_by_extension_then_filename(original_data, reverse_filename)
            else:
                return create_error_result(
                    f"未知的排序方法: {sort_method}",
                    file_path=file_path,
                    error_type="invalid_sort_method"
                )
            
            sorted_order = list(sorted_data.keys())
            order_changed = original_order != sorted_order
            
            # 如果顺序有变化，写入文件
            if order_changed:
                success = write_json_file(file_path, sorted_data)
                if not success:
                    return create_error_result(
                        f"无法写入文件: {file_path}",
                        file_path=file_path,
                        error_type="file_write_error"
                    )
                
                logger.info(f"排序完成并已保存: {file_path}")
            else:
                logger.info(f"文件已是排序状态: {file_path}")
            
            # 生成排序统计
            sort_stats = self._generate_sort_statistics(original_data, sorted_data)
            
            # 创建结果
            result = create_success_result(
                processed_files=1,
                total_files=1,
                details={
                    "sort_method": sort_method,
                    "order_changed": order_changed,
                    "entry_count": len(sorted_data),
                    "sort_statistics": sort_stats
                }
            )
            
            if order_changed:
                result.add_warning(
                    f"文件顺序已更改: {sort_method}",
                    file_path=file_path,
                    warning_type="order_changed"
                )
            
            return result
            
        except Exception as e:
            logger.error(f"排序文件异常 {file_path}: {e}")
            return create_error_result(
                f"排序异常: {e}",
                file_path=file_path,
                error_type="sorting_exception"
            )
    
    def _generate_sort_statistics(self, original_data: Dict[str, str], 
                                 sorted_data: Dict[str, str]) -> Dict[str, Any]:
        """生成排序统计信息"""
        try:
            # 字符分组统计
            char_groups: Dict[str, int] = defaultdict(int)
            for character in sorted_data.values():
                char_groups[character] += 1
            
            # 扩展名统计
            ext_stats: Dict[str, int] = defaultdict(int)
            for filename in sorted_data.keys():
                try:
                    ext = Path(filename).suffix.lower()
                    ext_stats[ext] += 1
                except:
                    ext_stats[''] += 1
            
            # 文件名长度统计
            filename_lengths = [len(filename) for filename in sorted_data.keys()]
            
            return {
                "character_groups": len(char_groups),
                "character_distribution": dict(sorted(char_groups.items())),
                "extension_distribution": dict(sorted(ext_stats.items())),
                "filename_length_stats": {
                    "min": min(filename_lengths) if filename_lengths else 0,
                    "max": max(filename_lengths) if filename_lengths else 0,
                    "avg": sum(filename_lengths) / len(filename_lengths) if filename_lengths else 0
                }
            }
            
        except Exception as e:
            logger.error(f"生成排序统计异常: {e}")
            return {"error": str(e)}
    
    def process_multiple_files(self, file_paths: List[str], 
                              sort_method: str = "character_then_filename",
                              reverse_char: bool = False,
                              reverse_filename: bool = False) -> ValidationResult:
        """
        处理多个文件的排序
        
        Args:
            file_paths: 文件路径列表
            sort_method: 排序方法
            reverse_char: 是否反向排序字符
            reverse_filename: 是否反向排序文件名
            
        Returns:
            ValidationResult: 综合处理结果
        """
        logger.info(f"开始批量排序: {len(file_paths)} 个文件")
        
        overall_result = ValidationResult(success=True, total_files=len(file_paths))
        
        for file_path in file_paths:
            file_result = self.sort_mappings_file(
                file_path, sort_method, reverse_char, reverse_filename
            )
            overall_result.merge(file_result)
            
            if file_result.success:
                overall_result.processed_files += 1
        
        logger.info(f"批量排序完成: 成功 {overall_result.processed_files}/{overall_result.total_files}")
        return overall_result
    
    def analyze_sort_requirements(self, mappings: Dict[str, str]) -> Dict[str, Any]:
        """
        分析映射的排序需求
        
        Args:
            mappings: 映射字典
            
        Returns:
            Dict[str, any]: 排序分析结果
        """
        logger.debug(f"分析排序需求，条目数: {len(mappings)}")
        
        analysis = {
            "total_entries": len(mappings),
            "is_sorted_by_filename": self._is_sorted_by_filename(mappings),
            "is_sorted_by_character": self._is_sorted_by_character(mappings),
            "is_sorted_by_char_then_filename": self._is_sorted_by_char_then_filename(mappings),
            "character_groups": self._get_character_groups(mappings),
            "recommended_sort_method": None
        }
        
        try:
            # 推荐排序方法
            if not analysis["is_sorted_by_char_then_filename"]:
                analysis["recommended_sort_method"] = "character_then_filename"
            elif not analysis["is_sorted_by_filename"]:
                analysis["recommended_sort_method"] = "filename_only"
            else:
                analysis["recommended_sort_method"] = "already_sorted"
            
            logger.debug(f"排序分析完成，推荐方法: {analysis['recommended_sort_method']}")
            
        except Exception as e:
            logger.error(f"排序分析异常: {e}")
            analysis["error"] = str(e)
        
        return analysis
    
    def _is_sorted_by_filename(self, mappings: Dict[str, str]) -> bool:
        """检查是否按文件名排序"""
        filenames = list(mappings.keys())
        return filenames == sorted(filenames)
    
    def _is_sorted_by_character(self, mappings: Dict[str, str]) -> bool:
        """检查是否按字符排序"""
        characters = list(mappings.values())
        return characters == sorted(characters)
    
    def _is_sorted_by_char_then_filename(self, mappings: Dict[str, str]) -> bool:
        """检查是否按字符分组后按文件名排序"""
        try:
            char_groups: Dict[str, List[str]] = defaultdict(list)
            for filename, character in mappings.items():
                char_groups[character].append(filename)
            
            # 检查字符是否按顺序出现
            current_char = None
            for filename, character in mappings.items():
                if current_char is None or character != current_char:
                    current_char = character
                elif character < current_char:
                    return False
            
            # 检查每个字符组内的文件名是否排序
            for character, filenames in char_groups.items():
                if filenames != sorted(filenames):
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"检查排序状态异常: {e}")
            return False
    
    def _get_character_groups(self, mappings: Dict[str, str]) -> Dict[str, int]:
        """获取字符分组统计"""
        char_groups: Dict[str, int] = defaultdict(int)
        for character in mappings.values():
            char_groups[character] += 1
        return dict(sorted(char_groups.items()))


def sort_mappings_file(file_path: str, 
                      sort_method: str = "character_then_filename",
                      create_backup: bool = True,
                      reverse_char: bool = False,
                      reverse_filename: bool = False) -> ValidationResult:
    """
    排序映射文件（便捷函数）
    
    Args:
        file_path: 文件路径
        sort_method: 排序方法
        create_backup: 是否创建备份
        reverse_char: 是否反向排序字符
        reverse_filename: 是否反向排序文件名
        
    Returns:
        ValidationResult: 处理结果
    """
    sorter = MappingSorter(create_backup=create_backup)
    return sorter.sort_mappings_file(file_path, sort_method, reverse_char, reverse_filename)


def sort_mappings_files(file_paths: List[str], 
                       sort_method: str = "character_then_filename",
                       create_backup: bool = True,
                       reverse_char: bool = False,
                       reverse_filename: bool = False) -> ValidationResult:
    """
    排序多个映射文件（便捷函数）
    
    Args:
        file_paths: 文件路径列表
        sort_method: 排序方法
        create_backup: 是否创建备份
        reverse_char: 是否反向排序字符
        reverse_filename: 是否反向排序文件名
        
    Returns:
        ValidationResult: 处理结果
    """
    sorter = MappingSorter(create_backup=create_backup)
    return sorter.process_multiple_files(file_paths, sort_method, reverse_char, reverse_filename)

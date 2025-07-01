"""
验证结果数据模型

定义用于验证和处理结果的数据结构，提供类型安全和一致的数据格式。
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime
import json


@dataclass
class ValidationError:
    """验证错误信息"""
    message: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    column_number: Optional[int] = None
    error_type: str = "general"
    details: Dict[str, Any] = field(default_factory=dict)
    
    def __str__(self) -> str:
        """字符串表示"""
        location = ""
        if self.file_path:
            location += f"文件: {self.file_path}"
            if self.line_number:
                location += f", 行: {self.line_number}"
                if self.column_number:
                    location += f", 列: {self.column_number}"
            location += " - "
        
        return f"{location}{self.message}"


@dataclass
class ValidationWarning:
    """验证警告信息"""
    message: str
    file_path: Optional[str] = None
    warning_type: str = "general"
    details: Dict[str, Any] = field(default_factory=dict)
    
    def __str__(self) -> str:
        """字符串表示"""
        location = f"文件: {self.file_path} - " if self.file_path else ""
        return f"{location}{self.message}"


@dataclass
class ValidationResult:
    """验证结果"""
    success: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationWarning] = field(default_factory=list)
    processed_files: int = 0
    total_files: int = 0
    execution_time: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    details: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def has_errors(self) -> bool:
        """是否有错误"""
        return len(self.errors) > 0
    
    @property
    def has_warnings(self) -> bool:
        """是否有警告"""
        return len(self.warnings) > 0
    
    @property
    def error_count(self) -> int:
        """错误数量"""
        return len(self.errors)
    
    @property
    def warning_count(self) -> int:
        """警告数量"""
        return len(self.warnings)
    
    def add_error(self, message: str, file_path: Optional[str] = None, 
                  line_number: Optional[int] = None, 
                  column_number: Optional[int] = None,
                  error_type: str = "general",
                  details: Optional[Dict[str, Any]] = None) -> None:
        """添加错误"""
        error = ValidationError(
            message=message,
            file_path=file_path,
            line_number=line_number,
            column_number=column_number,
            error_type=error_type,
            details=details or {}
        )
        self.errors.append(error)
        self.success = False
    
    def add_warning(self, message: str, file_path: Optional[str] = None,
                   warning_type: str = "general",
                   details: Optional[Dict[str, Any]] = None) -> None:
        """添加警告"""
        warning = ValidationWarning(
            message=message,
            file_path=file_path,
            warning_type=warning_type,
            details=details or {}
        )
        self.warnings.append(warning)
    
    def merge(self, other: 'ValidationResult') -> None:
        """合并另一个验证结果"""
        if not other.success:
            self.success = False
        
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        self.processed_files += other.processed_files
        self.total_files += other.total_files
        self.execution_time += other.execution_time
        
        # 合并详细信息
        for key, value in other.details.items():
            if key in self.details:
                if isinstance(self.details[key], list) and isinstance(value, list):
                    self.details[key].extend(value)
                elif isinstance(self.details[key], dict) and isinstance(value, dict):
                    self.details[key].update(value)
                else:
                    self.details[f"{key}_merged"] = [self.details[key], value]
            else:
                self.details[key] = value
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'success': self.success,
            'error_count': self.error_count,
            'warning_count': self.warning_count,
            'processed_files': self.processed_files,
            'total_files': self.total_files,
            'execution_time': self.execution_time,
            'timestamp': self.timestamp.isoformat(),
            'errors': [
                {
                    'message': error.message,
                    'file_path': error.file_path,
                    'line_number': error.line_number,
                    'column_number': error.column_number,
                    'error_type': error.error_type,
                    'details': error.details
                }
                for error in self.errors
            ],
            'warnings': [
                {
                    'message': warning.message,
                    'file_path': warning.file_path,
                    'warning_type': warning.warning_type,
                    'details': warning.details
                }
                for warning in self.warnings
            ],
            'details': self.details
        }
    
    def to_json(self, indent: Optional[int] = 2) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


@dataclass
class ProcessingStats:
    """处理统计信息"""
    processed: int = 0
    failed: int = 0
    skipped: int = 0
    created: int = 0
    updated: int = 0
    deleted: int = 0
    
    @property
    def total_attempts(self) -> int:
        """总尝试次数"""
        return self.processed + self.failed + self.skipped
    
    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.total_attempts == 0:
            return 0.0
        return (self.processed / self.total_attempts) * 100
    
    def add_processed(self, count: int = 1) -> None:
        """添加处理成功数量"""
        self.processed += count
    
    def add_failed(self, count: int = 1) -> None:
        """添加处理失败数量"""
        self.failed += count
    
    def add_skipped(self, count: int = 1) -> None:
        """添加跳过数量"""
        self.skipped += count
    
    def add_created(self, count: int = 1) -> None:
        """添加创建数量"""
        self.created += count
    
    def add_updated(self, count: int = 1) -> None:
        """添加更新数量"""
        self.updated += count
    
    def add_deleted(self, count: int = 1) -> None:
        """添加删除数量"""
        self.deleted += count


@dataclass
class SyncResult:
    """同步处理结果"""
    success: bool
    domain: str
    stats: ProcessingStats = field(default_factory=ProcessingStats)
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationWarning] = field(default_factory=list)
    execution_time: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    new_mappings: Dict[str, str] = field(default_factory=dict)  # 新创建的映射
    updated_mappings: Dict[str, str] = field(default_factory=dict)  # 更新的映射
    failed_downloads: List[str] = field(default_factory=list)  # 下载失败的文件名
    
    @property
    def has_errors(self) -> bool:
        """是否有错误"""
        return len(self.errors) > 0
    
    @property
    def has_warnings(self) -> bool:
        """是否有警告"""
        return len(self.warnings) > 0
    
    def add_error(self, message: str, file_path: Optional[str] = None,
                  error_type: str = "sync_error",
                  details: Optional[Dict[str, Any]] = None) -> None:
        """添加错误"""
        error = ValidationError(
            message=message,
            file_path=file_path,
            error_type=error_type,
            details=details or {}
        )
        self.errors.append(error)
        self.success = False
    
    def add_warning(self, message: str, file_path: Optional[str] = None,
                   warning_type: str = "sync_warning",
                   details: Optional[Dict[str, Any]] = None) -> None:
        """添加警告"""
        warning = ValidationWarning(
            message=message,
            file_path=file_path,
            warning_type=warning_type,
            details=details or {}
        )
        self.warnings.append(warning)
    
    def add_new_mapping(self, filename: str, character: str, hash_value: str) -> None:
        """添加新映射"""
        self.new_mappings[hash_value] = character
        self.stats.add_created()
    
    def add_updated_mapping(self, hash_value: str, character: str) -> None:
        """添加更新映射"""
        self.updated_mappings[hash_value] = character
        self.stats.add_updated()
    
    def add_failed_download(self, filename: str) -> None:
        """添加下载失败文件"""
        self.failed_downloads.append(filename)
        self.stats.add_failed()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'success': self.success,
            'domain': self.domain,
            'stats': {
                'processed': self.stats.processed,
                'failed': self.stats.failed,
                'skipped': self.stats.skipped,
                'created': self.stats.created,
                'updated': self.stats.updated,
                'deleted': self.stats.deleted,
                'success_rate': self.stats.success_rate
            },
            'error_count': len(self.errors),
            'warning_count': len(self.warnings),
            'execution_time': self.execution_time,
            'timestamp': self.timestamp.isoformat(),
            'new_mappings_count': len(self.new_mappings),
            'updated_mappings_count': len(self.updated_mappings),
            'failed_downloads_count': len(self.failed_downloads),
            'errors': [
                {
                    'message': error.message,
                    'file_path': error.file_path,
                    'error_type': error.error_type,
                    'details': error.details
                }
                for error in self.errors
            ],
            'warnings': [
                {
                    'message': warning.message,
                    'file_path': warning.file_path,
                    'warning_type': warning.warning_type,
                    'details': warning.details
                }
                for warning in self.warnings
            ],
            'failed_downloads': self.failed_downloads
        }


@dataclass
class OverallResult:
    """总体结果"""
    success: bool
    validation_results: Dict[str, ValidationResult] = field(default_factory=dict)
    sync_results: Dict[str, SyncResult] = field(default_factory=dict)
    execution_time: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    
    @property
    def total_errors(self) -> int:
        """总错误数"""
        count = 0
        for result in self.validation_results.values():
            count += result.error_count
        for result in self.sync_results.values():
            count += len(result.errors)
        return count
    
    @property
    def total_warnings(self) -> int:
        """总警告数"""
        count = 0
        for result in self.validation_results.values():
            count += result.warning_count
        for result in self.sync_results.values():
            count += len(result.warnings)
        return count
    
    def add_validation_result(self, step_name: str, result: ValidationResult) -> None:
        """添加验证结果"""
        self.validation_results[step_name] = result
        if not result.success:
            self.success = False
    
    def add_sync_result(self, domain: str, result: SyncResult) -> None:
        """添加同步结果"""
        self.sync_results[domain] = result
        if not result.success:
            self.success = False
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'success': self.success,
            'total_errors': self.total_errors,
            'total_warnings': self.total_warnings,
            'execution_time': self.execution_time,
            'timestamp': self.timestamp.isoformat(),
            'validation_results': {
                step: result.to_dict() 
                for step, result in self.validation_results.items()
            },
            'sync_results': {
                domain: result.to_dict()
                for domain, result in self.sync_results.items()
            }
        }
    
    def to_json(self, indent: Optional[int] = 2) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


def create_success_result(processed_files: int = 0, 
                         total_files: int = 0,
                         execution_time: float = 0.0,
                         details: Optional[Dict[str, Any]] = None) -> ValidationResult:
    """创建成功的验证结果"""
    return ValidationResult(
        success=True,
        processed_files=processed_files,
        total_files=total_files,
        execution_time=execution_time,
        details=details or {}
    )


def create_error_result(message: str, 
                       file_path: Optional[str] = None,
                       error_type: str = "general",
                       execution_time: float = 0.0,
                       details: Optional[Dict[str, Any]] = None) -> ValidationResult:
    """创建错误的验证结果"""
    result = ValidationResult(
        success=False,
        execution_time=execution_time,
        details=details or {}
    )
    result.add_error(message, file_path, error_type=error_type)
    return result


def create_sync_success_result(domain: str,
                              stats: Optional[ProcessingStats] = None,
                              execution_time: float = 0.0) -> SyncResult:
    """创建成功的同步结果"""
    return SyncResult(
        success=True,
        domain=domain,
        stats=stats or ProcessingStats(),
        execution_time=execution_time
    )


def create_sync_error_result(domain: str,
                            message: str,
                            execution_time: float = 0.0) -> SyncResult:
    """创建错误的同步结果"""
    result = SyncResult(
        success=False,
        domain=domain,
        execution_time=execution_time
    )
    result.add_error(message)
    return result

"""
日志工具模块

提供集中化的日志记录功能，支持多种日志级别和输出格式。
"""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Any

import colorama
from colorama import Fore, Style

# 初始化 colorama 以支持 Windows 终端颜色
colorama.init(autoreset=True)


class ColoredFormatter(logging.Formatter):
    """带颜色的日志格式化器，用于终端输出"""

    COLORS = {
        logging.DEBUG: Fore.CYAN,
        logging.INFO: Fore.GREEN,
        logging.WARNING: Fore.YELLOW,
        logging.ERROR: Fore.RED,
        logging.CRITICAL: Fore.MAGENTA + Style.BRIGHT,
    }

    def format(self, record: logging.LogRecord) -> str:
        log_color = self.COLORS.get(record.levelno, "")
        record.levelname = f"{log_color}{record.levelname}{Style.RESET_ALL}"
        return super().format(record)


def get_logger(
    module_name: str,
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    enable_console: bool = True,
) -> logging.Logger:
    """
    获取配置好的日志记录器

    Args:
        module_name: 模块名称，用作日志记录器名称
        log_level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: 日志文件路径，如果为 None 则不输出到文件
        enable_console: 是否启用控制台输出

    Returns:
        配置好的日志记录器实例
    """
    logger = logging.getLogger(module_name)

    # 避免重复添加处理器
    if logger.handlers:
        return logger

    # 设置日志级别
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(numeric_level)

    # 创建格式化器
    detailed_formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    simple_formatter = logging.Formatter(
        fmt="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%H:%M:%S",
    )

    # 控制台处理器
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)

        # 如果支持颜色，使用彩色格式化器
        if hasattr(sys.stdout, "isatty") and sys.stdout.isatty():
            colored_formatter = ColoredFormatter(
                fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%H:%M:%S",
            )
            console_handler.setFormatter(colored_formatter)
        else:
            console_handler.setFormatter(simple_formatter)

        logger.addHandler(console_handler)

    # 文件处理器
    if log_file:
        # 确保日志目录存在
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(detailed_formatter)
        logger.addHandler(file_handler)

    return logger


def get_default_log_file(module_name: str) -> str:
    """
    获取模块的默认日志文件路径

    Args:
        module_name: 模块名称

    Returns:
        默认日志文件路径
    """
    timestamp = datetime.now().strftime("%Y%m%d")
    safe_module_name = module_name.replace(".", "_")
    return f"logs/{safe_module_name}_{timestamp}.log"


def setup_validation_logger(enable_file_logging: bool = True) -> logging.Logger:
    """
    设置验证工具的专用日志记录器

    Args:
        enable_file_logging: 是否启用文件日志记录

    Returns:
        配置好的验证日志记录器
    """
    log_file = get_default_log_file("validation") if enable_file_logging else None
    log_level = os.getenv("LOG_LEVEL", "INFO")

    return get_logger(
        module_name="validation",
        log_level=log_level,
        log_file=log_file,
        enable_console=True,
    )


def log_progress(message: str) -> None:
    """
    Log a progress message with INFO level.
    
    Args:
        message: Progress message to log
    """
    main_logger.info(f"📝 {message}")


def log_result(operation: str, result: Any) -> None:
    """
    Log the result of an operation.
    
    Args:
        operation: Name of the operation
        result: ValidationResult or similar result object
    """
    if hasattr(result, 'is_valid'):
        status = "✅ Success" if result.is_valid else "❌ Failed"
        main_logger.info(f"{operation}: {status}")
        
        if hasattr(result, 'message') and result.message:
            main_logger.info(f"  Message: {result.message}")
            
        if hasattr(result, 'errors') and result.errors:
            main_logger.error(f"  Errors ({len(result.errors)}):")
            for i, error in enumerate(result.errors[:5], 1):  # Limit to first 5
                main_logger.error(f"    {i}. {error}")
            if len(result.errors) > 5:
                main_logger.error(f"    ... and {len(result.errors) - 5} more")
                
        if hasattr(result, 'warnings') and result.warnings:
            main_logger.warning(f"  Warnings ({len(result.warnings)}):")
            for i, warning in enumerate(result.warnings[:3], 1):  # Limit to first 3
                main_logger.warning(f"    {i}. {warning}")
            if len(result.warnings) > 3:
                main_logger.warning(f"    ... and {len(result.warnings) - 3} more")
                
        if hasattr(result, 'stats') and result.stats:
            main_logger.info(f"  Statistics: {result.stats}")
    else:
        main_logger.info(f"{operation}: {result}")


def log_progress_detailed(logger: logging.Logger, current: int, total: int, operation: str) -> None:
    """
    记录进度信息

    Args:
        logger: 日志记录器实例
        current: 当前进度
        total: 总数
        operation: 操作描述
    """
    percentage = (current / total) * 100 if total > 0 else 0
    logger.info(f"{operation}: {current}/{total} ({percentage:.1f}%)")


def log_validation_result(
    logger: logging.Logger,
    file_path: str,
    success: bool,
    errors: list = None,
    warnings: list = None,
) -> None:
    """
    记录验证结果

    Args:
        logger: 日志记录器实例
        file_path: 被验证的文件路径
        success: 验证是否成功
        errors: 错误列表
        warnings: 警告列表
    """
    errors = errors or []
    warnings = warnings or []

    status = "✅ 通过" if success else "❌ 失败"
    logger.info(f"验证结果 - {file_path}: {status}")

    if errors:
        logger.error(f"发现 {len(errors)} 个错误:")
        for i, error in enumerate(errors, 1):
            logger.error(f"  {i}. {error}")

    if warnings:
        logger.warning(f"发现 {len(warnings)} 个警告:")
        for i, warning in enumerate(warnings, 1):
            logger.warning(f"  {i}. {warning}")


def log_performance_metrics(
    logger: logging.Logger,
    operation: str,
    duration: float,
    items_processed: int = 0,
) -> None:
    """
    记录性能指标

    Args:
        logger: 日志记录器实例
        operation: 操作名称
        duration: 执行时间（秒）
        items_processed: 处理的项目数量
    """
    logger.info(f"性能指标 - {operation}:")
    logger.info(f"  执行时间: {duration:.2f} 秒")

    if items_processed > 0:
        rate = items_processed / duration if duration > 0 else 0
        logger.info(f"  处理项目: {items_processed}")
        logger.info(f"  处理速度: {rate:.2f} 项/秒")


# 预配置的日志记录器实例
main_logger = get_logger("main")
validation_logger = setup_validation_logger()

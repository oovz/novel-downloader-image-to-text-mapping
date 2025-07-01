"""
Novel Downloader Image-to-Text Mapping Validation Pipeline

This package provides a comprehensive validation and synchronization pipeline
for image-to-text mapping JSON files used in novel downloading applications.

Main Components:
- validators: JSON validation, duplicate removal, sorting, hash validation, minification
- processors: Image downloading, hashing, and mapping synchronization
- utils: File operations, logging, and configuration management
- models: Data structures for validation results
- config: Domain-specific configurations

Usage:
    python -m scripts.main --help
    python -m scripts.main --full-pipeline
    python -m scripts.main --validate-only --domains www.example.com
"""

__version__ = "1.0.0"
__author__ = "AI Assistant"
__email__ = "ai@assistant.com"

# Package-level imports for convenience
from .main import main
from .models.validation_result import ValidationResult
from .utils.logger import get_logger

__all__ = ["main", "ValidationResult", "get_logger"]

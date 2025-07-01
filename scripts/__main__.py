#!/usr/bin/env python3
"""
Module entry point for the novel downloader image-to-text mapping validation pipeline.

This file enables execution via 'uv run -m scripts' by providing a module-level entry point
that delegates to the main orchestrator script.
"""

from .main import main

if __name__ == "__main__":
    main()

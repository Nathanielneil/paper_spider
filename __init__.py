"""
ArXiv Academic Paper Crawler

A comprehensive tool for searching, downloading, and managing research papers from ArXiv.
Features multi-threaded downloads, database storage, and rich command-line interface.

Version: 1.0.0
Author: ArXiv Paper Crawler Team
License: MIT
"""

__version__ = "1.0.0"
__author__ = "ArXiv Paper Crawler Team"
__license__ = "MIT"
__description__ = "A comprehensive ArXiv academic paper crawler and manager"

# Import main classes for programmatic usage
from .arxiv_api import ArxivAPI, ArxivAPIException
from .data_processor import DataProcessor
from .downloader import DownloadManager, DownloadResult, DownloadException
from .config import ConfigManager, ConfigException

__all__ = [
    'ArxivAPI',
    'ArxivAPIException', 
    'DataProcessor',
    'DownloadManager',
    'DownloadResult',
    'DownloadException',
    'ConfigManager',
    'ConfigException',
    '__version__',
    '__author__',
    '__license__',
    '__description__'
]
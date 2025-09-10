"""
Logging configuration module for ArXiv paper crawler.
Provides centralized logging setup and utilities.
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Dict, Optional


class ColoredFormatter(logging.Formatter):
    """Colored formatter for console output."""
    
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green  
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }
    
    def format(self, record):
        if hasattr(record, 'levelname'):
            color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
            record.levelname = f"{color}{record.levelname}{self.COLORS['RESET']}"
        
        return super().format(record)


def setup_logging(config: Dict) -> None:
    """
    Setup logging configuration based on config dictionary.
    
    Args:
        config: Logging configuration dictionary
    """
    log_level = config.get('level', 'INFO').upper()
    log_file = config.get('log_file', 'arxiv_crawler.log')
    max_file_size = config.get('max_file_size', '10MB')
    backup_count = config.get('backup_count', 3)
    
    # Parse file size
    if isinstance(max_file_size, str):
        if max_file_size.upper().endswith('MB'):
            max_bytes = int(float(max_file_size[:-2]) * 1024 * 1024)
        elif max_file_size.upper().endswith('KB'):
            max_bytes = int(float(max_file_size[:-2]) * 1024)
        else:
            max_bytes = int(max_file_size)
    else:
        max_bytes = max_file_size
    
    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    console_formatter = ColoredFormatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level, logging.INFO))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler (only show warnings and errors)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file and log_file.lower() != 'none':
        try:
            # Ensure log directory exists
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding='utf-8'
            )
            file_handler.setLevel(getattr(logging, log_level, logging.INFO))
            file_handler.setFormatter(file_formatter)
            root_logger.addHandler(file_handler)
            
        except Exception as e:
            print(f"Warning: Could not setup file logging: {e}")
    
    # Set specific logger levels
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    
    # Log startup message
    logger = logging.getLogger(__name__)
    logger.info("Logging system initialized")
    logger.info(f"Log level: {log_level}")
    if log_file and log_file.lower() != 'none':
        logger.info(f"Log file: {log_file}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def log_exception(logger: logging.Logger, message: str, exc_info: bool = True) -> None:
    """
    Log an exception with traceback.
    
    Args:
        logger: Logger instance
        message: Exception message
        exc_info: Whether to include exception info
    """
    logger.exception(message, exc_info=exc_info)


def create_module_logger(module_name: str, level: Optional[str] = None) -> logging.Logger:
    """
    Create a logger for a specific module.
    
    Args:
        module_name: Name of the module
        level: Optional log level override
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(module_name)
    
    if level:
        logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    return logger
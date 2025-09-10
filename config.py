"""
Configuration management module for ArXiv paper crawler.
Handles loading, validation, and management of application settings.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union

import yaml


class ConfigException(Exception):
    """Custom exception for configuration-related errors."""
    pass


class ConfigManager:
    """
    Manages application configuration from YAML files and environment variables.
    
    Provides centralized configuration management with validation,
    default values, and environment variable overrides.
    """
    
    def __init__(self, config_path: Union[str, Path] = 'config.yaml'):
        """
        Initialize configuration manager.
        
        Args:
            config_path: Path to the configuration file
        """
        self.config_path = Path(config_path)
        self.logger = logging.getLogger(__name__)
        
        # Default configuration
        self._defaults = {
            'api': {
                'base_url': 'http://export.arxiv.org/api/query',
                'max_results_per_query': 100,
                'request_delay': 3.0,
                'user_agent': 'ArxivCrawler/1.0 (https://github.com/user/arxiv-crawler)',
                'timeout': 30
            },
            'download': {
                'output_directory': './downloaded_papers',
                'max_concurrent_downloads': 5,
                'retry_attempts': 3,
                'timeout': 60,
                'filename_pattern': '{year}_{first_author}_{title}',
                'create_category_folders': True
            },
            'storage': {
                'database_path': './arxiv_papers.db',
                'export_formats': ['json', 'csv'],
                'auto_backup': True
            },
            'logging': {
                'level': 'INFO',
                'log_file': 'arxiv_crawler.log',
                'max_file_size': '10MB',
                'backup_count': 3
            }
        }
        
        self._config = {}
        self._load_config()
    
    def _load_config(self) -> None:
        """Load configuration from file and apply environment overrides."""
        try:
            # Start with defaults
            self._config = self._deep_copy_dict(self._defaults)
            
            # Load from file if it exists
            if self.config_path.exists():
                self._load_from_file()
                self.logger.info(f"Configuration loaded from {self.config_path}")
            else:
                self.logger.warning(f"Configuration file {self.config_path} not found, using defaults")
                # Create default config file
                self._create_default_config()
            
            # Apply environment variable overrides
            self._apply_env_overrides()
            
            # Validate configuration
            self._validate_config()
            
        except Exception as e:
            raise ConfigException(f"Failed to load configuration: {e}")
    
    def _load_from_file(self) -> None:
        """Load configuration from YAML file."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                file_config = yaml.safe_load(f) or {}
            
            # Merge with defaults (file config takes precedence)
            self._config = self._merge_configs(self._defaults, file_config)
            
        except yaml.YAMLError as e:
            raise ConfigException(f"Invalid YAML in config file: {e}")
        except Exception as e:
            raise ConfigException(f"Error reading config file: {e}")
    
    def _create_default_config(self) -> None:
        """Create a default configuration file."""
        try:
            # Ensure parent directory exists
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write default config
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(self._defaults, f, default_flow_style=False, indent=2)
            
            self.logger.info(f"Created default configuration file at {self.config_path}")
            
        except Exception as e:
            self.logger.warning(f"Could not create default config file: {e}")
    
    def _apply_env_overrides(self) -> None:
        """Apply environment variable overrides to configuration."""
        env_mappings = {
            # API settings
            'ARXIV_API_BASE_URL': ['api', 'base_url'],
            'ARXIV_API_MAX_RESULTS': ['api', 'max_results_per_query'],
            'ARXIV_API_DELAY': ['api', 'request_delay'],
            'ARXIV_API_USER_AGENT': ['api', 'user_agent'],
            'ARXIV_API_TIMEOUT': ['api', 'timeout'],
            
            # Download settings
            'ARXIV_DOWNLOAD_DIR': ['download', 'output_directory'],
            'ARXIV_DOWNLOAD_THREADS': ['download', 'max_concurrent_downloads'],
            'ARXIV_DOWNLOAD_RETRIES': ['download', 'retry_attempts'],
            'ARXIV_DOWNLOAD_TIMEOUT': ['download', 'timeout'],
            'ARXIV_FILENAME_PATTERN': ['download', 'filename_pattern'],
            
            # Storage settings
            'ARXIV_DATABASE_PATH': ['storage', 'database_path'],
            
            # Logging settings
            'ARXIV_LOG_LEVEL': ['logging', 'level'],
            'ARXIV_LOG_FILE': ['logging', 'log_file']
        }
        
        for env_var, config_path in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                # Convert value to appropriate type
                converted_value = self._convert_env_value(env_value, config_path)
                self._set_nested_value(self._config, config_path, converted_value)
                self.logger.info(f"Applied environment override: {env_var} -> {'.'.join(config_path)}")
    
    def _convert_env_value(self, value: str, config_path: list) -> Any:
        """Convert environment variable string to appropriate type."""
        # Get the default value to determine expected type
        default_value = self._get_nested_value(self._defaults, config_path)
        
        if isinstance(default_value, bool):
            return value.lower() in ('true', '1', 'yes', 'on')
        elif isinstance(default_value, int):
            try:
                return int(value)
            except ValueError:
                return value
        elif isinstance(default_value, float):
            try:
                return float(value)
            except ValueError:
                return value
        elif isinstance(default_value, list):
            # Convert comma-separated string to list
            return [item.strip() for item in value.split(',') if item.strip()]
        else:
            return value
    
    def _validate_config(self) -> None:
        """Validate configuration values."""
        validations = [
            # API validations
            (self._config['api']['max_results_per_query'] > 0, 
             "api.max_results_per_query must be positive"),
            (self._config['api']['request_delay'] >= 0, 
             "api.request_delay must be non-negative"),
            (self._config['api']['timeout'] > 0, 
             "api.timeout must be positive"),
            
            # Download validations
            (self._config['download']['max_concurrent_downloads'] > 0, 
             "download.max_concurrent_downloads must be positive"),
            (self._config['download']['retry_attempts'] >= 0, 
             "download.retry_attempts must be non-negative"),
            (self._config['download']['timeout'] > 0, 
             "download.timeout must be positive"),
            
            # Logging validations
            (self._config['logging']['level'] in ['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
             "logging.level must be one of: DEBUG, INFO, WARNING, ERROR"),
            (self._config['logging']['backup_count'] >= 0, 
             "logging.backup_count must be non-negative")
        ]
        
        for condition, message in validations:
            if not condition:
                raise ConfigException(f"Configuration validation failed: {message}")
    
    def _deep_copy_dict(self, d: Dict) -> Dict:
        """Create a deep copy of a dictionary."""
        if isinstance(d, dict):
            return {k: self._deep_copy_dict(v) for k, v in d.items()}
        elif isinstance(d, list):
            return [self._deep_copy_dict(item) for item in d]
        else:
            return d
    
    def _merge_configs(self, base: Dict, override: Dict) -> Dict:
        """Recursively merge two configuration dictionaries."""
        merged = self._deep_copy_dict(base)
        
        for key, value in override.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = self._merge_configs(merged[key], value)
            else:
                merged[key] = self._deep_copy_dict(value)
        
        return merged
    
    def _get_nested_value(self, d: Dict, path: list) -> Any:
        """Get a nested value from dictionary using a path list."""
        current = d
        for key in path:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        return current
    
    def _set_nested_value(self, d: Dict, path: list, value: Any) -> None:
        """Set a nested value in dictionary using a path list."""
        current = d
        for key in path[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[path[-1]] = value
    
    def get(self, section: str, key: Optional[str] = None, default: Any = None) -> Any:
        """
        Get configuration value.
        
        Args:
            section: Configuration section name
            key: Optional key within section
            default: Default value if not found
            
        Returns:
            Configuration value or default
        """
        try:
            if key is None:
                return self._config.get(section, default)
            else:
                section_config = self._config.get(section, {})
                return section_config.get(key, default)
        except Exception:
            return default
    
    def get_all(self) -> Dict:
        """
        Get all configuration as a dictionary.
        
        Returns:
            Complete configuration dictionary
        """
        return self._deep_copy_dict(self._config)
    
    def set(self, section: str, key: str, value: Any) -> None:
        """
        Set configuration value.
        
        Args:
            section: Configuration section name
            key: Key within section
            value: Value to set
        """
        if section not in self._config:
            self._config[section] = {}
        
        self._config[section][key] = value
        self.logger.info(f"Configuration updated: {section}.{key} = {value}")
    
    def save(self, config_path: Optional[Union[str, Path]] = None) -> None:
        """
        Save configuration to file.
        
        Args:
            config_path: Optional path to save to (defaults to current config path)
        """
        save_path = Path(config_path) if config_path else self.config_path
        
        try:
            # Ensure parent directory exists
            save_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(save_path, 'w', encoding='utf-8') as f:
                yaml.dump(self._config, f, default_flow_style=False, indent=2)
            
            self.logger.info(f"Configuration saved to {save_path}")
            
        except Exception as e:
            raise ConfigException(f"Failed to save configuration: {e}")
    
    def reload(self) -> None:
        """Reload configuration from file."""
        self._load_config()
        self.logger.info("Configuration reloaded")
    
    def get_api_config(self) -> Dict:
        """Get API configuration section."""
        return self.get('api', default={})
    
    def get_download_config(self) -> Dict:
        """Get download configuration section."""
        return self.get('download', default={})
    
    def get_storage_config(self) -> Dict:
        """Get storage configuration section."""
        return self.get('storage', default={})
    
    def get_logging_config(self) -> Dict:
        """Get logging configuration section."""
        return self.get('logging', default={})
    
    def validate_paths(self) -> None:
        """Validate that all configured paths are accessible."""
        paths_to_check = [
            ('storage', 'database_path'),
            ('download', 'output_directory'),
            ('logging', 'log_file')
        ]
        
        for section, key in paths_to_check:
            path_value = self.get(section, key)
            if path_value:
                path_obj = Path(path_value)
                
                # Create parent directories if they don't exist
                try:
                    if key == 'output_directory':
                        path_obj.mkdir(parents=True, exist_ok=True)
                    else:
                        path_obj.parent.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    self.logger.warning(f"Could not create directory for {section}.{key}: {e}")
    
    def get_env_info(self) -> Dict:
        """Get information about environment variable overrides."""
        env_info = {}
        
        env_mappings = {
            'ARXIV_API_BASE_URL': 'api.base_url',
            'ARXIV_API_MAX_RESULTS': 'api.max_results_per_query',
            'ARXIV_API_DELAY': 'api.request_delay',
            'ARXIV_DOWNLOAD_DIR': 'download.output_directory',
            'ARXIV_DOWNLOAD_THREADS': 'download.max_concurrent_downloads',
            'ARXIV_DATABASE_PATH': 'storage.database_path',
            'ARXIV_LOG_LEVEL': 'logging.level'
        }
        
        for env_var, config_key in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                env_info[env_var] = {
                    'config_key': config_key,
                    'value': env_value
                }
        
        return env_info
    
    def export_config(self, format: str = 'yaml') -> str:
        """
        Export configuration as string in specified format.
        
        Args:
            format: Export format ('yaml' or 'json')
            
        Returns:
            Configuration as formatted string
        """
        if format.lower() == 'yaml':
            return yaml.dump(self._config, default_flow_style=False, indent=2)
        elif format.lower() == 'json':
            import json
            return json.dumps(self._config, indent=2)
        else:
            raise ConfigException(f"Unsupported export format: {format}")
    
    def create_user_config_template(self, output_path: Union[str, Path]) -> None:
        """
        Create a user configuration template with comments.
        
        Args:
            output_path: Path where to create the template
        """
        template = '''# ArXiv Paper Crawler Configuration
# This file contains all configuration options for the ArXiv paper crawler

# ArXiv API settings
api:
  # Base URL for ArXiv API
  base_url: "http://export.arxiv.org/api/query"
  
  # Maximum results per API query (ArXiv limit is 2000)
  max_results_per_query: 100
  
  # Delay between API requests in seconds (minimum 3 seconds recommended)
  request_delay: 3.0
  
  # User agent string for API requests
  user_agent: "ArxivCrawler/1.0 (https://github.com/user/arxiv-crawler)"
  
  # Request timeout in seconds
  timeout: 30

# Download settings
download:
  # Directory where PDFs will be downloaded
  output_directory: "./downloaded_papers"
  
  # Maximum concurrent downloads
  max_concurrent_downloads: 5
  
  # Number of retry attempts for failed downloads
  retry_attempts: 3
  
  # Download timeout in seconds
  timeout: 60
  
  # Filename pattern for downloaded papers
  # Available variables: {year}, {first_author}, {title}, {arxiv_id}
  filename_pattern: "{year}_{first_author}_{title}"
  
  # Create subdirectories for each category
  create_category_folders: true

# Data storage settings
storage:
  # SQLite database path
  database_path: "./arxiv_papers.db"
  
  # Export formats to support
  export_formats:
    - "json"
    - "csv"
  
  # Automatically backup database before operations
  auto_backup: true

# Logging settings
logging:
  # Log level (DEBUG, INFO, WARNING, ERROR)
  level: "INFO"
  
  # Log file path
  log_file: "arxiv_crawler.log"
  
  # Maximum log file size
  max_file_size: "10MB"
  
  # Number of backup log files to keep
  backup_count: 3
'''
        
        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(template)
            
            self.logger.info(f"Configuration template created at {output_path}")
            
        except Exception as e:
            raise ConfigException(f"Failed to create configuration template: {e}")


# Global configuration instance
_config_manager = None


def get_config_manager(config_path: Union[str, Path] = 'config.yaml') -> ConfigManager:
    """
    Get the global configuration manager instance.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        ConfigManager instance
    """
    global _config_manager
    
    if _config_manager is None:
        _config_manager = ConfigManager(config_path)
    
    return _config_manager


def reload_config() -> None:
    """Reload the global configuration."""
    global _config_manager
    
    if _config_manager is not None:
        _config_manager.reload()


# Convenience functions for common configuration access
def get_api_config() -> Dict:
    """Get API configuration."""
    return get_config_manager().get_api_config()


def get_download_config() -> Dict:
    """Get download configuration."""
    return get_config_manager().get_download_config()


def get_storage_config() -> Dict:
    """Get storage configuration."""
    return get_config_manager().get_storage_config()


def get_logging_config() -> Dict:
    """Get logging configuration."""
    return get_config_manager().get_logging_config()
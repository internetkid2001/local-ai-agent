"""
Configuration Management

Handles loading, validation, and management of agent configuration
from YAML files and environment variables.

Author: Claude Code
Date: 2025-07-13
Session: 1.1
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ConfigValidationError(Exception):
    """Raised when configuration validation fails"""
    pass


class ConfigManager:
    """
    Manages agent configuration with validation and environment variable support.
    
    Features:
    - YAML configuration loading
    - Environment variable substitution
    - Configuration validation
    - Default value application
    - Live configuration reloading
    """
    
    def __init__(self, config_path: Optional[Union[str, Path]] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_path: Path to configuration file (optional)
        """
        self.config_path = self._resolve_config_path(config_path)
        self._config: Dict[str, Any] = {}
        self._defaults = self._get_default_config()
        
    def load(self) -> Dict[str, Any]:
        """
        Load configuration from file with validation.
        
        Returns:
            Loaded and validated configuration
            
        Raises:
            ConfigValidationError: If configuration is invalid
            FileNotFoundError: If config file not found
        """
        logger.info(f"Loading configuration from {self.config_path}")
        
        try:
            with open(self.config_path, 'r') as f:
                raw_config = yaml.safe_load(f)
            
            if not raw_config:
                logger.warning("Empty configuration file, using defaults")
                raw_config = {}
            
            # Apply environment variable substitution
            config = self._substitute_env_vars(raw_config)
            
            # Merge with defaults
            self._config = self._merge_with_defaults(config)
            
            # Validate configuration
            self._validate_config()
            
            logger.info("Configuration loaded successfully")
            return self._config
            
        except FileNotFoundError:
            logger.error(f"Configuration file not found: {self.config_path}")
            raise
            
        except yaml.YAMLError as e:
            logger.error(f"Invalid YAML in configuration file: {e}")
            raise ConfigValidationError(f"Invalid YAML: {e}")
            
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            raise ConfigValidationError(f"Configuration error: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value with dot notation support.
        
        Args:
            key: Configuration key (supports dot notation like 'llm.models.primary')
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self._config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any):
        """
        Set configuration value with dot notation support.
        
        Args:
            key: Configuration key
            value: Value to set
        """
        keys = key.split('.')
        config = self._config
        
        # Navigate to parent
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        # Set value
        config[keys[-1]] = value
        logger.debug(f"Configuration updated: {key} = {value}")
    
    def save(self, path: Optional[Union[str, Path]] = None):
        """
        Save current configuration to file.
        
        Args:
            path: Optional path to save to (defaults to current config path)
        """
        save_path = path or self.config_path
        
        try:
            with open(save_path, 'w') as f:
                yaml.safe_dump(self._config, f, default_flow_style=False, indent=2)
            
            logger.info(f"Configuration saved to {save_path}")
            
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
            raise
    
    def reload(self) -> Dict[str, Any]:
        """
        Reload configuration from file.
        
        Returns:
            Reloaded configuration
        """
        logger.info("Reloading configuration...")
        return self.load()
    
    def _resolve_config_path(self, config_path: Optional[Union[str, Path]]) -> Path:
        """Resolve configuration file path"""
        if config_path:
            return Path(config_path).expanduser().resolve()
        
        # Try common locations
        candidates = [
            Path.cwd() / "config" / "agent_config.yaml",
            Path.home() / ".config" / "ai-agent" / "config.yaml",
            Path(__file__).parent.parent.parent / "config" / "agent_config.yaml"
        ]
        
        for candidate in candidates:
            if candidate.exists():
                return candidate
        
        # Default to project config
        return Path(__file__).parent.parent.parent / "config" / "agent_config.yaml"
    
    def _substitute_env_vars(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Substitute environment variables in configuration"""
        def substitute_value(value):
            if isinstance(value, str):
                # Handle ${VAR} syntax
                if value.startswith('${') and value.endswith('}'):
                    var_name = value[2:-1]
                    env_value = os.getenv(var_name)
                    if env_value is not None:
                        return env_value
                    else:
                        logger.warning(f"Environment variable not found: {var_name}")
                        return value
                return value
            elif isinstance(value, dict):
                return {k: substitute_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [substitute_value(item) for item in value]
            else:
                return value
        
        return substitute_value(config)
    
    def _merge_with_defaults(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Merge configuration with defaults"""
        def deep_merge(default: Dict, override: Dict) -> Dict:
            result = default.copy()
            for key, value in override.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = deep_merge(result[key], value)
                else:
                    result[key] = value
            return result
        
        return deep_merge(self._defaults, config)
    
    def _validate_config(self):
        """Validate configuration structure and values"""
        required_sections = ['agent', 'llm', 'mcp_servers', 'security', 'logging']
        
        for section in required_sections:
            if section not in self._config:
                raise ConfigValidationError(f"Missing required section: {section}")
        
        # Validate LLM configuration
        llm_config = self._config.get('llm', {})
        required_llm_fields = ['provider', 'host', 'models']
        
        for field in required_llm_fields:
            if field not in llm_config:
                raise ConfigValidationError(f"Missing required LLM field: {field}")
        
        # Validate models
        models = llm_config.get('models', {})
        if 'primary' not in models:
            raise ConfigValidationError("Primary LLM model not specified")
        
        # Validate security settings
        security_config = self._config.get('security', {})
        if 'allowed_paths' not in security_config:
            raise ConfigValidationError("Security allowed_paths not configured")
        
        # Validate paths exist (expand user paths)
        allowed_paths = security_config.get('allowed_paths', [])
        for i, path in enumerate(allowed_paths):
            expanded_path = Path(path).expanduser()
            security_config['allowed_paths'][i] = str(expanded_path)
        
        logger.debug("Configuration validation passed")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration values"""
        return {
            'agent': {
                'name': 'Local AI Assistant',
                'version': '1.0.0'
            },
            'llm': {
                'provider': 'ollama',
                'host': 'http://localhost:11434',
                'models': {
                    'primary': 'llama3.1:8b',
                    'fallback': 'mistral:7b'
                },
                'context_window': 8192,
                'max_tokens': 2048,
                'temperature': {
                    'creative': 0.8,
                    'balanced': 0.5,
                    'precise': 0.2
                },
                'timeout': 30.0
            },
            'mcp_servers': {},
            'security': {
                'sandbox_enabled': True,
                'require_confirmation': True,
                'allowed_paths': ['~/Documents', '~/Downloads', '~/Desktop', '/tmp'],
                'forbidden_paths': ['/etc', '/sys', '/root', '~/.ssh'],
                'max_file_size_mb': 100
            },
            'logging': {
                'level': 'INFO',
                'file': '~/.local/share/ai-agent/agent.log',
                'max_size_mb': 100,
                'backup_count': 5
            },
            'performance': {
                'max_concurrent_tasks': 5,
                'task_timeout': 300,
                'memory_limit_mb': 1024
            }
        }


def load_config(config_path: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    """
    Convenience function to load configuration.
    
    Args:
        config_path: Optional path to configuration file
        
    Returns:
        Loaded configuration
    """
    manager = ConfigManager(config_path)
    return manager.load()
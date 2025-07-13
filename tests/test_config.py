"""
Unit Tests for Configuration Management

Tests for configuration loading, validation, and environment variable substitution.

Author: Claude Code
Date: 2025-07-13
Session: 1.1
"""

import pytest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import patch
import os

from src.utils.config import ConfigManager, ConfigValidationError, load_config


class TestConfigManager:
    """Test configuration manager functionality"""
    
    @pytest.fixture
    def temp_config_file(self):
        """Create temporary config file for testing"""
        config_data = {
            'agent': {
                'name': 'Test Agent',
                'version': '1.0.0'
            },
            'llm': {
                'provider': 'ollama',
                'host': 'http://localhost:11434',
                'models': {
                    'primary': 'llama3.1:8b',
                    'fallback': 'mistral:7b'
                },
                'timeout': 30.0
            },
            'security': {
                'sandbox_enabled': True,
                'allowed_paths': ['~/Documents', '~/Downloads'],
                'forbidden_paths': ['/etc', '/sys']
            },
            'logging': {
                'level': 'INFO',
                'file': '~/.local/share/ai-agent/test.log'
            },
            'mcp_servers': {
                'test_server': {
                    'enabled': True,
                    'url': 'ws://localhost:8000'
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.safe_dump(config_data, f)
            temp_file = Path(f.name)
        
        yield temp_file
        temp_file.unlink(missing_ok=True)
    
    @pytest.fixture
    def config_manager(self, temp_config_file):
        """Create config manager with temporary file"""
        return ConfigManager(temp_config_file)
    
    def test_config_loading(self, config_manager):
        """Test basic configuration loading"""
        config = config_manager.load()
        
        assert config['agent']['name'] == 'Test Agent'
        assert config['llm']['provider'] == 'ollama'
        assert config['security']['sandbox_enabled'] is True
        assert config['logging']['level'] == 'INFO'
    
    def test_get_with_dot_notation(self, config_manager):
        """Test getting values with dot notation"""
        config_manager.load()
        
        assert config_manager.get('agent.name') == 'Test Agent'
        assert config_manager.get('llm.models.primary') == 'llama3.1:8b'
        assert config_manager.get('nonexistent.key', 'default') == 'default'
    
    def test_set_with_dot_notation(self, config_manager):
        """Test setting values with dot notation"""
        config_manager.load()
        
        config_manager.set('agent.description', 'Test description')
        assert config_manager.get('agent.description') == 'Test description'
        
        config_manager.set('new.nested.value', 'test')
        assert config_manager.get('new.nested.value') == 'test'
    
    def test_environment_variable_substitution(self, temp_config_file):
        """Test environment variable substitution"""
        # Create config with environment variables
        config_data = {
            'llm': {
                'host': '${OLLAMA_HOST}',
                'api_key': '${API_KEY}'
            },
            'logging': {
                'level': '${LOG_LEVEL}'
            }
        }
        
        with open(temp_config_file, 'w') as f:
            yaml.safe_dump(config_data, f)
        
        # Set environment variables
        with patch.dict(os.environ, {
            'OLLAMA_HOST': 'http://custom-host:11434',
            'API_KEY': 'secret-key-123',
            'LOG_LEVEL': 'DEBUG'
        }):
            manager = ConfigManager(temp_config_file)
            config = manager.load()
            
            assert config['llm']['host'] == 'http://custom-host:11434'
            assert config['llm']['api_key'] == 'secret-key-123'
            assert config['logging']['level'] == 'DEBUG'
    
    def test_missing_environment_variable(self, temp_config_file):
        """Test handling of missing environment variables"""
        config_data = {
            'llm': {
                'host': '${MISSING_VAR}'
            }
        }
        
        with open(temp_config_file, 'w') as f:
            yaml.safe_dump(config_data, f)
        
        manager = ConfigManager(temp_config_file)
        config = manager.load()
        
        # Should keep original value when env var not found
        assert config['llm']['host'] == '${MISSING_VAR}'
    
    def test_config_validation_success(self, config_manager):
        """Test successful configuration validation"""
        # This should not raise any exceptions
        config = config_manager.load()
        assert config is not None
    
    def test_config_validation_missing_section(self, temp_config_file):
        """Test validation failure for missing required section"""
        # Create config missing required section
        config_data = {
            'agent': {'name': 'Test'},
            # Missing 'llm' section
            'security': {'sandbox_enabled': True, 'allowed_paths': []},
            'logging': {'level': 'INFO'},
            'mcp_servers': {}
        }
        
        with open(temp_config_file, 'w') as f:
            yaml.safe_dump(config_data, f)
        
        manager = ConfigManager(temp_config_file)
        
        with pytest.raises(ConfigValidationError, match="Missing required section: llm"):
            manager.load()
    
    def test_config_validation_missing_llm_field(self, temp_config_file):
        """Test validation failure for missing LLM field"""
        config_data = {
            'agent': {'name': 'Test'},
            'llm': {
                'provider': 'ollama',
                # Missing 'host' and 'models'
            },
            'security': {'sandbox_enabled': True, 'allowed_paths': []},
            'logging': {'level': 'INFO'},
            'mcp_servers': {}
        }
        
        with open(temp_config_file, 'w') as f:
            yaml.safe_dump(config_data, f)
        
        manager = ConfigManager(temp_config_file)
        
        with pytest.raises(ConfigValidationError, match="Missing required LLM field"):
            manager.load()
    
    def test_config_validation_missing_primary_model(self, temp_config_file):
        """Test validation failure for missing primary model"""
        config_data = {
            'agent': {'name': 'Test'},
            'llm': {
                'provider': 'ollama',
                'host': 'http://localhost:11434',
                'models': {
                    'fallback': 'mistral:7b'
                    # Missing 'primary'
                }
            },
            'security': {'sandbox_enabled': True, 'allowed_paths': []},
            'logging': {'level': 'INFO'},
            'mcp_servers': {}
        }
        
        with open(temp_config_file, 'w') as f:
            yaml.safe_dump(config_data, f)
        
        manager = ConfigManager(temp_config_file)
        
        with pytest.raises(ConfigValidationError, match="Primary LLM model not specified"):
            manager.load()
    
    def test_config_save(self, config_manager, temp_config_file):
        """Test configuration saving"""
        config_manager.load()
        config_manager.set('agent.description', 'Modified agent')
        
        # Save to new file
        new_file = temp_config_file.with_suffix('.new.yaml')
        try:
            config_manager.save(new_file)
            
            # Load from new file and verify
            new_manager = ConfigManager(new_file)
            new_config = new_manager.load()
            assert new_config['agent']['description'] == 'Modified agent'
            
        finally:
            new_file.unlink(missing_ok=True)
    
    def test_config_reload(self, config_manager, temp_config_file):
        """Test configuration reloading"""
        # Load initial config
        config1 = config_manager.load()
        original_name = config1['agent']['name']
        
        # Modify file externally
        config_data = yaml.safe_load(temp_config_file.read_text())
        config_data['agent']['name'] = 'Modified Name'
        temp_config_file.write_text(yaml.safe_dump(config_data))
        
        # Reload and verify changes
        config2 = config_manager.reload()
        assert config2['agent']['name'] == 'Modified Name'
        assert config2['agent']['name'] != original_name
    
    def test_invalid_yaml(self, temp_config_file):
        """Test handling of invalid YAML"""
        # Write invalid YAML
        temp_config_file.write_text("invalid: yaml: content: [")
        
        manager = ConfigManager(temp_config_file)
        
        with pytest.raises(ConfigValidationError, match="Invalid YAML"):
            manager.load()
    
    def test_nonexistent_config_file(self):
        """Test handling of nonexistent config file"""
        manager = ConfigManager("/nonexistent/config.yaml")
        
        with pytest.raises(FileNotFoundError):
            manager.load()
    
    def test_empty_config_file(self, temp_config_file):
        """Test handling of empty config file"""
        temp_config_file.write_text("")
        
        manager = ConfigManager(temp_config_file)
        config = manager.load()
        
        # Should load defaults
        assert 'agent' in config
        assert config['agent']['name'] == 'Local AI Assistant'
    
    def test_default_config_merge(self, temp_config_file):
        """Test merging with default configuration"""
        # Minimal config
        config_data = {
            'agent': {'name': 'Custom Agent'},
            'llm': {
                'provider': 'custom',
                'host': 'http://custom:11434',
                'models': {'primary': 'custom:latest'}
            },
            'security': {'allowed_paths': []},
            'logging': {'level': 'ERROR'},
            'mcp_servers': {}
        }
        
        with open(temp_config_file, 'w') as f:
            yaml.safe_dump(config_data, f)
        
        manager = ConfigManager(temp_config_file)
        config = manager.load()
        
        # Should have custom values
        assert config['agent']['name'] == 'Custom Agent'
        assert config['llm']['provider'] == 'custom'
        
        # Should have default values for missing fields
        assert config['llm']['context_window'] == 8192  # From defaults
        assert config['security']['sandbox_enabled'] is True  # From defaults
    
    def test_path_expansion(self, config_manager):
        """Test user path expansion in configuration"""
        config = config_manager.load()
        
        # Check that paths are expanded
        allowed_paths = config['security']['allowed_paths']
        for path in allowed_paths:
            # Should be absolute paths (expanded)
            assert not path.startswith('~')


class TestLoadConfigFunction:
    """Test the convenience load_config function"""
    
    def test_load_config_function(self, temp_config_file):
        """Test load_config convenience function"""
        config = load_config(temp_config_file)
        
        assert config['agent']['name'] == 'Test Agent'
        assert 'llm' in config
        assert 'security' in config
    
    def test_load_config_no_path(self):
        """Test load_config with no path (should find default)"""
        # This will try to find config in default locations
        # In test environment, it may not find anything, so we expect an error
        with pytest.raises(FileNotFoundError):
            load_config()


class TestConfigResolution:
    """Test configuration file path resolution"""
    
    def test_explicit_path_resolution(self, temp_config_file):
        """Test explicit path resolution"""
        manager = ConfigManager(str(temp_config_file))
        assert manager.config_path == temp_config_file
    
    def test_user_path_expansion(self):
        """Test user path expansion"""
        manager = ConfigManager("~/test_config.yaml")
        expected_path = Path.home() / "test_config.yaml"
        assert manager.config_path == expected_path
    
    @patch('pathlib.Path.exists')
    def test_default_path_search(self, mock_exists):
        """Test default configuration path search"""
        # Mock that no config files exist
        mock_exists.return_value = False
        
        manager = ConfigManager()
        
        # Should default to project config path
        expected_path = Path(__file__).parent.parent / "config" / "agent_config.yaml"
        assert manager.config_path.name == "agent_config.yaml"
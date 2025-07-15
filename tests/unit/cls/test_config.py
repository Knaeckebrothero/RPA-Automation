"""
Unit tests for the ConfigHandler class.

This module contains tests for the ConfigHandler class functionality, including
configuration file management, value retrieval, and error handling.
"""
import os
import configparser
import pytest
from unittest.mock import patch, mock_open, MagicMock

from cls.config import ConfigHandler


class TestConfigHandler:
    """Test suite for the ConfigHandler class."""

    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_init_with_existing_config(self, mock_file, mock_exists):
        """Test initialization when config file exists."""
        # Mock that the config file exists
        mock_exists.return_value = True
        
        # Mock the config file content
        mock_file.return_value.read.return_value = """
        [APP_SETTINGS]
        certificate_template_path = test_path/certificate.docx
        terms_conditions_path = test_path/terms.pdf
        archive_file_prefix = test_prefix
        """
        
        # Create a ConfigHandler instance
        with patch.object(ConfigHandler, 'load') as mock_load:
            handler = ConfigHandler(config_path="test_config.cfg")
            
            # Verify that load was called
            mock_load.assert_called_once()
            
            # Verify the config path was set correctly
            assert handler.config_path == "test_config.cfg"

    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_init_with_new_config(self, mock_file, mock_exists):
        """Test initialization when config file doesn't exist."""
        # Mock that the config file doesn't exist
        mock_exists.return_value = False
        
        # Create a ConfigHandler instance
        with patch.object(ConfigHandler, '_create_default_config') as mock_create:
            handler = ConfigHandler(config_path="test_config.cfg")
            
            # Verify that _create_default_config was called
            mock_create.assert_called_once()
            
            # Verify the config path was set correctly
            assert handler.config_path == "test_config.cfg"

    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    @patch.dict('os.environ', {'FILESYSTEM_PATH': '/custom/path'})
    def test_create_default_config(self, mock_file, mock_exists):
        """Test creating a default configuration file."""
        # Mock that the config file doesn't exist
        mock_exists.return_value = False
        
        # Create a ConfigHandler instance
        handler = ConfigHandler(config_path="test_config.cfg")
        
        # Call the method directly to test it
        handler._create_default_config()
        
        # Verify that the file was opened for writing
        mock_file.assert_called_with("test_config.cfg", 'w')
        
        # Verify that the config was written to the file
        mock_file().write.assert_called()
        
        # Verify that the default values were set correctly
        assert 'APP_SETTINGS' in handler.config
        assert handler.config['APP_SETTINGS']['certificate_template_path'] == '/custom/path/certificate_template.docx'
        assert handler.config['APP_SETTINGS']['terms_conditions_path'] == '/custom/path/terms_conditions.pdf'
        assert handler.config['APP_SETTINGS']['archive_file_prefix'] == 'audit_archive'

    @patch('configparser.ConfigParser.read')
    def test_load_success(self, mock_read):
        """Test loading configuration successfully."""
        # Create a ConfigHandler instance
        with patch('os.path.exists', return_value=True):
            handler = ConfigHandler(config_path="test_config.cfg")
            
            # Reset the mock to clear the call from initialization
            mock_read.reset_mock()
            
            # Call the load method
            handler.load()
            
            # Verify that read was called with the correct path
            mock_read.assert_called_once_with("test_config.cfg")

    @patch('configparser.ConfigParser.read')
    def test_load_with_missing_section(self, mock_read):
        """Test loading configuration with a missing required section."""
        # Create a ConfigHandler instance
        with patch('os.path.exists', return_value=True):
            handler = ConfigHandler(config_path="test_config.cfg")
            
            # Remove the APP_SETTINGS section
            handler.config.remove_section('APP_SETTINGS')
            
            # Call the load method
            with patch.object(handler, 'save') as mock_save:
                handler.load()
                
                # Verify that the section was added and save was called
                assert 'APP_SETTINGS' in handler.config
                mock_save.assert_called_once()

    @patch('configparser.ConfigParser.read')
    def test_load_with_error(self, mock_read):
        """Test loading configuration with an error."""
        # Mock read to raise an exception
        mock_read.side_effect = Exception("Test error")
        
        # Create a ConfigHandler instance
        with patch('os.path.exists', return_value=True):
            handler = ConfigHandler(config_path="test_config.cfg")
            
            # Reset the mock to clear the call from initialization
            mock_read.reset_mock()
            
            # Call the load method
            with patch.object(handler, '_create_default_config') as mock_create:
                handler.load()
                
                # Verify that _create_default_config was called
                mock_create.assert_called_once()

    @patch('builtins.open', new_callable=mock_open)
    def test_save_success(self, mock_file):
        """Test saving configuration successfully."""
        # Create a ConfigHandler instance
        with patch('os.path.exists', return_value=True):
            handler = ConfigHandler(config_path="test_config.cfg")
            
            # Call the save method
            handler.save()
            
            # Verify that the file was opened for writing
            mock_file.assert_called_with("test_config.cfg", 'w')
            
            # Verify that write was called
            mock_file().write.assert_called()

    @patch('builtins.open')
    def test_save_with_error(self, mock_open):
        """Test saving configuration with an error."""
        # Mock open to raise an exception
        mock_open.side_effect = Exception("Test error")
        
        # Create a ConfigHandler instance
        with patch('os.path.exists', return_value=True):
            handler = ConfigHandler(config_path="test_config.cfg")
            
            # Call the save method
            result = handler.save()
            
            # Verify that the method handled the error gracefully
            # (no assertion needed as we're just testing it doesn't raise an exception)

    def test_get_existing_value(self):
        """Test getting an existing configuration value."""
        # Create a ConfigHandler instance
        with patch('os.path.exists', return_value=True):
            handler = ConfigHandler(config_path="test_config.cfg")
            
            # Set a test value
            handler.config['TEST_SECTION'] = {'test_key': 'test_value'}
            
            # Get the value
            value = handler.get('TEST_SECTION', 'test_key')
            
            # Verify the value
            assert value == 'test_value'

    def test_get_missing_section(self):
        """Test getting a value from a missing section."""
        # Create a ConfigHandler instance
        with patch('os.path.exists', return_value=True):
            handler = ConfigHandler(config_path="test_config.cfg")
            
            # Get a value from a missing section
            value = handler.get('MISSING_SECTION', 'test_key', default='default_value')
            
            # Verify the default value was returned
            assert value == 'default_value'

    def test_get_missing_key(self):
        """Test getting a missing key from an existing section."""
        # Create a ConfigHandler instance
        with patch('os.path.exists', return_value=True):
            handler = ConfigHandler(config_path="test_config.cfg")
            
            # Set up a section without the key we'll request
            handler.config['TEST_SECTION'] = {'other_key': 'other_value'}
            
            # Get a missing key
            value = handler.get('TEST_SECTION', 'missing_key', default='default_value')
            
            # Verify the default value was returned
            assert value == 'default_value'

    def test_get_with_error(self):
        """Test getting a value with an error."""
        # Create a ConfigHandler instance
        with patch('os.path.exists', return_value=True):
            handler = ConfigHandler(config_path="test_config.cfg")
            
            # Mock the config to raise an exception when accessed
            handler.config = MagicMock()
            handler.config.__getitem__.side_effect = Exception("Test error")
            
            # Get a value
            value = handler.get('TEST_SECTION', 'test_key', default='default_value')
            
            # Verify the default value was returned
            assert value == 'default_value'

    @patch('builtins.open', new_callable=mock_open)
    def test_set_existing_section(self, mock_file):
        """Test setting a value in an existing section."""
        # Create a ConfigHandler instance
        with patch('os.path.exists', return_value=True):
            handler = ConfigHandler(config_path="test_config.cfg")
            
            # Set up an existing section
            handler.config['TEST_SECTION'] = {'existing_key': 'existing_value'}
            
            # Set a new value
            result = handler.set('TEST_SECTION', 'test_key', 'test_value')
            
            # Verify the result
            assert result is True
            
            # Verify the value was set
            assert handler.config['TEST_SECTION']['test_key'] == 'test_value'
            
            # Verify that save was called
            mock_file.assert_called_with("test_config.cfg", 'w')

    @patch('builtins.open', new_callable=mock_open)
    def test_set_new_section(self, mock_file):
        """Test setting a value in a new section."""
        # Create a ConfigHandler instance
        with patch('os.path.exists', return_value=True):
            handler = ConfigHandler(config_path="test_config.cfg")
            
            # Set a value in a new section
            result = handler.set('NEW_SECTION', 'test_key', 'test_value')
            
            # Verify the result
            assert result is True
            
            # Verify the section and value were created
            assert 'NEW_SECTION' in handler.config
            assert handler.config['NEW_SECTION']['test_key'] == 'test_value'
            
            # Verify that save was called
            mock_file.assert_called_with("test_config.cfg", 'w')

    def test_set_with_error(self):
        """Test setting a value with an error."""
        # Create a ConfigHandler instance
        with patch('os.path.exists', return_value=True):
            handler = ConfigHandler(config_path="test_config.cfg")
            
            # Mock the config to raise an exception when accessed
            handler.config = MagicMock()
            handler.config.__setitem__.side_effect = Exception("Test error")
            
            # Set a value
            result = handler.set('TEST_SECTION', 'test_key', 'test_value')
            
            # Verify the result
            assert result is False
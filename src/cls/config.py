# In a new file: src/workflow/config_handler.py
"""
This module handles configuration file reading and writing.
"""
import os
import configparser
import logging


# Set up logging
log = logging.getLogger(__name__)


class ConfigHandler:
    """
    Handles reading and writing to the application configuration file.
    """
    _instance = None

    @classmethod
    def get_instance(cls):
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = ConfigHandler()
        return cls._instance

    def __init__(self, config_path="src/config.cfg"):
        """
        Initialize the config handler.

        :param config_path: Path to the configuration file
        """
        self.config_path = config_path
        self.config = configparser.ConfigParser()

        # Create default config if it doesn't exist
        if not os.path.exists(config_path):
            self._create_default_config()
        else:
            self.load()

    def _create_default_config(self):
        """Create a default configuration file if none exists."""
        # Create sections
        self.config['APP_SETTINGS'] = {
            'certificate_template_path': os.path.join(os.getenv('FILESYSTEM_PATH', './.filesystem'),
                                                      "certificate_template.docx"),
            'archive_file_prefix': 'audit_archive'
        }

        # Write to file
        with open(self.config_path, 'w') as configfile:
            self.config.write(configfile)

        log.info(f"Created default configuration file at {self.config_path}")

    def load(self):
        """Load the configuration from file."""
        try:
            self.config.read(self.config_path)
            log.debug(f"Loaded configuration from {self.config_path}")

            # Ensure required sections exist
            if 'APP_SETTINGS' not in self.config:
                self.config['APP_SETTINGS'] = {}
                self.save()

        except Exception as e:
            log.error(f"Error loading configuration: {str(e)}")
            # Create a new default config
            self._create_default_config()

    def save(self):
        """Save the configuration to file."""
        try:
            with open(self.config_path, 'w') as configfile:
                self.config.write(configfile)
            log.debug(f"Saved configuration to {self.config_path}")
        except Exception as e:
            log.error(f"Error saving configuration: {str(e)}")

    def get(self, section, key, default=None):
        """
        Get a configuration value.

        :param section: Configuration section
        :param key: Configuration key
        :param default: Default value if key doesn't exist
        :return: Configuration value or default
        """
        try:
            if section in self.config and key in self.config[section]:
                return self.config[section][key]
            return default
        except Exception as e:
            log.error(f"Error getting configuration value {section}.{key}: {str(e)}")
            return default

    def set(self, section, key, value):
        """
        Set a configuration value.

        :param section: Configuration section
        :param key: Configuration key
        :param value: Value to set
        """
        try:
            if section not in self.config:
                self.config[section] = {}

            self.config[section][key] = value
            self.save()
            log.debug(f"Set configuration value {section}.{key} = {value}")
            return True
        except Exception as e:
            log.error(f"Error setting configuration value {section}.{key}: {str(e)}")
            return False

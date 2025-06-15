"""
This module handles configuration file reading and writing.
"""
import os
import configparser
import logging

# Custom imports
from cls.singleton import Singleton


# Set up logging
log = logging.getLogger(__name__)


class ConfigHandler(Singleton):
    """
    Handles configuration management for the application.

    This class is responsible for managing application configuration through
    a configuration file. It includes methods to load, save, and modify
    configuration values, ensuring that default settings are created when
    the configuration file does not exist.

    :ivar config_path: Path to the configuration file.
    :type config_path: str
    :ivar config: Configuration parser instance that manages sections and
        key-value pairs.
    :type config: configparser.ConfigParser
    """
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
        """
        Creates a default configuration file with predefined application settings.
        This configuration file includes paths for the certificate template,
        terms and conditions, and an archive file prefix. These paths utilize
        environment variables or default to relative paths if the variables
        are not set. The generated configuration file is saved to the defined
        `config_path` for the application.

        :raises EnvironmentError: In case of issues accessing the filesystem path
            or writing to the configuration file.
        """
        self.config['APP_SETTINGS'] = {
            'certificate_template_path': os.path.join(os.getenv('FILESYSTEM_PATH', './.filesystem'),
                                                      "certificate_template.docx"),
            'terms_conditions_path': os.path.join(os.getenv('FILESYSTEM_PATH', './.filesystem'),
                                                  "terms_conditions.pdf"),
            'archive_file_prefix': 'audit_archive'
        }

        # Write to file
        with open(self.config_path, 'w') as configfile:
            self.config.write(configfile)

        log.info(f"Created default configuration file at {self.config_path}")

    def load(self):
        """
        Loads the configuration from the specified configuration file. Ensures that required
        sections exist in the configuration. If any error occurs during loading, logs the
        error and creates a default configuration file if necessary.

        :raises Exception: If an issue occurs when reading the configuration file.
        """
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
        """
        Saves the current state of the configuration to the specified file path.

        This method attempts to write the configuration data to a file at the location
        specified by the `self.config_path` attribute. If the operation is successful,
        a debug log entry indicates the success. In case of an error, it logs the error
        message to assist with debugging.

        :raises OSError: If there is an error accessing or writing to the file system.
        :raises Exception: If any other exception occurs during the save operation.
        """
        try:
            with open(self.config_path, 'w') as configfile:
                self.config.write(configfile)
            log.debug(f"Saved configuration to {self.config_path}")
        except Exception as e:
            log.error(f"Error saving configuration: {str(e)}")

    def get(self, section, key, default=None):
        """
        Retrieves the value from a nested configuration dictionary structure based on a given
        section and key. It first checks if the specified section exists within
        the configuration. If the section exists, it further checks if the specified key exists
        within the section. If both exist, it returns the value corresponding to the key within
        the section. If either the section or key is missing, or an exception occurs,
        it returns a default value.

        :param section: The top-level section of the configuration dictionary to search.
        :type section: str
        :param key: The specific key within the section for which to retrieve the value.
        :type key: str
        :param default: The default value to return if the section or key is not found,
            or if an error occurs. Defaults to None.
        :return: The configuration value retrieved from the specified section and key,
            or the default value if not found.
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
        Sets a configuration value under a specific section and key, saving the changes
        to the configuration, and logging the operation or any errors that occur.

        :param section: The section in which the configuration value is to be set.
        :type section: str
        :param key: The key under the specified section where the value is assigned.
        :type key: str
        :param value: The configuration value to be set for the provided key.
        :return: Boolean indicating whether the operation was successful.
        :rtype: bool
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

"""
This module holds the filehandler class used to interact with the file system.
"""
import os
# Custom imports
from src.config.singleton import Singleton
from src.config.custom_logger import configure_custom_logger


class Filehandler(Singleton):
    """
    This class is used to interact with the file system.

    It uses the Singleton pattern to ensure that only one instance of the class is created.
    """

    def __init__(self, base_path: str = None, *args, **kwargs):
        """
        Constructor for the filehandler class.
        """
        self.logger = configure_custom_logger(__name__)
        self.base_path = base_path if base_path else './filesystem/'

        self.logger.info("Filehandler initialized.")

    def __del__(self):
        """
        Destructor for the filehandler class.

        """
        self.logger.info('Filehandler destroyed.')

    def create_file(self, file_name: str, path: str, content: str | bytes):
        """
        Create a file with the given name and content.


        :param file_name: The name of the file to create.
        :param path: The path to the file.
        :param content: The content to write to the file.
        """
        try:
            if os.path.exists(self.base_path + path + file_name):
                self.logger.warning(f"File {file_name} already exists.")
                return

            if not os.path.exists(self.base_path + path + '/'):
                os.makedirs(self.base_path + path + '/')
                self.logger.debug(f"Path {path} created.")

            with open(self.base_path + path + file_name, 'w') as file:
                file.write(content)
                self.logger.info(f"File {file_name} created.")

        except Exception as e:
            self.logger.error(f"Error: {e} while attempting to create file: {file_name}.")

    def read_file(self, file_name: str, path: str):
        """
        Read the content of a file.

        :param file_name: The name of the file to read.
        :param path: The path to the file.
        """
        with open(self.base_path + path + file_name, 'r') as file:
            try:
                content = file.read()
                self.logger.debug(f"File {file_name} read.")
                return content

            except Exception as e:
                self.logger.error(f"Error: {e} while attempting to read file: {file_name}.")
                return None

    def update_file(self, file_name: str, path: str, content: str | bytes):
        """
        Update the content of a file.

        :param file_name: The name of the file to update.
        :param path: The path to the file.
        :param content: The content to write to the file.
        """
        try:
            with open(self.base_path + path + file_name, 'w') as file:
                file.write(content)
                self.logger.info(f"File {file_name} updated.")

        except Exception as e:
            self.logger.error(f"Error: {e} while attempting to update file: {file_name}.")

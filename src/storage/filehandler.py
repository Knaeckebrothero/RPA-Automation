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
        self.logger = configure_custom_logger(
            module_name='filehandler',
            console_level=int(os.getenv('LOG_LEVEL_CONSOLE')),
            file_level=int(os.getenv('LOG_LEVEL_FILE')),
            logging_directory=os.getenv('LOG_PATH') if os.getenv('LOG_PATH') else None
        )
        self.logger.debug('Logger initialized')

        # Set the base path for the filehandler and ensure that it exists
        self.base_path = base_path if base_path else './filesystem/'
        if not self.base_path.endswith('/'):
            self.base_path += '/'
        self._ensure_directory()

        # Scan the directory for files and store them in a list
        self.files = self._scan_directory()

        self.logger.info("Filehandler initialized, base path: " + self.base_path)

    def __del__(self):
        """
        Destructor for the filehandler class.
        """
        self.logger.info('Filehandler destroyed.')
        # TODO: Implement saving of self.files to database

    def create_file(self, path: str, file_name: str, content: str | bytes):
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

    def read_file(self, path: str, file_name: str):
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

    def update_file(self, path: str, file_name: str, content: str | bytes):
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

    def delete_file(self, file_name: str, path: str):
        """
        Delete a file.

        :param file_name: The name of the file to delete.
        :param path: The path to the file.
        """
        try:
            os.remove(self.base_path + path + file_name)
            self.logger.info(f"File {file_name} deleted.")

        except Exception as e:
            self.logger.error(f"Error: {e} while attempting to delete file: {file_name}.")

    def _ensure_directory(self, path: str = None):
        """
        Ensure that the directory exists.

        :param path: The path to the directory.
        """
        if path is None:
            path = ''
        if not path.endswith('/'):
            path += '/'

        # Ensure that the path exists within the base directory
        try:
            if not os.path.exists(self.base_path + path):
                os.makedirs(self.base_path + path)
                self.logger.debug(f"Path {path} created.")
            elif not os.path.exists(self.base_path):
                self.logger.debug(f"Issue with base path: {self.base_path}")
            else:
                self.logger.debug(f"Path {path} already exists.")

        except Exception as e:
            self.logger.error(f"Error: {e} while attempting to create directory: {path}.")

    def _scan_directory(self) -> list[str]:
        """
        Scan the directory and return a list of all files.

        :return: A list of string paths for all files in the directory.
        """
        files = []
        try:
            for root, _, file_list in os.walk(self.base_path):
                for file in file_list:
                    files.append(os.path.join(root, file))

            self.logger.debug("Directory scan ran successfully")

        except Exception as e:
            self.logger.error(f"Error: {e} while attempting to scan directory")

        finally:
            self.logger.debug("Done scanning directory")
            return files

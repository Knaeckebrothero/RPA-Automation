"""
This module holds the email class.
"""
import os
import preprocessing.preprocessing as prp
# Custom imports
from cfg.custom_logger import configure_custom_logger
from document import Document


class Email(Document):
    """
    The Email class represents an email document.
    """
    _logger = None


    def __init__(self, content: bytes, attributes: dict = None):
        """
        The constructor for the Document class.

        :param content: The raw content of the document.
        :param attributes: A set of attributes for the document.
        """
        if not Document._logger:
            Document._logger = configure_custom_logger(
                module_name=__name__,
                console_level=int(os.getenv('LOG_LEVEL_CONSOLE')),
                file_level=int(os.getenv('LOG_LEVEL_FILE')),
                logging_directory=os.getenv('LOG_PATH')
            )
            Document._logger.debug('Logger initialized')

        # Initialize the class
        super().__init__(content, attributes)
        self._header = None
        self._body = None
        self._attachments = None
        self._sender = None
        self._receiver = None

        Document._logger.debug(f"Email created: {len(self._content)}, {len(self._attributes.keys())}")

# ToDo: Implement the Email class

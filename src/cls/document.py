"""
This module holds the document class.
"""
import os
# Custom imports
import preprocessing.preprocessing as prp
from cfg.custom_logger import configure_custom_logger


class Document:
    """
    The Document class represents a document.
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
        self._content: bytes = content
        self._attributes: dict = attributes if attributes else {}
        Document._logger.debug(f"Document created: {len(self._content)}, {len(self._attributes.keys())}")

    def __str__(self):
        string_form = (f"Document: of size {len(self._content)} bytes, with: {len(self._attributes.keys())} "
                       f"number of attributes.")
        return string_form

    def get_content(self) -> bytes:
        return self._content

    def get_attributes(self, attributes: str | list[str] = None) -> dict:
        """
        Get the attributes of the document.
        If a list of attributes is provided, only those attributes will be returned.

        :param attributes: Optional list of attributes to return.
        :return: All attributes of the document. Or only the attributes in the list.
        """
        if attributes and isinstance(attributes, list):
            return {key: value for key, value in self._attributes.items() if key in attributes}
        elif attributes and isinstance(attributes, str):
            return {attributes: self._attributes[attributes]}
        else:
            return self._attributes

    def add_attributes(self, attributes: dict):
        """
        Set the attributes of the document.

        :param attributes: The attributes to be set.
        """
        self._attributes.update(attributes)

    def update_attributes(self, attributes: dict):
        """
        Update the attributes of the document.

        :param attributes: The attributes to be updated.
        """
        self._attributes.update(attributes)

    def delete_attributes(self, attributes: list[str] = None):
        """
        Delete the attributes of the document.

        :param attributes: The attributes to be deleted.
        """
        if attributes:
            for attribute in attributes:
                self._attributes.pop(attribute)
        else:
            self._attributes.clear()

    def extract_table_attributes(self):
        """
        Extract the text from the document.
        """
        document_images = prp.get_images_from_pdf(self._content)

        for image in document_images:
            tables = prp.detect_tables(image)
            for table in tables:
                import streamlit  # TODO: Continue implementation
                streamlit.image(table)

"""
This module holds the document class.
"""
import cv2
import numpy as np
import logging
from pdf2image import convert_from_bytes

# Custom imports
import preprocessing.preprocessing as prp
from preprocessing.ocr import ocr_cell


# Set up logging
log  = logging.getLogger(__name__)


class Document:
    """
    The Document class represents a document.
    """

    def __init__(self, content: bytes, attributes: dict = None):
        """
        The constructor for the Document class.

        :param content: The raw content of the document.
        :param attributes: A set of attributes for the document.
        """
        self._content: bytes = content
        self._attributes: dict = attributes if attributes else {}
        log.debug(f"Document created: {len(self._content)}, {len(self._attributes.keys())}")

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

    def extract_table_data(self):
        """
        Extract the text from the document.
        """
        if self._content:
            images = convert_from_bytes(self._content)

            for i, image in enumerate(images):
                np_image = np.array(image)
                bgr_image = cv2.cvtColor(np_image, cv2.COLOR_RGB2BGR)

                # Detect tables
                table_contours = prp.detect_tables(bgr_image)
                log.debug(f"Number of tables detected on page {i + 1}: {len(table_contours)}")

                # Process each detected table
                for j, contour in enumerate(table_contours):
                    x, y, w, h = cv2.boundingRect(contour)
                    table_roi = bgr_image[y:y + h, x:x + w]

                    log.debug(f"Table {j + 1} on Page {i + 1}")

                    # Detect rows in the table
                    rows = prp.detect_rows(table_roi)
                    log.debug(f"Number of rows detected: {len(rows)}")

                    table_data = []

                    # Process each detected row
                    for k, (y1, y2) in enumerate(rows):
                        row_image = table_roi[y1:y2, :]

                        # Detect cells in the row
                        cells = prp.detect_cells(row_image)
                        log.debug(f"Number of cells detected: {len(cells)}")

                        row_data = []
                        for m, (x1, x2) in enumerate(cells):
                            cell_image = row_image[:, x1:x2]
                            cell_text = ocr_cell(cell_image)
                            row_data.append(cell_text)

                        table_data.append(row_data)

                        # Display extracted data in a Streamlit table
                        log.info("Extracted Table Data")
                        log.debug(table_data)

"""
This module holds the document class.
"""
import cv2
import numpy as np
import logging
from pdf2image import convert_from_bytes
import re

# Custom imports
import preprocessing.detect as dct
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

    def get_attributes(self, key_or_keys: str | list[str] = None) -> dict | str | None:
        """
        Get the attributes of the document.
        If a list of attributes is provided, only those attributes will be returned.

        :param key_or_keys: Optional list of attribute keys to return.
        :return: All attributes of the document. Or only the attributes in the list.
        """
        try:
            if key_or_keys and isinstance(key_or_keys, list):
                rtn_keys = {key: value for key, value in self._attributes.items() if key in key_or_keys}
                return rtn_keys if len(rtn_keys) >= 1 else None
            elif key_or_keys and isinstance(key_or_keys, str):
                return self._attributes[key_or_keys]
            else:
                if len(self._attributes) >= 1:
                    return self._attributes
                else:
                    return None
        except KeyError as e:
            log.error(f"KeyError: {e}")
            return None

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
            # Convert the PDF document into a list of images (one image per page)
            images = convert_from_bytes(self._content)
            log.debug(f"Number of pages in the document: {len(images)}")

            # Loop through each page of the document
            for i, image in enumerate(images):
                # Convert the image to a NumPy array (shape is height times width times RGB channels)
                np_image = np.array(image)

                # Convert to BGR format since it is required for OpenCV (BGR is basically RGB reversed)
                bgr_image = cv2.cvtColor(np_image, cv2.COLOR_RGB2BGR)

                # Detect tables in the image
                table_contours = dct.tables(bgr_image)

                # Process each detected table
                for j, contour in enumerate(table_contours):
                    x, y, w, h = cv2.boundingRect(contour)
                    table_roi = bgr_image[y:y + h, x:x + w]
                    log.debug(f"Table {j + 1} on Page {i + 1}")

                    # Detect rows in the table
                    rows = dct.rows(table_roi)
                    log.debug(f"Number of rows detected: {len(rows)}")

                    # Process each detected row
                    for k, (y1, y2) in enumerate(rows):
                        row_data = []

                        # Crop the row from the table
                        row_image = table_roi[y1:y2, :]
                        log.debug(f"Row {k + 1} on Page {i + 1}")

                        # Detect cells in the row
                        cells = dct.cells(row_image)

                        # Process each detected cell
                        for m, (x1, x2) in enumerate(cells):
                            # Crop the cell from the row
                            cell_image = row_image[:, x1:x2]

                            # Extract and append the text from the cell
                            cell_text = ocr_cell(cell_image)
                            row_data.append(cell_text)

                        # Log and add the extracted row data to the attributes
                        log.debug(f"Row {k + 1} Data: {row_data}")

                        # Three columns
                        if len(row_data) > 2:
                            # Combine the first two columns into one key and add the third column as the value
                            if (row_data[0], row_data[1], row_data[2]) != '':
                                #self.add_attributes({row_data[0] + ", " + row_data[1] : row_data[2]})
                                self.add_attributes({row_data[1].strip() : row_data[2].strip()})
                            # Add the total sum of the table as an attribute
                            elif row_data[0] == 'Gesamtsumme' and row_data[2] != '':
                                self.add_attributes({'Gesamtsumme': row_data[2].strip()})
                                # TODO: Why is this not working?
                        # Two columns
                        elif len(row_data) == 2:
                            # Use the first column as the key and the second column as the value
                            if row_data[0] != '':
                                self.add_attributes({row_data[0].strip() : row_data[1].strip()})
                        # One column
                        elif len(row_data) == 1:
                            # TODO: Fix cheesy way of checking for the BaFin-ID
                            bafin_id = re.search(r'\b\d{8}\b', row_data[0])
                            if row_data[0] != '' and bafin_id:
                                self.add_attributes({"BaFin-ID": bafin_id.group()})

                            # Use the first few characters of the cell text as the key
                            elif row_data[0] != '':
                                #self.add_attributes({row_data[0][:8]: row_data[0]})
                                self.add_attributes({row_data[0]: row_data[0]})
                        else:
                            log.warning(f"Row data is not in the expected format: {row_data}")

            # TODO: Integrate the new functionality into the existing code
            #for key, value in self.get_attributes().items():
            #    print(f"\nKey: {key} \n Value: {value}")

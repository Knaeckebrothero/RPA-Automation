"""
This module holds the document class.
"""
import os
import cv2
import numpy as np
import logging
import re
from easyocr import Reader

# Custom imports
import process.detect as dct
from process.ocr import ocr_cell
from process.files import get_images_from_pdf
from cls.database import Database


# Set up logging
log  = logging.getLogger(__name__)

class Document:
    """
    The Document class represents a basic document.
    It provides core functionality for storing and managing document content and attributes.
    """
    # TODO: Add a method to store and retrieve the document in the database
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

    def save_to_file(self, file_path: str):
        """
        Save the document's content to a file at the specified path.

        :param file_path: The path where the file should be saved.
        """
        if not os.path.exists(file_path):
            os.makedirs(file_path)

        try:
            with open(file_path, 'wb') as file:
                file.write(self._content)
            log.info(f"Document saved to: {file_path}")
        except IOError as e:
            log.error(f"Error saving document: {e}")

    @classmethod
    def to_pdf(cls, document):
        """
        Convert a Document instance to a PDF instance if it's a PDF document.

        :param document: The Document instance to convert.
        :return: A PDF instance if the document is a PDF, otherwise the original Document.
        """
        if not isinstance(document, Document):
            log.error("Cannot convert non-Document instance to PDF")
            return document

        # Check if the document is a PDF based on its content_type attribute
        content_type = document.get_attributes('content_type')
        if content_type and content_type.lower() == 'application/pdf':
            log.debug("Converting Document instance to PDF instance")
            return PDF(document.get_content(), document.get_attributes())

        # If it's not a PDF, return the original document
        log.debug(f"Document is not a PDF (content_type: {content_type}), not converting")
        return document

class PDF(Document):
    """
    The PDF class represents a PDF document.
    It extends the Document class with PDF-specific functionality like OCR and table extraction.
    """
    # TODO: Add attributes such as client_id, email_id, etc. to the PDF class
    def __init__(self, content: bytes, attributes: dict = None):
        """
        The constructor for the PDF class.

        :param content: The raw content of the PDF document.
        :param attributes: A set of attributes for the document.
        """
        super().__init__(content, attributes)
        log.debug("PDF document created")

    def extract_table_data(self):
        """
        Extract the text from the document.
        """
        if self._content:
            ocr_reader = Reader(['de'])

            # Convert the PDF document into a list of images (one image per page)
            # images = convert_from_bytes(self._content)
            images = get_images_from_pdf(self._content)
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
                            cell_text = ocr_cell(cell_image, ocr_reader)
                            row_data.append(cell_text)

                        # Log and add the extracted row data to the attributes
                        log.info(f"Row {k + 1} Data: {row_data}")

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

    def initialize_audit_case(self):
        """
        Function to initialize an audit case for a document.

        :param document: The document to initialize the audit case for.
        """
        db = Database().get_instance()

        log.debug(f'Initializing audit case for document: {self.get_attributes("email_id")}')
        client_id = db.query(
            f"""
            SELECT id
            FROM client
            WHERE bafin_id ={int(self.get_attributes('BaFin-ID'))} 
            """)

        # Insert the audit case into the database if a matching client is found
        if client_id[0][0] != 0:
            db.insert(
                f"""
                    INSERT INTO audit_case (client_id, email_id, status)
                    VALUES ({client_id[0][0]}, {self.get_attributes('email_id')}, 1)
                    """)
            log.info(f"Company with BaFin ID {self.get_attributes('BaFin-ID')} has been initialized successfully")
        else:
            log.warning(f"Couldn't detect BaFin-ID for document with mail id: {self.get_attributes('email_id')}")

    # TODO: Implement a proper way to compare the values
    def compare_values(self) -> bool:
        """
        Function to compare the values of a document with the values of a client in the database.

        :param document: The document to compare the values with.
        """
        db = Database().get_instance()
        bafin_id = self.get_attributes("BaFin-ID")

        if bafin_id:
            client_data = db.query(f"""
            SELECT 
                id,
                p033, p034, p035, p036,
                ab2s1n01, ab2s1n02, ab2s1n03, ab2s1n04, 
                ab2s1n05, ab2s1n06, ab2s1n07, ab2s1n08, 
                ab2s1n09, ab2s1n10, ab2s1n11
            FROM client 
            WHERE bafin_id = {bafin_id}
            """)

            # Check if the client is in the database
            if len(client_data) > 0:
                log.debug(f"Company with BaFin ID {bafin_id} found in database")
                document_attributes = self.get_attributes()

                # Iterate over the document attributes
                for key in document_attributes.keys():
                    try:
                        value = int(document_attributes[key].replace(".", ""))
                    except ValueError:
                        continue

                    # Compare the values of the document with the values of the client in the database
                    if "033" in key:
                        if client_data[0][1] != value:
                            log.warning(f"db: {type(client_data[0][1])} vs doc: {type(value)}")
                            log.warning(f"Value mismatch for key {key}: {client_data[0][1]} (database) vs {value} (document)")
                            return False
                    elif "034" in key:
                        if client_data[0][2] != value:
                            log.warning(f"Value mismatch for key {key}: {client_data[0][2]} (database) vs {value} (document)")
                            return False
                    elif "035" in key:
                        if client_data[0][3] != value:
                            log.warning(f"Value mismatch for key {key}: {client_data[0][3]} (database) vs {value} (document)")
                            return False
                    elif "036" in key:
                        if client_data[0][4] != value:
                            log.warning(f"Value mismatch for key {key}: {client_data[0][4]} (database) vs {value} (document)")
                            return False
                    elif "Nr. 1 " in key:
                        if client_data[0][5] != value:
                            log.warning(f"Value mismatch for key {key}: {client_data[0][5]} (database) vs {value} (document)")
                            return False
                    elif "Nr. 2 " in key:
                        if client_data[0][6] != value:
                            log.warning(f"Value mismatch for key {key}: {client_data[0][6]} (database) vs {value} (document)")
                            return False
                    elif "Nr. 3 " in key:
                        if client_data[0][7] != value:
                            log.warning(f"Value mismatch for key {key}: {client_data[0][7]} (database) vs {value} (document)")
                            return False
                    elif "Nr. 4 " in key:
                        if client_data[0][8] != value:
                            log.warning(f"Value mismatch for key {key}: {client_data[0][8]} (database) vs {value} (document)")
                            return False
                    elif "Nr. 5 " in key:
                        if client_data[0][9] != value:
                            log.warning(f"Value mismatch for key {key}: {client_data[0][9]} (database) vs {value} (document)")
                            return False
                    elif "Nr. 6 " in key:
                        if client_data[0][10] != value:
                            log.warning(f"Value mismatch for key {key}: {client_data[0][10]} (database) vs {value} (document)")
                            return False
                    elif "Nr. 7 " in key:
                        if client_data[0][11] != value:
                            log.warning(f"Value mismatch for key {key}: {client_data[0][11]} (database) vs {value} (document)")
                            return False
                    elif "Nr. 8 " in key:
                        if client_data[0][12] != value:
                            log.warning(f"Value mismatch for key {key}: {client_data[0][12]} (database) vs {value} (document)")
                            return False
                    elif "Nr. 9 " in key:
                        if client_data[0][13] != value:
                            log.warning(f"Value mismatch for key {key}: {client_data[0][13]} (database) vs {value} (document)")
                            return False
                    elif "Nr. 10 " in key:
                        if client_data[0][14] != value:
                            log.warning(f"Value mismatch for key {key}: {client_data[0][14]} (database) vs {value} (document)")
                            return False
                    #elif "Nr. 11 " in key:
                    #    if client_data[0][15] != float(value.replace(".", "").replace(",", ".")):
                    #        log.debug(f"Value mismatch for key {key}: {client_data[0][15]} (database) vs {value} (
                    #        document)")
                    #        return False
                    # TODO: Fix this and add it back to the checked points

                    # Return True if all conditions are met and no mismatches are found
                    log.info(f"Values for client with BaFin ID {bafin_id} match the database.")
                    return True
            else:
                log.warning(f"Client with BaFin ID {bafin_id} not found in database")
                return False
        else:
            log.warning("No BaFin ID found for document")
            return False

    def verify_bafin_id(self) -> int | None:
        """
        Method to verify the bafin id against the database.

        :return: The client id if the bafin id is found in the database or None if no client is found.
        """
        db = Database().get_instance()
        bafin_id = self.get_attributes("BaFin-ID")

        if bafin_id:
            client_id = db.query(f'SELECT id FROM client WHERE bafin_id ={int(bafin_id)}')
            if client_id[0][0] != 0:
                self.add_attributes({'client_id': client_id})
                return client_id[0][0]
            else:
                return None
        else:
            return None

    def get_audit_status(self) -> int | None:
        """
        This method returns the status of the audit case if it exists.

        :return: The status of the audit case if it exists, otherwise None.
        """
        if not 'client_id' in self._attributes:
            client_id = self.verify_bafin_id()
        else:
            client_id = self.get_attributes('client_id')

        # Check if the client id is not None
        if client_id:
            db = Database().get_instance()
            status = db.query(f"""
            SELECT status
            FROM audit_case
            WHERE client_id = {client_id}
            """)
            if status:
                return status[0][0]
            else:
                return None
        else:
            return None

"""
This module holds the document class.
"""
import cv2
import numpy as np
import logging
from easyocr import Reader

# Custom imports
import process.detect as dtc
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
        return f"""
        Document: of size {len(self._content)} bytes, with: {len(self._attributes.keys())} number of attributes.
        Attributes: {self._attributes}
        """

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
    def __init__(self, content: bytes, email_id: int = None, client_id: int = None, bafin_id: int = None,
                 attributes: dict = None):
        """
        The constructor for the PDF class.

        :param content: The raw content of the PDF document.
        :param attributes: A set of attributes for the document.
        """
        super().__init__(content, attributes)
        self.email_id = email_id
        self.client_id = client_id
        self.bafin_id = bafin_id
        log.debug("PDF document created")

    def extract_table_data(self, ocr_reader: Reader = None):
        """
        Extract the text from the document.
        """
        if self._content:
            if not ocr_reader:
                ocr_reader = Reader(['de'])

            # Convert the PDF document into a list of images (one image per page)
            images = get_images_from_pdf(self._content)

            # Process each image in the PDF document
            for i, image in enumerate(images):
                log.debug(f"Processing image: {i + 1}/{len(images)}")

                # Convert the image to a NumPy array (shape is height times width times RGB channels)
                np_image_array = np.array(image)

                # Convert to BGR format since it is required for OpenCV (BGR is basically RGB but in reverse)
                bgr_image_array = cv2.cvtColor(np_image_array, cv2.COLOR_RGB2BGR)

                # Detect tables
                table_contours = dtc.tables(bgr_image_array)
                log.debug(f"Number of pages in the document: {len(images)}")

                # Process each detected table
                for j, contour in enumerate(table_contours):
                    log.debug(f"Processing table: {j + 1}/{len(table_contours)}")

                    # Crop the table from the image
                    x, y, w, h = cv2.boundingRect(contour)
                    table_roi = bgr_image_array[y:y + h, x:x + w]

                    # Detect rows in the table
                    rows = dtc.rows(table_roi)

                    # Process each detected row
                    for k, (y1, y2) in enumerate(rows):
                        log.debug(f"Processing row: {k + 1}/{len(rows)}")
                        row_data = []

                        # Crop the row from the table
                        row_image = table_roi[y1:y2, :]

                        # Detect cells in the row
                        cells = dtc.cells(row_image)

                        # Process each detected cell
                        for m, (x1, x2) in enumerate(cells):
                            log.debug(f"Processing cell: {m + 1}/{len(cells)}")
                            cell_image = row_image[:, x1:x2]

                            # Perform OCR on the cell image and append the extracted text to the row data
                            cell_text = ocr_cell(cell_image, ocr_reader)
                            row_data.append(cell_text)
                            log.debug(f"Row {k + 1} Data: {row_data}")

                        # Add the row data to the attributes
                        self._process_row_data(row_data)
                        log.debug(f"Document Attributes: {self._attributes}")

    def _process_row_data(self, row_data):
        """
        Process a row of table data and add it to attributes.

        :param row_data: A list of strings, each representing content from a table cell
        """
        # Filter out empty strings
        row_data = [cell.strip() for cell in row_data if cell.strip()]

        # Handle rows with multiple cells
        if len(row_data) > 1:
            # Use all but the last element as key components
            key_parts = row_data[:-1]
            value = row_data[-1]

            # Join all key parts with a separator (or just use the main key)
            key = key_parts[-1] if len(key_parts) == 1 else " ".join(key_parts)
            self.add_attributes({key: value})

        # Handle rows with single cell
        elif len(row_data) == 1:
            cell_content = row_data[0]
            content_length = len(cell_content) if cell_content else 0

            # Skip rows with more than 300 characters
            if content_length > 100:
                log.warning(f"Skipping long row ({content_length} chars) for document: {self.email_id}")
            else:
                # Look for a BaFin ID if the attribute is not already set
                if not self.bafin_id:
                    # Check the cell for a BaFin ID
                    bafin_id = dtc.bafin_id(row_data[0])
                    if bafin_id:
                        # Add the BaFin ID if it could be extracted
                        self.bafin_id = bafin_id
                        # TODO: Perhaps there should be some checks if the extracted BaFin ID is valid or if there is
                        #  already a BaFin ID attached to the document (since multiple ids in a doc could be an issue).

                # Proceed with the usual key-value split
                cell_content = row_data[0]
                if ':' in cell_content:
                    # Split only at first occurrence of ":"
                    parts = cell_content.split(':', 1)

                    # Add the first part as key and the second part as value
                    key = parts[0].strip()
                    value = parts[1].strip()
                    self.add_attributes({key: value})
                else:
                    # Ignore single cells without ":"
                    log.warning(f"Could not split cell for document: {self.email_id}")

    def initialize_audit_case(self, stage: int = 1):
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
                INSERT INTO audit_case (client_id, email_id, stage)
                VALUES ({client_id[0][0]}, {self.email_id}, {stage})
                """)
            log.info(f"Company with BaFin ID {self.get_attributes('BaFin-ID')} has been initialized successfully")
        else:
            log.warning(f"Couldn't detect BaFin-ID for document with mail id: {self.email_id}")

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
            # Use parameters to avoid SQL injection and ensure proper type handling
            result = db.query("SELECT id FROM client WHERE bafin_id = ?", (int(bafin_id),))

            if result:
                client_id = result[0][0]
                self.add_attributes({'client_id': client_id})
                return client_id
            else:
                return None
        else:
            return None

    def get_audit_stage(self) -> int | None:
        """
        This method returns the stage of the audit case if it exists.

        :return: The stage of the audit case if it exists, otherwise None.
        """
        if not 'client_id' in self._attributes:
            client_id = self.verify_bafin_id()
        else:
            client_id = self.get_attributes('client_id')

        # Check if the client id is not None
        if client_id:
            db = Database().get_instance()
            stage = db.query(f"""
            SELECT stage
            FROM audit_case
            WHERE client_id = {client_id}
            """)
            if stage:
                return stage[0][0]
            else:
                return None
        else:
            return None

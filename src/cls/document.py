"""
This module holds the document class.
"""
import os
import json
import cv2
import numpy as np
import re
import logging
import hashlib
import pandas as pd

# Custom imports
import processing.detect as dtct
from processing.ocr import ocr_cell, create_ocr_reader
from processing.files import get_images_from_pdf
from cls.database import Database


# Set up logging
log  = logging.getLogger(__name__)


class Document:
    """
    The Document class represents a basic document.
    It provides core functionality for storing and managing document content and attributes.
    """
    _db = Database.get_instance()

    def __init__(self, content: bytes, attributes: dict = None, content_path: str = None, document_hash: str = None):
        """
        The constructor for the Document class.

        :param content: The raw content of the document.
        :param attributes: A set of attributes for the document.
        :param content_path: The path to the content file.
        :param document_hash: The hash of the document content.
        """
        self._content: bytes = content
        self._attributes: dict = attributes if attributes else {}
        self._content_path: str = content_path  # TODO: Check if this is still needed!
        self.document_hash: str = document_hash if document_hash else self._generate_document_hash()
        log.debug(f"Document created: {len(self._content) if self._content else 0}, {len(self._attributes.keys())}")

    def __str__(self):
        return f"""
        ----------------- 
        Document: of size {len(self._content)} bytes, with: {len(self._attributes.keys())} number of attributes. 
        Attributes: {self._attributes}
        -----------------
        Content path: {self._content_path}
        Document Hash: {self.document_hash}
        """

    # TODO: Perhaps we should move to using getters and setters for all attributes (e.g. be consistent with the attributes)
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

    def save_to_file(self, file_path: str, save_as_json: bool = False):
        """
        Save the document to files:
        - Content is saved to the specified file path
        - If save_as_json is True, document metadata is saved to a JSON file with the same base name

        :param file_path: The path where the content file should be saved
        :param save_as_json: Whether to also save document metadata as JSON (default: False)
        :return: Path to the JSON file if save_as_json is True, otherwise path to the content file
        """
        try:
            # Ensure the directory exists
            os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)

            # Save the content to the specified file
            with open(file_path, 'wb') as file:
                file.write(self._content)
            log.info(f"Document content saved to: {file_path}")

            # Store the content path
            self._content_path = file_path

            # If JSON serialization is requested, save metadata to a JSON file
            if save_as_json:
                json_path = f"{os.path.splitext(file_path)[0]}.json"
                self.save_to_json(json_path)
                return json_path

            return file_path

        except IOError as e:
            log.error(f"Error saving document: {e}")
            return None

    def save_to_json(self, json_path: str = None):
        """
        Save the document metadata to a JSON file.

        :param json_path: Path to save the JSON file. If None, uses the content_path with .json extension.
        :return: Path to the JSON file
        """
        if not json_path and not self._content_path:
            log.error("No JSON path provided and no content path set")
            return None

        if not json_path:
            json_path = f"{os.path.splitext(self._content_path)[0]}.json"

        try:
            # Create a serializable representation of the document
            serialized = self._get_serializable_data()

            # Save to JSON file
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(serialized, f, ensure_ascii=False, indent=2)

            log.info(f"Document metadata saved to: {json_path}")
            return json_path

        except (IOError, TypeError) as e:
            log.error(f"Error saving document metadata to JSON: {e}")
            return None

    def _get_serializable_data(self):
        """
        Get a serializable representation of the document.
        This method should be overridden by subclasses to include their specific attributes.

        :return: Dictionary with serializable document data
        """
        return {
            "document_type": self.__class__.__name__,
            "attributes": self._attributes,
            "content_path": self._content_path
        }

    def _generate_document_hash(self, add_document_hash: bool = True) -> str | None:
        """
        Generate an MD5 hash of the document content to uniquely identify it.
        
        :return: The document hash as a string, or None if content is empty.
        """
        if not self._content:
            log.warning("No content available to generate hash")
            return None

        # Generate MD5 hash of the content            
        md5_hash = hashlib.md5(self._content).hexdigest()
        log.debug(f"Document hash generated: {md5_hash}")

        # Add the hash to the attributes if requested
        if add_document_hash:
            self.document_hash = md5_hash
            self._attributes["document_hash"] = md5_hash
            log.debug(f"Document hash added to attributes: {md5_hash}")

        return md5_hash

    @classmethod
    def from_json(cls, json_path: str, load_content: bool = True):
        """
        Create a Document instance from a JSON file.

        :param json_path: Path to the JSON file
        :param load_content: Whether to load the content file into memory (default: True)
        :return: A Document instance or an instance of an appropriate subclass
        """
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Determine what type of document to create
            document_type = data.get('document_type', 'Document')

            # Create the appropriate document type
            if document_type == 'Document':
                return cls._create_from_json_data(data, load_content)
            elif document_type == 'PDF':
                # Import locally to avoid circular imports
                return PDF._create_from_json_data(data, load_content)
            else:
                log.warning(f"Unknown document type: {document_type}, creating base Document")
                return cls._create_from_json_data(data, load_content)

        except (IOError, json.JSONDecodeError) as e:
            log.error(f"Error loading document from JSON: {e}")
            return None

    @classmethod
    def _create_from_json_data(cls, data, load_content):
        """
        Create a Document instance from parsed JSON data.
        This method should be overridden by subclasses to handle their specific attributes.

        :param data: Dictionary with document data
        :param load_content: Whether to load the content file
        :return: A Document instance
        """
        # Get the content path from the JSON
        content_path = data.get('content_path')
        attributes = data.get('attributes', {})

        # Load content if requested and the content file exists
        content = None
        if load_content and content_path and os.path.exists(content_path):
            with open(content_path, 'rb') as file:
                content = file.read()
            log.debug(f"Content loaded from file: {content_path}")

        # Create the document
        document = cls(content=content, attributes=attributes)
        document._content_path = content_path

        log.info(f"Document loaded from JSON data, type: {cls.__name__}")
        return document

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
    def __init__(
            self, content: bytes, email_id: int = None, client_id: int = None, bafin_id: int = None,
            attributes: dict = None, content_path: str = None, audit_case_id: int = None,
            document_hash: str = None, audit_values: dict = None):
        """
        The constructor for the PDF class.

        :param content: The raw content of the PDF document.
        :param attributes: A set of attributes for the document.
        :param email_id: The email ID associated with the document.
        :param client_id: The client ID associated with the document.
        :param bafin_id: The BaFin ID associated with the document.
        :param content_path: The path to the content file.
        :param audit_case_id: The audit case ID associated with the document.
        :param document_hash: The hash of the document content.
        """
        super().__init__(content, attributes, content_path, document_hash)
        self.email_id = email_id
        self.client_id = client_id
        self.bafin_id = bafin_id
        self.audit_case_id = audit_case_id
        self._audit_values = audit_values
        log.debug("PDF document created")

    def __str__(self):
        base_str = super().__str__()
        return f"""
        {base_str.rstrip()} 
        Email ID: {self.email_id}
        Client ID: {self.client_id}
        BaFin ID: {self.bafin_id}
        Audit Case ID: {self.audit_case_id}
        -----------------  
        Audit Values: {self._audit_values}
        ----------------- 
        """

    def _get_serializable_data(self):
        """
        Get a serializable representation of the document.
        This method should be overridden by subclasses to include their specific attributes.

        :return: Dictionary with serializable document data
        """
        data = {
            "document_type": self.__class__.__name__,
            "attributes": self._attributes,
            "content_path": self._content_path
        }

        # Include audit_values if they exist
        if hasattr(self, '_audit_values') and self._audit_values:
            data['_audit_values'] = self._audit_values

        return data

    def extract_table_data(self, ocr_reader = None):
        """
        Extract the text from the document.

        :param ocr_reader: The OCR reader to use for text extraction. If None, a default reader is created.
        """
        if self._content:
            if not ocr_reader:
                ocr_reader = create_ocr_reader(language='de')

            # Convert the PDF document into a list of images (one image per page)
            images = get_images_from_pdf(self._content)

            # Process each image in the PDF document
            for i, image in enumerate(images):
                log.debug(f"Processing image: {i + 1}/{len(images)}")

                # Convert the image to a NumPy array (shape is height times width times RGB channels)
                np_image_array = np.array(image)

                # Convert to BGR format since it is required for OpenCV (BGR is basically RGB but in reverse)
                bgr_image_array = cv2.cvtColor(np_image_array, cv2.COLOR_RGB2BGR)

                # Normalize the image resolution
                bgr_image_array = dtct.normalize_image_resolution(bgr_image_array)
                # TODO: Check if this works as expected!

                # Detect tables
                table_contours = dtct.tables(bgr_image_array)
                log.debug(f"Number of pages in the document: {len(images)}")

                # Process each detected table
                for j, contour in enumerate(table_contours):
                    log.debug(f"Processing table: {j + 1}/{len(table_contours)}")

                    # Crop the table from the image
                    x, y, w, h = cv2.boundingRect(contour)
                    table_roi = bgr_image_array[y:y + h, x:x + w]

                    # Detect rows in the table
                    rows = dtct.rows(table_roi)

                    # Process each detected row
                    for k, (y1, y2) in enumerate(rows):
                        log.debug(f"Processing row: {k + 1}/{len(rows)}")
                        row_data = []

                        # Crop the row from the table
                        row_image = table_roi[y1:y2, :]

                        # Detect cells in the row
                        cells = dtct.cells(row_image)

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

            log.debug(self.__str__())

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
                return

            # Look for a BaFin ID if the attribute is not already set
            if not self.bafin_id:
                log.debug("Document does not have a BaFin ID yet, proceeding to check the cell for one.")

                # Check the cell for a BaFin ID
                bafin_id = dtct.bafin_id(row_data[0])

                if bafin_id:
                    # TODO: Check if this part works as expected!
                    if not self.client_id:
                        # Verify the BaFin ID against the database and add the client id to the document
                        self.verify_bafin_id(bafin_id)
                    elif self.client_id == self.verify_bafin_id(bafin_id, add_client_to_doc=False):
                        # Add the BaFin ID if it matches the client id
                        self.bafin_id = bafin_id
                        self.add_attributes({"BaFin-ID": bafin_id})
                        log.info(f"BaFin ID extracted: {bafin_id} for document: {self.email_id}")
                        # TODO: Perhaps there should be some checks if the extracted BaFin ID is valid or if there is
                        #  already a BaFin ID attached to the document (since multiple ids in a doc could be an issue).
                    else:
                        log.warning(
                            f"Extracted BaFin id: {bafin_id} does not match existing client id"
                            f": {self.client_id} on document: {self.email_id}")
                else:
                    log.warning(f"No BaFin ID found in cell for document: {self.email_id}")

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

    def initialize_audit_case(self, stage: int = 1) -> int | None:
        """
        Function to initialize an audit case for a document.

        :param stage: The stage to initialize the audit case with.
        :return: The audit case id if the initialization was successful, otherwise None.
        """

        log.debug(f'Initializing audit case for document: {self.email_id}')
        client_id = self._db.query("SELECT id FROM client WHERE bafin_id = ? ", (self.bafin_id,))

        # Insert the audit case into the database if a matching client is found
        if client_id:
            inserted_id = self._db.insert(
                f"""
                INSERT INTO audit_case (client_id, email_id, stage)
                VALUES (?, ?, ?)
                """, (client_id[0][0], self.email_id, stage))
            log.info(f"Company with BaFin ID {self.bafin_id} has been initialized successfully audit case id: {inserted_id}")
            return inserted_id
        else:
            log.warning(f"Couldn't detect BaFin-ID for document with mail id: {self.email_id}")
            return None

    def compare_values(self) -> bool:
        """
        Compare extracted values from document with the values stored in the database.
        Returns True if all required values match, False otherwise.

        This function first calls extract_audit_values() to prepare the comparison data,
        then retrieves corresponding values from the database and performs the comparison.

        :return: True if all required values match, False if any discrepancy is found
        """
        if not self.bafin_id:
            log.warning("No BaFin ID found for document, cannot compare values")
            return False

        # Extract audit values from document attributes
        self.extract_audit_values()
        log.debug(f"Starting value comparison for document with BaFin ID: {self.bafin_id}")

        # Fetch client data from database
        client_data = self._db.query(f"""
        SELECT 
            id,
            p033, p034, p035, p036,
            ab2s1n01, ab2s1n02, ab2s1n03, ab2s1n04, 
            ab2s1n05, ab2s1n06, ab2s1n07, ab2s1n08, 
            ab2s1n09, ab2s1n10, ab2s1n11
        FROM client 
        WHERE bafin_id = ?
        """, (self.bafin_id,))

        # Check if client exists in database
        if client_data:
            client_data = client_data[0]
            log.debug(f"Retrieved client data: {client_data}")
        else:
            log.warning(f"Client with BaFin ID {self.bafin_id} not found in database")
            return False

        # Define field codes and their corresponding positions in client_data
        field_codes = {
            "p033": 1, "p034": 2, "p035": 3, "p036": 4,
            "ab2s1n01": 5, "ab2s1n02": 6, "ab2s1n03": 7, "ab2s1n04": 8,
            "ab2s1n05": 9, "ab2s1n06": 10, "ab2s1n07": 11, "ab2s1n08": 12,
            "ab2s1n09": 13, "ab2s1n10": 14, "ab2s1n11": 15
        }

        # Define required fields that must match for verification to pass
        required_fields = [
            "p033", "p034", "p035", "p036",
            "ab2s1n01", "ab2s1n02", "ab2s1n03", "ab2s1n04",
            "ab2s1n05", "ab2s1n06", "ab2s1n07", "ab2s1n08",
            "ab2s1n09", "ab2s1n10", "ab2s1n11"]
        # TODO: Remove this hardcoded list since using only the summed up values is not a good idea (make the
        #  function compare all attributes returned by the db query)

        # Track matches and mismatches
        matches = {}
        mismatches = {}

        # Compare values for each field
        for field_code, db_index in field_codes.items():
            db_value = client_data[db_index]

            # Check if this field was extracted from the document
            if field_code in self._audit_values:
                doc_value = self._audit_values[field_code]
                raw_value = self._audit_values.get(f"raw_{field_code}", "N/A")

                # Compare values
                if doc_value == db_value:
                    matches[field_code] = (raw_value, db_value)
                    self._audit_values[f"match_{field_code}"] = True
                    log.debug(f"Match for {field_code}: Document value '{raw_value}' matches database value '{db_value}'")
                else:
                    mismatches[field_code] = (raw_value, doc_value, db_value)
                    self._audit_values[f"match_{field_code}"] = False
                    log.warning(f"Mismatch for {field_code}: Document value '{raw_value}' ({doc_value}) does not match database value '{db_value}'")
            else:
                # Field not found in document
                if field_code in required_fields:
                    mismatches[field_code] = ("Not found", "N/A", db_value)
                    self._audit_values[f"missing_{field_code}"] = True
                    log.warning(f"Required field {field_code} not found in document")

        # Calculate match statistics for required fields
        total_required = len(required_fields)
        matched_required = sum(1 for field in required_fields if field in matches)
        match_percentage = (matched_required / total_required) * 100 if total_required > 0 else 0

        # Store overall match information
        self._audit_values["match_percentage"] = match_percentage
        self._audit_values["total_required_fields"] = total_required
        self._audit_values["matched_required_fields"] = matched_required
        self._audit_values["missing_fields"] = sum(1 for field in required_fields if f"missing_{field}" in self._audit_values)
        self._audit_values["mismatched_fields"] = sum(1 for field in required_fields if field in mismatches and field in required_fields)

        # Log overall result
        log.info(f"Value comparison complete - {matched_required}/{total_required} required fields match ({match_percentage:.1f}%)")

        # Only check required fields for pass/fail decision
        required_mismatches = {k: v for k, v in mismatches.items() if k in required_fields}

        if required_mismatches:
            log.warning(f"Document values do not match database - found {len(required_mismatches)} mismatches in required fields")
            return False
        else:
            log.info(f"All required document values match database values")
            return True

    def verify_bafin_id(self, bafin_id: int = None, add_bafin_id: bool = True,
                        add_client_id: bool = True) -> int | None:
        """
        Method to verify the bafin id against the database.

        :param bafin_id: The bafin id to verify. If not provided, the bafin id of the document is used.
        :param add_bafin_id: Whether to add the bafin id to the document attributes if it is found.
        :param add_client_id: Whether to add the bafin id to the document attributes if it is found.
        :return: The client id if the bafin id is found in the database or None if no client is found.
        """
        # Use the bafin id from the document if none is provided
        if not bafin_id:
            log.debug(f"No bafin id provided, using bafin id from document: {self.email_id}")
            bafin_id = self.bafin_id if self.bafin_id else self.get_attributes("BaFin-ID")

        if bafin_id:
            # Check if the bafin id matches a client in the database
            result = self._db.query("SELECT id FROM client WHERE bafin_id = ?", (bafin_id,))
            if result:
                log.info(f"Client with BaFin ID {bafin_id} found in database")

                # Add the ids to the document unless specified otherwise
                if add_client_id:
                    log.debug(f"Adding client id: {result[0][0]} to document: {self.email_id}")
                    self.client_id = result[0][0]
                    self.add_attributes({"client_id": result[0][0]})
                if add_bafin_id:
                    log.debug(f"Adding BaFin ID: {bafin_id} to document: {self.email_id}")
                    self.bafin_id = bafin_id
                    self.add_attributes({"BaFin-ID": bafin_id})

                return result[0][0]
            else:
                log.warning(f"No client found with BaFin ID {bafin_id}")
                return None
        else:
            log.warning(f"No BaFin ID found in document with email id: {self.email_id}")
            return None

    def get_audit_stage(self) -> int | None:
        """
        This method returns the stage of the audit case if it exists.

        :return: The stage of the audit case if it exists, otherwise None.
        """
        if not self.client_id:
            client_id = self.verify_bafin_id()
        else:
            client_id = self.client_id

        # Check if the client id is not None
        if client_id:
            stage = self._db.query("SELECT stage FROM audit_case WHERE client_id = ?", (client_id,))
            if stage:
                return stage[0][0]
            else:
                return None
        else:
            return None

    def get_audit_case_id(self, add_audit_case_id: bool = True) -> int | None:
        """
        This method returns the audit case id if it exists.

        :return: The audit case id if it exists, otherwise None.
        """
        if not self.client_id:
            log.debug(f"No client id on document: {self.email_id}")
            self.verify_bafin_id()

        # Check if the client id is not None
        if self.client_id:
            log.debug(f"Getting audit case id for client id: {self.client_id}")
            audit_case_id = self._db.query("SELECT id FROM audit_case WHERE client_id = ?", (self.client_id,))

            if audit_case_id:
                log.debug(f"Audit case id: {audit_case_id[0][0]} found for client id: {self.client_id}")

                if add_audit_case_id:
                    log.debug(f"Adding audit case id: {audit_case_id[0][0]} to document: {self.email_id}")
                    self.audit_case_id = audit_case_id[0][0]
                    self.add_attributes({"audit_case_id": audit_case_id[0][0]})

                return audit_case_id[0][0]
            else:
                log.debug(f"No audit case found for client id: {self.client_id}")
                return None
        else:
            log.debug(f"No client id found for document: {self.email_id}")
            return None

    def store_document(self, audit_case_id: int) -> bool:
        """
        Store the document on disk and create an entry in the document table.
        This method ensures that the database entry is only created if the file
        is successfully saved to disk.
        
        :param audit_case_id: The ID of the audit case associated with the document.
        :return: True if successful, False otherwise.
        """
        try:
            if not self.document_hash:
                log.debug("Document hash not set, generating hash")
                if not self._generate_document_hash():
                    log.error("Failed to generate the document hash")
                    return False
            
            # Check if this document already exists for this audit case
            existing_doc_path = self._db.query(
                "SELECT document_path FROM document WHERE document_hash = ? AND audit_case_id = ?",
                (self.document_hash, audit_case_id)
            )
            if existing_doc_path:
                log.info(f"Document with hash {self.document_hash[:8]} already exists for audit case {audit_case_id}")
                return True
            
            # Create filename and path
            filename = self.get_attributes("filename") or f"document_{self.document_hash[:8]}.pdf"
            if self.email_id:
                filename = f"{self.email_id}_{filename}"

            # Create the path
            document_path = os.path.join(
                os.getenv('FILESYSTEM_PATH', './.filesystem'),
                "documents",
                str(audit_case_id),
                filename
            )

            # Save file to disk using the existing method
            self._content_path = document_path
            saved_path = self.save_to_file(document_path, save_as_json=True)
            
            if not saved_path:
                log.error(f"Failed to save document to {document_path}")
                self._content_path = None
                return False
            
            # If file saved successfully, create database entry
            self._db.insert(
                """
                INSERT INTO document 
                (document_hash, audit_case_id, email_id, document_filename, document_path, processed) 
                VALUES (?, ?, ?, ?, ?, ?)
                """, 
                (self.document_hash, audit_case_id, self.email_id, filename, saved_path, False)
            )
            
            log.info(f"Document with hash {self.document_hash[:8]} saved to {saved_path} and added to database")
            return True
            
        except Exception as e:
            log.error(f"Error storing document: {e}")
            return False

    def extract_audit_values(self, patterns_file_path: str = None) -> dict:
        """
        Extract audit-relevant values from document attributes and populate self._audit_values.
        This function processes document attributes to identify fields relevant for audit
        verification, applying normalization to make comparison with database values more reliable.

        :param patterns_file_path: Path to the JSON file containing regex patterns. If None, uses default path.
        :return: Dictionary containing extracted and normalized audit values
        """
        if not hasattr(self, '_audit_values') or self._audit_values is None:
            self._audit_values = {}

        # Get document attributes
        document_attributes = self.get_attributes()
        if not document_attributes:
            log.warning("No attributes found in document")
            return self._audit_values

        # Load regex patterns from file
        if not patterns_file_path:
            # Default path is in the same directory as schema.sql
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            patterns_file_path = os.path.join(base_dir, 'regex_patterns.json')

        try:
            with open(patterns_file_path, 'r', encoding='utf-8') as f:
                field_mappings = json.load(f)
            log.debug(f"Loaded regex patterns from {patterns_file_path}")
        except (FileNotFoundError, json.JSONDecodeError) as e:
            log.error(f"Error loading regex patterns file: {e}")
            return {}

        # Process document attributes to find and normalize audit values
        for key, value in document_attributes.items():
            # Skip non-value attributes
            if key in ['filename', 'content_type', 'email_id', 'sender', 'date', 'client_id', 'BaFin-ID', 'document_hash']:
                continue

            # Skip empty values or non-string values
            if not value or not isinstance(value, str):
                continue

            # Try to match the attribute key with field patterns
            for field_code, patterns in field_mappings.items():
                if any(re.search(pattern, key, re.IGNORECASE) for pattern in patterns):
                    # Store the raw extracted value and key
                    self._audit_values[f"raw_{field_code}"] = value
                    self._audit_values[f"key_{field_code}"] = key

                    # Try to convert document value to integer for comparison
                    try:
                        # Remove dots (thousand separators) and convert commas to periods for decimal values
                        processed_value = value.replace('.', '')

                        # Handle decimal values (with comma as decimal separator)
                        if ',' in processed_value:
                            # For decimal values, keep the decimal part
                            processed_value = processed_value.replace(',', '.')
                            # If it's a legitimate decimal, convert to float first
                            normalized_value = int(float(processed_value))
                        else:
                            # For integers
                            normalized_value = int(processed_value)

                        # Store the normalized numeric value
                        self._audit_values[field_code] = normalized_value

                    except (ValueError, TypeError) as e:
                        # Store error information
                        self._audit_values[f"error_{field_code}"] = str(e)

                    break  # Stop checking patterns once a match was found

        return self._audit_values

    def get_value_comparison_table(self) -> pd.DataFrame:
        """
        Generate a comparison table between document values and database values.

        :return: Pandas DataFrame with columns for key figure, database value, document value, and match status
        """
        if not hasattr(self, '_audit_values') or not self._audit_values:
            log.debug("No audit values found, extracting them now")
            self.extract_audit_values()

        # Get BaFin ID if not already set
        if not self.bafin_id and self.client_id:
            bafin_id_result = self._db.query("SELECT bafin_id FROM client WHERE id = ?", (self.client_id,))
            if bafin_id_result:
                self.bafin_id = bafin_id_result[0][0]
                log.debug(f"Retrieved BaFin ID {self.bafin_id} for client {self.client_id}")

        # Check if we have a BaFin ID to proceed
        if not self.bafin_id:
            log.warning("No BaFin ID found for document, cannot generate comparison table")
            return pd.DataFrame(columns=["Key figure", "Database value", "Document value", "Match status"])

        # Fetch client data from database
        client_data = self._db.query(f"""
        SELECT 
            id,
            p033, p034, p035, p036,
            ab2s1n01, ab2s1n02, ab2s1n03, ab2s1n04, 
            ab2s1n05, ab2s1n06, ab2s1n07, ab2s1n08, 
            ab2s1n09, ab2s1n10, ab2s1n11
        FROM client 
        WHERE bafin_id = ?
        """, (self.bafin_id,))

        # Check if client exists in database
        if not client_data:
            log.warning(f"Client with BaFin ID {self.bafin_id} not found in database")
            return pd.DataFrame(columns=["Key figure", "Database value", "Document value", "Match status"])

        client_data = client_data[0]  # Get first row of results
        log.debug(f"Retrieved client data for BaFin ID {self.bafin_id}")

        # Define field mappings and readable names
        field_mappings = {
            # Position fields
            1: {"code": "p033", "name": "Position 033 (Provisionsergebnis)"},
            2: {"code": "p034", "name": "Position 034 (Nettoergebnis Wertpapieren)"},
            3: {"code": "p035", "name": "Position 035 (Nettoergebnis Devisen)"},
            4: {"code": "p036", "name": "Position 036 (Nettoergebnis Derivaten)"},

            # Section fields (§ 16j Abs. 2 Satz 1 Nr. X FinDAG)
            5: {"code": "ab2s1n01", "name": "Nr. 1 (Zahlungsverkehr)"},
            6: {"code": "ab2s1n02", "name": "Nr. 2 (Außenhandelsgeschäft)"},
            7: {"code": "ab2s1n03", "name": "Nr. 3 (Reisezahlungsmittelgeschäft)"},
            8: {"code": "ab2s1n04", "name": "Nr. 4 (Treuhandkredite)"},
            9: {"code": "ab2s1n05", "name": "Nr. 5 (Vermittlung von Kredit)"},
            10: {"code": "ab2s1n06", "name": "Nr. 6 (Kreditbearbeitung)"},
            11: {"code": "ab2s1n07", "name": "Nr. 7 (ausländischen Tochterunternehmen)"},
            12: {"code": "ab2s1n08", "name": "Nr. 8 (Nachlassbearbeitungen)"},
            13: {"code": "ab2s1n09", "name": "Nr. 9 (Electronic Banking)"},
            14: {"code": "ab2s1n10", "name": "Nr. 10 (Gutachtertätigkeiten)"},
            15: {"code": "ab2s1n11", "name": "Nr. 11 (sonstigen Bearbeitungsentgelten)"}
        }

        # Prepare data for the DataFrame
        comparison_data = []

        for db_index, field_info in field_mappings.items():
            field_code = field_info["code"]
            key_figure = field_info["name"]
            db_value = client_data[db_index]
            doc_value = "Not found"
            matches = False

            # Check if this field was extracted from the document
            if hasattr(self, '_audit_values') and self._audit_values:
                if f"raw_{field_code}" in self._audit_values:
                    doc_value = self._audit_values[f"raw_{field_code}"]

                    # If there's a normalized value, use it for comparison
                    if field_code in self._audit_values:
                        normalized_value = self._audit_values[field_code]
                        matches = (normalized_value == db_value)
                        log.debug(f"Comparing {field_code}: Document value '{normalized_value}' vs DB value '{db_value}' - Match: {matches}")

            # Use icons for match status
            match_status = "✅" if matches else "❌"

            # Add to comparison data
            comparison_data.append({
                "Key figure": key_figure,
                "Database value": db_value,
                "Document value": doc_value,
                "Match status": match_status
            })

        # Create DataFrame
        df = pd.DataFrame(comparison_data)
        log.info(f"Generated comparison table with {len(df)} rows")
        return df

    @classmethod
    def _create_from_json_data(cls, data, load_content):
        """
        Create a PDF instance from parsed JSON data.

        :param data: Dictionary with document data
        :param load_content: Whether to load the content file
        :return: A PDF instance
        """
        content_path = data.get('content_path')
        attributes = data.get('attributes', {})

        # Get audit values directly from the JSON data
        audit_values = data.get('_audit_values')

        # Extract client-related IDs from attributes if they exist there
        email_id = attributes.get('email_id')
        client_id = attributes.get('client_id')
        bafin_id = attributes.get('BaFin-ID')  # The JSON uses BaFin-ID as the key
        audit_case_id = attributes.get('audit_case_id')

        # Load content if requested and the content file exists
        content = None
        if load_content and content_path and os.path.exists(content_path):
            with open(content_path, 'rb') as file:
                content = file.read()
            log.debug(f"Content loaded from file: {content_path}")

        # Create the PDF instance with its specific attributes
        pdf = cls(
            content=content,
            email_id=email_id,
            client_id=client_id,
            bafin_id=bafin_id,
            attributes=attributes,
            content_path=content_path,
            audit_case_id=audit_case_id,
            audit_values=audit_values
        )

        log.info(f"PDF document loaded from JSON data with {len(audit_values) if audit_values else 0} audit values")
        return pdf

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
    Represents a document, encapsulating its content, attributes, and metadata, and providing functionality
    to manage, save, and retrieve document-related data.

    The Document class is a base implementation for content management that allows associating metadata
    (attributes) with raw content. It also facilitates saving the content and its metadata to files (binary
    and JSON formats) and generating a unique hash for the document content. The class can be extended for
    more specific document types.

    :ivar _content: The raw content of the document.
    :type _content: bytes
    :ivar _attributes: A dictionary holding the metadata for the document (key-value pairs).
    :type _attributes: dict
    :ivar _content_path: The file path where the document's content is stored. This attribute is optional.
    :type _content_path: str
    :ivar document_hash: A unique hash value representing the document's content.
    :type document_hash: str
    """
    _db = Database.get_instance()

    def __init__(self, content: bytes, attributes: dict = None, content_path: str = None, document_hash: str = None):
        """
        Initializes an instance of the class used for handling document-related information,
        such as content, associated attributes, content path, and the hash of its content.
        The class provides a mechanism to create and manage documents with essential metadata
        and ensures the content hash is generated if not provided.

        :param content: The binary content of the document. This is mandatory.
        :type content: bytes
        :param attributes: A dictionary of attributes associated with the document. If not provided,
                           an empty dictionary is initialized.
        :type attributes: dict, optional
        :param content_path: The path to the document content. This is optional and may not be used.
        :type content_path: str, optional
        :param document_hash: A pre-computed hash representing the document content.
                              If not provided, it will be generated automatically.
        :type document_hash: str, optional
        """
        self._content: bytes = content
        self._attributes: dict = attributes if attributes else {}
        self._content_path: str = content_path  # TODO: Check if this is still needed!
        self.document_hash: str = document_hash if document_hash else self._generate_document_hash()
        log.debug(f"Document created: {len(self._content) if self._content else 0}, {len(self._attributes.keys())}")

    def __str__(self):
        """
        Provides a custom string representation for a document object, detailing the
        attributes, content size, and additional metadata.

        :return: A formatted string providing information about the document size, number
            of attributes, list of attributes, content path, and the document hash.
        :rtype: str
        """
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
        """
        Retrieves the content stored in the `_content` attribute.

        This method is designed to return the content in bytes format,
        as stored internally in the `_content` attribute of the class.

        :return: The content stored in the `_content` attribute.
        :rtype: bytes
        """
        return self._content

    def get_attributes(self, key_or_keys: str | list[str] = None) -> dict | str | None:
        """
        Retrieve specific attributes or all attributes from an internal attributes dictionary,
        based on the provided key or list of keys. If no key is provided, return the entire
        attributes dictionary. In case none of the specified keys exist in the dictionary
        or when the dictionary is empty, return None.

        :param key_or_keys: The key (string) or list of keys to fetch values from the attributes
            dictionary. If None, all attributes are returned.
        :type key_or_keys: str | list[str], optional
        :return: A dictionary of key-value pairs for the requested keys, a single key's value,
            or the entire attributes dictionary. If the specified key(s) do not exist, or
            the dictionary is empty, return None.
        :rtype: dict | str | None
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
        Updates the internal attributes dictionary with the provided key-value pairs.

        This method allows for adding or updating multiple attributes to the internal
        attributes dictionary in a single operation. It updates the existing dictionary
        by merging it with the entries provided in the `attributes` parameter.

        :param attributes: A dictionary containing key-value pairs that will be added
           or updated in the internal attributes dictionary.
        :type attributes: dict
        """
        self._attributes.update(attributes)

    def update_attributes(self, attributes: dict):
        """
        Updates the internal attributes dictionary with the provided key-value pairs.

        This method allows adding or updating multiple key-value pairs in the
        internal attributes dictionary in one operation. This is particularly
        useful for efficiently managing state or metadata.

        :param attributes: A dictionary of key-value pairs to merge into the
            internal attributes dictionary.
        :type attributes: dict
        """
        self._attributes.update(attributes)

    def delete_attributes(self, attributes: list[str] = None):
        """
        Deletes specified attributes from the internal attributes dictionary. If no attributes
        are specified, all attributes in the dictionary will be cleared.

        :param attributes: List of attribute names to delete from the internal attributes.
            If None, all attributes will be removed.
        :type attributes: list[str], optional
        """
        if attributes:
            for attribute in attributes:
                self._attributes.pop(attribute)
        else:
            self._attributes.clear()

    def save_to_file(self, file_path: str, save_as_json: bool = False):
        """
        Saves the current document content to a specified file path. Optionally, allows
        the content's metadata to be saved as a JSON file.

        This method ensures that the directory for the specified file path exists before
        saving the document content. If requested, a separate JSON file containing the
        metadata of the document is created alongside the main file.

        :param file_path: The file path to save the document content.
        :type file_path: str
        :param save_as_json: A flag indicating whether to save the document metadata
                             as a JSON file. Defaults to False.
        :type save_as_json: bool, optional
        :return: The file path where the document content was saved, or the path to the
                 JSON file if `save_as_json` is True. Returns None if an error occurred.
        :rtype: str or None
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
        Saves the document metadata to a JSON file. If the `json_path` argument is not provided,
        the method will attempt to use the `self._content_path` to determine the file path. If
        neither is available, it logs an error and returns None. The method transforms the document
        metadata into a serializable format before writing it to the JSON file.

        :param json_path: The file path where the document metadata should be saved. If not
            specified, a default path is generated based on `self._content_path`.
        :type json_path: str
        :return: The file path of the saved JSON file, or None if an error occurs or no path is provided.
        :rtype: str or None
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
        Generates a dictionary containing serializable data about the object. This
        includes its class name, attributes, and content path. The method is used to
        serialize the key components of the object into a structured format.

        :return: A dictionary with serializable details about the object.
        :rtype: dict
        """
        return {
            "document_type": self.__class__.__name__,
            "attributes": self._attributes,
            "content_path": self._content_path
        }

    def _generate_document_hash(self, add_document_hash: bool = True) -> str | None:
        """
        Generates a MD5 hash based on the content of the document and optionally
        registers it within the attributes. This function allows for securely identifying
        or validating the content integrity by creating a unique hash.

        :param add_document_hash: Determines whether the generated hash should also be
            registered as part of the attributes. If set to True, the hash is added
            to `self._attributes` and `self.document_hash`.
        :type add_document_hash: bool
        :return: The generated MD5 hash of the document's content, or None if there’s
            no content available to hash.
        :rtype: str | None
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
        Creates an instance of the class or a subclass based on a JSON file. The method reads
        a JSON file from the provided path, determines the type of document specified in the
        JSON data, and creates the corresponding document instance.

        The method returns an instance of the base class or its subclass (such as `PDF`). If the
        document type is unrecognized, a base class instance is created with a warning. In case
        of failures in reading or parsing the JSON file, it logs the error and returns `None`.

        :param json_path: The path to the JSON file containing the document data.
        :type json_path: str
        :param load_content: A flag indicating whether to load content into the document. Defaults to True.
        :type load_content: bool
        :return: An instance of the class or its subclass based on the document type, or None if an error occurs.
        :rtype: Optional[BaseClass]
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
        Creates an instance of the class using JSON data, optionally loading content from
        a file if specified and available. This method primarily extracts the content path
        and attributes from the given JSON data, loads content if requested, and then
        instantiates the class.

        :param data: JSON data containing 'content_path' and 'attributes' needed for
            creating the class instance.
        :type data: dict
        :param load_content: Flag indicating whether to load content from the file
            specified by 'content_path' in the JSON data. Defaults to False.
        :type load_content: bool
        :return: An instance of the class, initialized with the specified attributes
            and content (if loaded).
        :rtype: cls
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
        Converts a `Document` instance to a `PDF` instance if the document's content type
        indicates it is already a PDF. Otherwise, the original document is returned without
        any modification. Only instances of `Document` are supported for conversion.

        :param document: The `Document` instance to be converted into a `PDF` instance.
        :type document: Document
        :return: A `PDF` instance if the document's content type is `application/pdf`,
                 otherwise the original `Document` instance is returned unmodified.
        :rtype: Union[Document, PDF]
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
    Represents a PDF document with attributes and functionalities for processing
    and extracting table data.

    This class is designed to handle raw PDF data, associate it with various IDs
    (e.g., email, client, BaFin, etc.), and provide advanced functionalities for
    table detection, signature page identification, and text extraction. It extends
    the base `Document` class, incorporating additional mechanisms for auditing data
    and analyzing table structures within the document.

    :ivar email_id: The email ID associated with the document.
    :type email_id: int
    :ivar client_id: The client ID associated with the document.
    :type client_id: int
    :ivar bafin_id: The BaFin ID associated with the document.
    :type bafin_id: int
    :ivar audit_case_id: The audit case ID associated with the document.
    :type audit_case_id: int
    :ivar _audit_values: A private attribute containing audit-related values.
    :type _audit_values: dict
    :ivar _signature_page_index: A private attribute storing the index of the
        detected signature page, if applicable.
    :type _signature_page_index: int
    """
    def __init__(
            self, content: bytes, email_id: int = None, client_id: int = None, bafin_id: int = None,
            attributes: dict = None, content_path: str = None, audit_case_id: int = None,
            document_hash: str = None, audit_values: dict = None):
        """
        Initializes a new instance of the class that represents a PDF document
        with specified content and associated metadata. This class extends
        the base functionality by adding additional attributes specific to
        handling PDF documents, such as references to email, client, and
        case-specific information. This initialization sets up internal states,
        including optional metadata and debug logging on successful creation.

        :param content: Binary content of the PDF document.
        :type content: bytes
        :param email_id: Unique identifier for the associated email, if any.
        :type email_id: int, optional
        :param client_id: Unique identifier for the client associated with this document.
        :type client_id: int, optional
        :param bafin_id: Identifier referencing BaFin-related attributes, if relevant.
        :type bafin_id: int, optional
        :param attributes: Custom attributes related to the PDF document for specific processing.
        :type attributes: dict, optional
        :param content_path: Path where the PDF content is stored, if applicable.
        :type content_path: str, optional
        :param audit_case_id: Unique identifier for the audit case associated with the document.
        :type audit_case_id: int, optional
        :param document_hash: Hash of the document for integrity verification purposes.
        :type document_hash: str, optional
        :param audit_values: Metadata containing audit-related details about the document.
        :type audit_values: dict, optional
        """
        super().__init__(content, attributes, content_path, document_hash)
        self.email_id = email_id
        self.client_id = client_id
        self.bafin_id = bafin_id
        self.audit_case_id = audit_case_id
        self._audit_values = audit_values
        self._signature_page_index = None
        log.debug("PDF document created")

    def __str__(self):
        """
        Constructs a string representation of the object which includes its base string
        representation and additional identifiers for the email, client, BaFin, and audit case.
        It also includes audit values at the end of the representation.

        :return: String representation of the object with extended identifiers and audit values.
        :rtype: str
        """
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
        Constructs a dictionary that represents the serializable data for the calling object.

        The returned dictionary includes the document type, attributes, content path, and any
        audit values if they exist. This is used for serializing the calling object's data
        into a standardized format.

        :return: A dictionary containing all serializable components of the calling object.
        :rtype: dict
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
        Extracts table data from a PDF document using OCR and computer vision techniques. The method goes
        through each page of the PDF (converted to image format), detects tables, rows, and cells in the
        table, applies OCR on the detected cells, and processes the extracted text data for further use. It
        also calculates and stores structural characteristics of each page, including details about detected
        tables.

        :param ocr_reader: Optional. An OCR reader instance used to perform OCR on detected cell images. If
                           not provided, a default OCR reader with German language configuration
                           is created.
        :type ocr_reader: Optional[Any]
        :return: None. The method processes and stores extracted data internally within the object.
        :rtype: None
        """
        if self._content:
            if not ocr_reader:
                ocr_reader = create_ocr_reader(language='de')

            # Convert the PDF document into a list of images (one image per page)
            images = get_images_from_pdf(self._content)

            # Track page characteristics for signature detection
            page_data = []

            # Process each image in the PDF document
            for i, image in enumerate(images):
                log.debug(f"Processing image: {i + 1}/{len(images)}")

                # Convert the image to a NumPy array (shape is height times width times RGB channels)
                np_image_array = np.array(image)

                # Convert to BGR format since it is required for OpenCV (BGR is basically RGB but in reverse)
                bgr_image_array = cv2.cvtColor(np_image_array, cv2.COLOR_RGB2BGR)

                # Normalize the image resolution
                bgr_image_array = dtct.normalize_image_resolution(bgr_image_array)

                # Detect tables
                table_contours = dtct.tables(bgr_image_array)
                log.debug(f"Number of pages in the document: {len(images)}")

                # Calculate table metrics for this page
                if table_contours:
                    table_areas = [cv2.contourArea(contour) for contour in table_contours]
                    page_data.append({
                        'page_index': i,
                        'num_tables': len(table_contours),
                        'total_area': sum(table_areas),
                        'max_area': max(table_areas),
                        'min_area': min(table_areas) if table_areas else 0
                    })

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

                # After processing all pages, determine the signature page
                self._determine_signature_page(page_data)

            log.debug(self.__str__())

    def _determine_signature_page(self, page_data):
        """
        Analyzes the provided page data to determine the index of the optimal page
        to designate as the signature page. The function applies specific criteria
        to select a page, including the number of tables, the largest and smallest
        table sizes, and proximity to the end of the document. If no conditions
        are met, it defaults to selecting the last page with the largest table.

        :param page_data: A list of dictionaries representing page details, where each
                          dictionary includes attributes such as 'num_tables',
                          'max_area', 'min_area', and 'page_index'.
        :type page_data: list[dict]
        """
        if not page_data:
            # Default to last page if no tables found
            self._signature_page_index = -1
            return

        # Find pages with exactly two tables (criterion A)
        pages_with_two_tables = [p for p in page_data if p['num_tables'] == 2]

        if pages_with_two_tables:
            # Look for a page that has both the largest and smallest tables
            # Sort pages by maximum table area
            sorted_by_max = sorted(page_data, key=lambda p: p['max_area'], reverse=True)
            # Sort pages by minimum table area
            sorted_by_min = sorted(page_data, key=lambda p: p['min_area'])

            # If the same page has both the largest and smallest tables
            if sorted_by_max[0]['page_index'] == sorted_by_min[0]['page_index']:
                self._signature_page_index = sorted_by_max[0]['page_index']
                log.debug(f"Selected page {self._signature_page_index + 1} for signature detection (has largest and smallest tables)")
                return

            # Otherwise, use the page with two tables that's closest to the end
            self._signature_page_index = pages_with_two_tables[-1]['page_index']
            log.debug(f"Selected page {self._signature_page_index + 1} for signature detection (has two tables)")
        else:
            # Default to the page with the largest table
            largest_table_page = max(page_data, key=lambda p: p['max_area'])
            self._signature_page_index = largest_table_page['page_index']
            log.debug(f"Selected page {self._signature_page_index + 1} for signature detection (has largest table)")

    def _process_row_data(self, row_data):
        """
        Processes a row of data by filtering and interpreting the content to extract key-value
        pairs or relevant information such as a BaFin ID. Handles rows with multiple cells or
        a single cell differently. Adds extracted details as attributes to the document while
        also performing validation checks for specific fields like BaFin ID. Skips rows
        that are too long or improperly formatted. Logs appropriate warnings or details
        during the processing steps.

        :param row_data: A list of strings representing a row's content, where each element
            corresponds to the content of a cell in the row. The input is expected to be
            preprocessed for basic formatting, such as trimming whitespace around cells.
            Empty cells will automatically be ignored during processing.
        :type row_data: list[str]
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
        Initializes an audit case for a given document, using the associated BaFin ID to
        identify the client. If a matching client is found, the audit case is created
        in the database with the provided stage value. Logs relevant information about
        the creation of the audit case or warnings if no matching client is found.

        :param stage: The stage of the audit case to initialize. Defaults to 1.
        :type stage: int
        :return: The ID of the created audit case if successful, or None if no matching
            client is found.
        :rtype: int | None
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
            log.info(
                f"Company with BaFin ID {self.bafin_id} has been initialized successfully audit case id: {inserted_id}")
            return inserted_id
        else:
            log.warning(f"Couldn't detect BaFin-ID for document with mail id: {self.email_id}")
            return None

    def compare_values(self) -> bool:
        """
        Compares extracted document values with values stored in the database for a
        specific client identified by their BaFin ID. The method verifies if all
        required fields match between the document and database, calculating match
        statistics and logging detailed results.

        Matching is determined by comparing document values to their corresponding
        database entries. Matches, mismatches, and missing fields are tracked, and a
        pass/fail decision is made based on required field mismatches. Audit results
        and statistics are stored within the object's audit structure for further
        analysis.

        :param self: Instance of the class that includes the object's state, such as
            the BaFin ID and extracted document values.
        :return: Whether all required document values match the database values.
        :rtype: bool
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
        Verify and process a BaFin ID by checking its existence in the database and optionally
        updating corresponding document attributes. If no BaFin ID is provided, the function will
        attempt to utilize a BaFin ID from the document's attributes or retrieve one as necessary.
        The process includes verifying whether the ID matches a client in the database, and
        logging outcomes.

        :param bafin_id: The BaFin ID to verify and process. If None, it will attempt to fetch
                         from the document attributes.
        :type bafin_id: int, optional
        :param add_bafin_id: Indicates whether to add the verified BaFin ID to the document attributes.
        :type add_bafin_id: bool, optional
        :param add_client_id: Indicates whether to add the corresponding client ID to the document attributes.
        :type add_client_id: bool, optional
        :return: The client ID associated with the BaFin ID if found, otherwise None.
        :rtype: int | None
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
        Determines the audit stage for a client by querying the database using the client ID.
        If the client ID is not directly available, attempts to verify it using `verify_bafin_id`.
        The method returns the audit stage as an integer if found, else returns None.

        :raises ValueError: If `verify_bafin_id` fails to provide a valid `client_id`.

        :return: The audit stage associated with the client ID, or None if no stage is found.
        :rtype: int | None
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
        Retrieve the audit case ID associated with the client ID of the object. Optionally, add the
        retrieved audit case ID as an attribute to the object and update the document's attributes.

        This method queries the database for the audit case ID corresponding to the object's
        client ID. If the client ID is not present, it attempts to verify and set the client ID
        by calling the `verify_bafin_id` method. If an audit case ID is found, it can be added
        to the object's attributes based on the `add_audit_case_id` parameter.

        :param add_audit_case_id: Specifies whether the retrieved audit case ID should be added
            as an attribute to the object and the document's attributes.
        :type add_audit_case_id: bool

        :return: The audit case ID if found, or None if no matching audit case ID exists or the
            client ID is not set.
        :rtype: int | None
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
        Stores a document for a given audit case after performing various operations
        such as generating a hash, checking for existing documents, saving the file
        to the filesystem, and creating a corresponding database entry. Returns a
        boolean indicating the success or failure of the operation.

        :param audit_case_id: The unique identifier of the audit case associated with
                              the document.
        :type audit_case_id: int
        :return: True if the document was successfully stored, otherwise False.
        :rtype: bool
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
        Extracts and processes audit-related attributes from a document based on regex patterns.

        This method identifies and scores potential matches for various document attributes using
        regular expressions loaded from a file. It processes these matches to extract the key,
        raw value, and normalized numeric values, whenever applicable.

        :param patterns_file_path: Path to the JSON file containing regex patterns for field matching.
                                   If not provided, a default path relative to the current module is used.
        :type patterns_file_path: str, optional
        :return: A dictionary of extracted audit values including raw data, associated keys, and
                 normalized numeric values when applicable.
        :rtype: dict
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

        # Dictionary to store potential matches with scores
        potential_matches = {}

        # Process document attributes to find all potential matches
        for key, value in document_attributes.items():
            # Skip non-value attributes
            if key in ['filename', 'content_type', 'email_id', 'sender', 'date', 'client_id', 'BaFin-ID', 'document_hash']:
                continue

            # Skip empty values or non-string values
            if not value or not isinstance(value, str):
                continue

            # Try to match the attribute key with field patterns
            for field_code, patterns in field_mappings.items():
                for pattern_idx, pattern in enumerate(patterns):
                    match = re.search(pattern, key, re.IGNORECASE)
                    if match:
                        # Calculate match score (pattern index provides base priority)
                        score = 100 - pattern_idx * 10  # Earlier patterns get higher base scores

                        # Specific scoring rules for different field types
                        if field_code.startswith('p0'):  # Position fields
                            # Boost score for Position fields that contain both "Position" and the number
                            if re.search(r'(?i)position.*0*' + field_code[1:], key):
                                score += 50
                            # Boost for "Anlage SONO1" references
                            if "anlage" in key.lower() and "sono1" in key.lower():
                                score += 30
                            # Boost for exact position number
                            if re.search(r'(?i)(?:position|pos\.?|punkt)?\s*0*' + field_code[1:] + r'\b', key):
                                score += 40

                        elif field_code.startswith('ab2s1n'):  # FinDAG fields
                            # Extract number from field code (e.g., "01" from "ab2s1n01")
                            number = field_code[-2:]
                            # Boost score for fields with explicit "Nr. X" and "FinDAG" references
                            if re.search(r'(?i)nr\.?\s*' + number.lstrip('0') + r'\b.*findag', key):
                                score += 50
                            # Boost for paragraph references
                            if re.search(r'(?i)(?:§|para(?:graph)?)\s*16j\s*abs', key):
                                score += 40

                        # Add precision boost for longer, more specific keys
                        score += min(len(key) / 10, 20)  # Cap at 20 additional points

                        # Store this match with its score
                        if field_code not in potential_matches:
                            potential_matches[field_code] = []
                        potential_matches[field_code].append({
                            'key': key,
                            'value': value,
                            'score': score
                        })

                        log.debug(f"Potential match for {field_code}: '{key}' with score {score}")

        # Select the best match for each field code based on score
        for field_code, matches in potential_matches.items():
            if not matches:
                continue

            # Sort matches by score in descending order
            matches.sort(key=lambda x: x['score'], reverse=True)
            best_match = matches[0]

            log.info(f"Best match for {field_code}: '{best_match['key']}' (score: {best_match['score']:.1f})")

            # Store the raw extracted value and key
            self._audit_values[f"raw_{field_code}"] = best_match['value']
            self._audit_values[f"key_{field_code}"] = best_match['key']

            # Try to convert document value to integer for comparison
            try:
                # Remove dots (thousand separators) and convert commas to periods for decimal values
                processed_value = best_match['value'].replace('.', '')

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

        return self._audit_values

    def get_value_comparison_table(self) -> pd.DataFrame:
        """
        Generates a comparison table of key figures for a client, retrieved from the database,
        compared against audit values extracted from the document. The function checks the
        availability of required client information (like BaFin ID) and fetches corresponding data.
        It then maps and compares relevant fields between the database and document to generate
        a comparison DataFrame.

        If certain fields or data are not found, logs warnings, and provides an empty DataFrame
        with the appropriate structure.

        :return: A Pandas DataFrame containing the comparison of key figures with their database
                 values, document values, and match statuses.
        :rtype: pd.DataFrame
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

    def check_for_signature(self):
        """
        Analyze the content of a PDF document to determine whether it contains a signature. The function focuses
        on the last page of the document, as signatures are typically found there. Converts the PDF content into
        images, processes the last page, and applies a signature detection algorithm to identify the presence
        of a signature. The result is stored as an attribute and logged for debugging.

        :return: Boolean indicating whether the document contains a signature.
        :rtype: bool
        """
        if self._content:
            # Convert the PDF document into a list of images
            images = get_images_from_pdf(self._content)

            # Check the last page for a signature (often where signatures are found)
            if images:
                last_page = images[-1]
                np_image = np.array(last_page)  # TODO: Currently searches for a signature on the last page only.
                bgr_image = cv2.cvtColor(np_image, cv2.COLOR_RGB2BGR)

                # Use the signature detection function
                from processing.detect import signature
                has_signature = signature(bgr_image)

                # Store the result as an attribute
                self.add_attributes({"has_signature": has_signature})

                if has_signature:
                    log.debug(f"Document has a signature!")
                else:
                    log.debug(f"Document does not have a signature!")

                return has_signature

        return False

    def check_document_completeness(self):
        """
        Checks the completeness of a given PDF document by verifying the presence of a
        signature and a date. The method processes the content of the PDF, extracts the
        relevant page (defaulting to the last page if no explicit signature page is designated),
        and performs separate detections to identify if both conditions are met. Detection
        results are stored and returned.

        :raises AttributeError: If the required attributes or data are missing from the instance.
        :raises ImportError: If any imported modules or detection functions are not accessible.

        :param self: Instance of the class containing the method execution context.
        :type self: object

        :return: A dictionary indicating the detection results for the presence of a signature
                 and a date, along with whether the document is considered complete.
        :rtype: dict
        """
        completeness = {'has_signature': False, 'has_date': False, 'is_complete': False}

        if self._content:
            # Convert the PDF document into a list of images
            images = get_images_from_pdf(self._content)

            if not images:
                return completeness

            # Determine which page to check - use detected signature page or default to last page
            page_index = self._signature_page_index if self._signature_page_index is not None else -1

            # Ensure page_index is valid
            if page_index < 0:
                page_index = len(images) + page_index  # Handle negative indexing

            if page_index >= len(images):
                log.warning(f"Signature page index {page_index} out of range, defaulting to last page")
                page_index = -1

            # Check the selected page
            page_to_check = images[page_index]
            np_image = np.array(page_to_check)
            bgr_image = cv2.cvtColor(np_image, cv2.COLOR_RGB2BGR)

            # Use the detection functions
            from processing.detect import signature, date

            # Check for signature and date
            completeness['has_signature'] = signature(bgr_image)
            completeness['has_date'] = date(bgr_image)
            completeness['is_complete'] = (completeness['has_signature'] and completeness['has_date'])

            log.info(f"Document completeness check on page {page_index + 1}: " +
                     f"Signature: {completeness['has_signature']}, Date: {completeness['has_date']}")

            # Store the results as attributes
            self.add_attributes(completeness)

        return completeness

    @classmethod
    def _create_from_json_data(cls, data, load_content):
        """
        Creates an instance of the class from JSON data by extracting relevant fields
        and optionally loading content from a specified file path.

        :param data: A dictionary containing JSON data with fields such as 'content_path',
            'attributes', and optional '_audit_values'. It must include relevant metadata
            to create the instance.
        :type data: dict
        :param load_content: A flag indicating whether to load file content from
            the specified content path if it exists.
        :type load_content: bool
        :return: An instance of the class containing populated attributes,
            optionally with loaded content.
        :rtype: cls
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

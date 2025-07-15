"""
Unit tests for the Document class.

This module contains tests for the Document class functionality, including
content management, attribute handling, and file operations.
"""
import os
import json
import pytest
from unittest.mock import patch, mock_open, MagicMock

from cls.document import Document


class TestDocument:
    """Test suite for the Document class."""

    def test_document_initialization(self, sample_document_content, sample_document_attributes):
        """Test document initialization with content and attributes."""
        doc = Document(content=sample_document_content, attributes=sample_document_attributes)
        
        assert doc.get_content() == sample_document_content
        assert doc.get_attributes() == sample_document_attributes
        assert doc._document_hash is not None  # Hash should be generated

    def test_document_initialization_with_hash(self, sample_document_content, sample_document_attributes):
        """Test document initialization with a provided hash."""
        custom_hash = "custom_hash_value"
        doc = Document(
            content=sample_document_content, 
            attributes=sample_document_attributes,
            document_hash=custom_hash
        )
        
        assert doc._document_hash == custom_hash

    def test_document_str_representation(self, sample_document_content, sample_document_attributes):
        """Test the string representation of a document."""
        doc = Document(content=sample_document_content, attributes=sample_document_attributes)
        str_repr = str(doc)
        
        assert "Document" in str_repr
        assert sample_document_attributes['name'] in str_repr
        assert str(len(sample_document_content)) in str_repr

    def test_get_content(self, sample_document_content, sample_document_attributes):
        """Test retrieving document content."""
        doc = Document(content=sample_document_content, attributes=sample_document_attributes)
        content = doc.get_content()
        
        assert content == sample_document_content

    def test_get_attributes_all(self, sample_document_content, sample_document_attributes):
        """Test retrieving all document attributes."""
        doc = Document(content=sample_document_content, attributes=sample_document_attributes)
        attributes = doc.get_attributes()
        
        assert attributes == sample_document_attributes

    def test_get_attributes_single(self, sample_document_content, sample_document_attributes):
        """Test retrieving a single document attribute."""
        doc = Document(content=sample_document_content, attributes=sample_document_attributes)
        name = doc.get_attributes('name')
        
        assert name == sample_document_attributes['name']

    def test_get_attributes_multiple(self, sample_document_content, sample_document_attributes):
        """Test retrieving multiple specific document attributes."""
        doc = Document(content=sample_document_content, attributes=sample_document_attributes)
        selected = doc.get_attributes(['name', 'type'])
        
        assert selected == {
            'name': sample_document_attributes['name'],
            'type': sample_document_attributes['type']
        }

    def test_get_attributes_nonexistent(self, sample_document_content, sample_document_attributes):
        """Test retrieving a nonexistent attribute."""
        doc = Document(content=sample_document_content, attributes=sample_document_attributes)
        value = doc.get_attributes('nonexistent')
        
        assert value is None

    def test_add_attributes(self, sample_document_content, sample_document_attributes):
        """Test adding new attributes to a document."""
        doc = Document(content=sample_document_content, attributes=sample_document_attributes)
        new_attributes = {'category': 'report', 'priority': 'high'}
        
        doc.add_attributes(new_attributes)
        
        # Check that new attributes were added
        assert doc.get_attributes('category') == 'report'
        assert doc.get_attributes('priority') == 'high'
        # Check that original attributes are preserved
        assert doc.get_attributes('name') == sample_document_attributes['name']

    def test_update_attributes(self, sample_document_content, sample_document_attributes):
        """Test updating existing attributes."""
        doc = Document(content=sample_document_content, attributes=sample_document_attributes)
        updated_attributes = {'name': 'updated_name.pdf', 'size': 2048}
        
        doc.update_attributes(updated_attributes)
        
        # Check that attributes were updated
        assert doc.get_attributes('name') == 'updated_name.pdf'
        assert doc.get_attributes('size') == 2048
        # Check that other attributes are preserved
        assert doc.get_attributes('type') == sample_document_attributes['type']

    def test_delete_attributes(self, sample_document_content, sample_document_attributes):
        """Test deleting attributes from a document."""
        doc = Document(content=sample_document_content, attributes=sample_document_attributes)
        
        doc.delete_attributes(['name', 'type'])
        
        # Check that attributes were deleted
        assert doc.get_attributes('name') is None
        assert doc.get_attributes('type') is None
        # Check that other attributes are preserved
        assert doc.get_attributes('size') == sample_document_attributes['size']

    def test_delete_all_attributes(self, sample_document_content, sample_document_attributes):
        """Test deleting all attributes from a document."""
        doc = Document(content=sample_document_content, attributes=sample_document_attributes)
        
        doc.delete_attributes()
        
        # Check that all attributes were deleted
        assert doc.get_attributes() == {}

    @patch('builtins.open', new_callable=mock_open)
    def test_save_to_file(self, mock_file, sample_document_content, sample_document_attributes):
        """Test saving document content to a file."""
        doc = Document(content=sample_document_content, attributes=sample_document_attributes)
        file_path = 'test_document.bin'
        
        doc.save_to_file(file_path)
        
        # Check that file was opened in write binary mode
        mock_file.assert_called_once_with(file_path, 'wb')
        # Check that content was written to the file
        mock_file().write.assert_called_once_with(sample_document_content)

    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.dirname')
    @patch('os.makedirs')
    def test_save_to_file_create_directory(self, mock_makedirs, mock_dirname, mock_file, 
                                          sample_document_content, sample_document_attributes):
        """Test that save_to_file creates the directory if it doesn't exist."""
        doc = Document(content=sample_document_content, attributes=sample_document_attributes)
        file_path = 'nonexistent/directory/test_document.bin'
        
        # Set up the mock to return a directory path
        mock_dirname.return_value = 'nonexistent/directory'
        
        doc.save_to_file(file_path)
        
        # Check that makedirs was called to create the directory
        mock_makedirs.assert_called_once_with('nonexistent/directory', exist_ok=True)
        # Check that file was opened and content was written
        mock_file.assert_called_once_with(file_path, 'wb')
        mock_file().write.assert_called_once_with(sample_document_content)

    @patch('builtins.open', new_callable=mock_open)
    @patch('json.dump')
    def test_save_to_json(self, mock_json_dump, mock_file, 
                         sample_document_content, sample_document_attributes):
        """Test saving document to a JSON file."""
        doc = Document(content=sample_document_content, attributes=sample_document_attributes)
        json_path = 'test_document.json'
        
        doc.save_to_json(json_path)
        
        # Check that file was opened in write mode
        mock_file.assert_called_once_with(json_path, 'w')
        # Check that json.dump was called with the serializable data
        mock_json_dump.assert_called_once()
        # First argument to json.dump should be the serializable data
        serializable_data = mock_json_dump.call_args[0][0]
        assert serializable_data['attributes'] == sample_document_attributes
        assert 'content_base64' in serializable_data  # Content should be base64 encoded

    @patch('builtins.open', new_callable=mock_open)
    @patch('json.load')
    def test_from_json(self, mock_json_load, mock_file, 
                      sample_document_content, sample_document_attributes):
        """Test creating a document from a JSON file."""
        import base64
        
        # Create mock JSON data
        json_data = {
            'attributes': sample_document_attributes,
            'content_base64': base64.b64encode(sample_document_content).decode('utf-8'),
            'document_hash': 'test_hash'
        }
        mock_json_load.return_value = json_data
        
        # Call the from_json class method
        doc = Document.from_json('test_document.json')
        
        # Check that file was opened in read mode
        mock_file.assert_called_once_with('test_document.json', 'r')
        # Check that json.load was called
        mock_json_load.assert_called_once()
        # Check that the document was created with the correct data
        assert doc.get_attributes() == sample_document_attributes
        assert doc.get_content() == sample_document_content
        assert doc._document_hash == 'test_hash'

    def test_generate_document_hash(self, sample_document_content):
        """Test hash generation for a document."""
        doc = Document(content=sample_document_content)
        
        # Generate a new hash
        doc._generate_document_hash()
        
        # Check that a hash was generated
        assert doc._document_hash is not None
        assert isinstance(doc._document_hash, str)
        assert len(doc._document_hash) > 0
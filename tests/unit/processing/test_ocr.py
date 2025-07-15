"""
Unit tests for the OCR module.

This module contains tests for the OCR (Optical Character Recognition) functionality,
including text extraction from images and OCR reader creation.
"""
import os
import pytest
import numpy as np
from unittest.mock import patch, MagicMock
import sys

from processing.ocr import (
    ocr_cell,
    create_ocr_reader,
    ocr_cell_tesseract,
    _handle_empty_cell_result_easyocr
)


class TestOCR:
    """Test suite for the OCR module."""

    def test_ocr_cell_with_text(self, mock_ocr_reader):
        """Test OCR cell extraction when text is present."""
        # Create a sample cell image
        cell_image = np.zeros((100, 100, 3), dtype=np.uint8)
        
        # Call the function with our mock reader
        result = ocr_cell(cell_image, reader=mock_ocr_reader)
        
        # Verify the result
        assert result == "Sample OCR Text"
        mock_ocr_reader.readtext.assert_called_once()

    @patch('processing.ocr.create_ocr_reader')
    def test_ocr_cell_without_reader(self, mock_create_reader, mock_ocr_reader):
        """Test OCR cell extraction when no reader is provided."""
        # Set up the mock to return our mock reader
        mock_create_reader.return_value = mock_ocr_reader
        
        # Create a sample cell image
        cell_image = np.zeros((100, 100, 3), dtype=np.uint8)
        
        # Call the function without providing a reader
        result = ocr_cell(cell_image)
        
        # Verify the result
        assert result == "Sample OCR Text"
        mock_create_reader.assert_called_once()
        mock_ocr_reader.readtext.assert_called_once()

    @patch('processing.ocr._handle_empty_cell_result_easyocr')
    def test_ocr_cell_empty_result(self, mock_handle_empty, mock_ocr_reader):
        """Test OCR cell extraction when no text is detected."""
        # Set up the mock to return an empty result
        mock_ocr_reader.readtext.return_value = []
        mock_handle_empty.return_value = "0"
        
        # Create a sample cell image
        cell_image = np.zeros((100, 100, 3), dtype=np.uint8)
        
        # Call the function with our mock reader
        result = ocr_cell(cell_image, reader=mock_ocr_reader)
        
        # Verify the result
        assert result == "0"
        mock_ocr_reader.readtext.assert_called_once()
        mock_handle_empty.assert_called_once()

    @patch('os.getenv')
    @patch('processing.ocr.Reader')
    def test_create_ocr_reader_with_gpu(self, mock_reader_class, mock_getenv):
        """Test creating an OCR reader with GPU enabled."""
        # Set up the mocks
        mock_getenv.return_value = 'true'
        
        # Mock torch module
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = True
        
        # Temporarily add torch to sys.modules
        sys.modules['torch'] = mock_torch
        
        try:
            # Call the function
            reader = create_ocr_reader(language='en', use_gpu=True)
            
            # Verify the result
            mock_reader_class.assert_called_once_with(['en'], gpu=True)
        finally:
            # Clean up
            if 'torch' in sys.modules:
                del sys.modules['torch']

    @patch('os.getenv')
    @patch('processing.ocr.Reader')
    def test_create_ocr_reader_gpu_not_available(self, mock_reader_class, mock_getenv):
        """Test creating an OCR reader when GPU is requested but not available."""
        # Set up the mocks
        mock_getenv.return_value = 'true'
        
        # Mock torch module
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = False
        
        # Temporarily add torch to sys.modules
        sys.modules['torch'] = mock_torch
        
        try:
            # Call the function
            reader = create_ocr_reader(language='en', use_gpu=True)
            
            # Verify the result
            mock_reader_class.assert_called_once_with(['en'], gpu=False)
        finally:
            # Clean up
            if 'torch' in sys.modules:
                del sys.modules['torch']

    @patch('os.getenv')
    @patch('processing.ocr.Reader')
    def test_create_ocr_reader_with_cpu(self, mock_reader_class, mock_getenv):
        """Test creating an OCR reader with CPU."""
        # Set up the mock
        mock_getenv.return_value = 'false'
        
        # Call the function
        reader = create_ocr_reader(language='en', use_gpu=False)
        
        # Verify the result
        mock_reader_class.assert_called_once_with(['en'], gpu=False)

    @patch('os.getenv')
    @patch('processing.ocr.Reader')
    def test_create_ocr_reader_env_var(self, mock_reader_class, mock_getenv):
        """Test creating an OCR reader using environment variable."""
        # Set up the mock to return 'true' for OCR_USE_GPU
        mock_getenv.return_value = 'true'
        
        # Mock torch module
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = True
        
        # Temporarily add torch to sys.modules
        sys.modules['torch'] = mock_torch
        
        try:
            # Call the function without explicitly setting use_gpu
            reader = create_ocr_reader(language='en')
            
            # Verify the result
            mock_reader_class.assert_called_once_with(['en'], gpu=True)
        finally:
            # Clean up
            if 'torch' in sys.modules:
                del sys.modules['torch']

    @patch('os.getenv')
    @patch('processing.ocr.Reader')
    def test_create_ocr_reader_torch_import_error(self, mock_reader_class, mock_getenv):
        """Test creating an OCR reader when torch import fails."""
        # Set up the mock
        mock_getenv.return_value = 'true'
        
        # Make sure torch is not in sys.modules
        if 'torch' in sys.modules:
            del sys.modules['torch']
        
        # Call the function - it should handle the ImportError and use CPU
        reader = create_ocr_reader(language='en', use_gpu=True)
        
        # Verify the result
        mock_reader_class.assert_called_once_with(['en'], gpu=False)

    @patch('pytesseract.image_to_string')
    @patch('PIL.Image.fromarray')
    def test_ocr_cell_tesseract(self, mock_fromarray, mock_image_to_string):
        """Test OCR cell extraction using Tesseract."""
        # Set up the mocks
        mock_image = MagicMock()
        mock_fromarray.return_value = mock_image
        mock_image_to_string.return_value = "Sample Tesseract Text"
        
        # Create a sample cell image
        cell_image = np.zeros((100, 100, 3), dtype=np.uint8)
        
        # Call the function
        result = ocr_cell_tesseract(cell_image)
        
        # Verify the result
        assert result == "Sample Tesseract Text"
        mock_fromarray.assert_called_once()
        mock_image_to_string.assert_called_once_with(mock_image, lang='eng', config='--psm 6')

    @patch('pytesseract.image_to_string')
    @patch('PIL.Image.fromarray')
    def test_ocr_cell_tesseract_empty(self, mock_fromarray, mock_image_to_string):
        """Test OCR cell extraction using Tesseract with empty result."""
        # Set up the mocks
        mock_image = MagicMock()
        mock_fromarray.return_value = mock_image
        mock_image_to_string.return_value = ""
        
        # Create a sample cell image
        cell_image = np.zeros((100, 100, 3), dtype=np.uint8)
        
        # Call the function
        result = ocr_cell_tesseract(cell_image)
        
        # Verify the result
        assert result == ""
        mock_fromarray.assert_called_once()
        mock_image_to_string.assert_called_once_with(mock_image, lang='eng', config='--psm 6')

    def test_handle_empty_cell_result_easyocr(self):
        """Test handling empty OCR results."""
        # Test with typical empty result
        assert _handle_empty_cell_result_easyocr("") == "0"
        assert _handle_empty_cell_result_easyocr(" ") == "0"
        assert _handle_empty_cell_result_easyocr("\n") == "0"
        
        # Test with actual text
        assert _handle_empty_cell_result_easyocr("123") == "123"
        assert _handle_empty_cell_result_easyocr("text") == "text"
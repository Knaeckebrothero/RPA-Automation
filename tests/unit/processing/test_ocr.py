"""
Unit tests for the OCR module.

This module contains tests for the OCR (Optical Character Recognition) functionality,
including text extraction from images and OCR reader creation.
"""
import os
import pytest
import numpy as np
from unittest.mock import patch, MagicMock

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
    @patch('torch.cuda.is_available')
    def test_create_ocr_reader_with_gpu(self, mock_cuda_available, mock_getenv):
        """Test creating an OCR reader with GPU enabled."""
        # Set up the mocks
        mock_getenv.return_value = 'true'
        mock_cuda_available.return_value = True
        
        with patch('easyocr.Reader') as mock_reader_class:
            # Call the function
            reader = create_ocr_reader(language='en', use_gpu=True)
            
            # Verify the result
            mock_reader_class.assert_called_once_with(['en'], gpu=True)

    @patch('os.getenv')
    @patch('torch.cuda.is_available')
    def test_create_ocr_reader_gpu_not_available(self, mock_cuda_available, mock_getenv):
        """Test creating an OCR reader when GPU is requested but not available."""
        # Set up the mocks
        mock_getenv.return_value = 'true'
        mock_cuda_available.return_value = False
        
        with patch('easyocr.Reader') as mock_reader_class:
            # Call the function
            reader = create_ocr_reader(language='en', use_gpu=True)
            
            # Verify the result
            mock_reader_class.assert_called_once_with(['en'], gpu=False)

    @patch('os.getenv')
    def test_create_ocr_reader_with_cpu(self, mock_getenv):
        """Test creating an OCR reader with CPU."""
        # Set up the mock
        mock_getenv.return_value = 'false'
        
        with patch('easyocr.Reader') as mock_reader_class:
            # Call the function
            reader = create_ocr_reader(language='en', use_gpu=False)
            
            # Verify the result
            mock_reader_class.assert_called_once_with(['en'], gpu=False)

    @patch('os.getenv')
    def test_create_ocr_reader_env_var(self, mock_getenv):
        """Test creating an OCR reader using environment variable."""
        # Set up the mock to return 'true' for OCR_USE_GPU
        mock_getenv.return_value = 'true'
        
        with patch('easyocr.Reader') as mock_reader_class, \
             patch('torch.cuda.is_available', return_value=True):
            # Call the function without explicitly setting use_gpu
            reader = create_ocr_reader(language='en')
            
            # Verify the result
            mock_reader_class.assert_called_once_with(['en'], gpu=True)

    @patch('os.getenv')
    def test_create_ocr_reader_torch_import_error(self, mock_getenv):
        """Test creating an OCR reader when torch import fails."""
        # Set up the mock
        mock_getenv.return_value = 'true'
        
        with patch('easyocr.Reader') as mock_reader_class, \
             patch('processing.ocr.torch', side_effect=ImportError):
            # Call the function
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
        mock_image_to_string.assert_called_once_with(mock_image)

    @patch('cv2.cvtColor')
    @patch('cv2.threshold')
    @patch('cv2.findContours')
    @patch('cv2.boundingRect')
    def test_handle_empty_cell_result_no_contours(self, mock_boundingRect, mock_findContours, 
                                                mock_threshold, mock_cvtColor):
        """Test handling empty cell result when no contours are found."""
        # Set up the mocks
        mock_cvtColor.return_value = np.zeros((100, 100), dtype=np.uint8)
        mock_threshold.return_value = (None, np.zeros((100, 100), dtype=np.uint8))
        mock_findContours.return_value = ([], None)
        
        # Create a sample cell image and reader
        cell_image = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_reader = MagicMock()
        
        # Call the function
        result = _handle_empty_cell_result_easyocr(cell_image, mock_reader)
        
        # Verify the result
        assert result == ""
        mock_cvtColor.assert_called_once()
        mock_threshold.assert_called_once()
        mock_findContours.assert_called_once()
        mock_boundingRect.assert_not_called()

    @patch('cv2.cvtColor')
    @patch('cv2.threshold')
    @patch('cv2.findContours')
    @patch('cv2.boundingRect')
    @patch('cv2.resize')
    def test_handle_empty_cell_result_with_contours_and_text(self, mock_resize, mock_boundingRect, 
                                                          mock_findContours, mock_threshold, mock_cvtColor):
        """Test handling empty cell result when contours are found and text is detected."""
        # Set up the mocks
        mock_cvtColor.return_value = np.zeros((100, 100), dtype=np.uint8)
        mock_threshold.return_value = (None, np.zeros((100, 100), dtype=np.uint8))
        mock_contour = MagicMock()
        mock_findContours.return_value = ([mock_contour], None)
        mock_boundingRect.return_value = (0, 0, 10, 10)
        mock_resize.return_value = np.zeros((30, 30), dtype=np.uint8)
        
        # Create a sample cell image and reader
        cell_image = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_reader = MagicMock()
        mock_reader.readtext.return_value = ["5"]
        
        # Call the function
        result = _handle_empty_cell_result_easyocr(cell_image, mock_reader)
        
        # Verify the result
        assert result == "5"
        mock_cvtColor.assert_called_once()
        mock_threshold.assert_called_once()
        mock_findContours.assert_called_once()
        mock_boundingRect.assert_called_once()
        mock_resize.assert_called_once()
        mock_reader.readtext.assert_called_once()

    @patch('cv2.cvtColor')
    @patch('cv2.threshold')
    @patch('cv2.findContours')
    @patch('cv2.boundingRect')
    @patch('cv2.resize')
    @patch('cv2.contourArea')
    @patch('cv2.arcLength')
    def test_handle_empty_cell_result_with_circular_contour(self, mock_arcLength, mock_contourArea, 
                                                         mock_resize, mock_boundingRect, mock_findContours, 
                                                         mock_threshold, mock_cvtColor):
        """Test handling empty cell result when a circular contour is found (likely a '0')."""
        # Set up the mocks
        mock_cvtColor.return_value = np.zeros((100, 100), dtype=np.uint8)
        mock_threshold.return_value = (None, np.zeros((100, 100), dtype=np.uint8))
        mock_contour = MagicMock()
        mock_findContours.return_value = ([mock_contour], None)
        mock_boundingRect.return_value = (0, 0, 10, 10)
        mock_resize.return_value = np.zeros((30, 30), dtype=np.uint8)
        mock_contourArea.return_value = 50  # Area that gives a ratio of ~0.5
        mock_arcLength.return_value = 30  # Perimeter that gives high circularity
        
        # Create a sample cell image and reader
        cell_image = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_reader = MagicMock()
        mock_reader.readtext.return_value = []  # No text detected by OCR
        
        # Call the function
        result = _handle_empty_cell_result_easyocr(cell_image, mock_reader)
        
        # Verify the result
        assert result == "0"  # Should detect as '0' based on circularity
        mock_cvtColor.assert_called_once()
        mock_threshold.assert_called_once()
        mock_findContours.assert_called_once()
        mock_boundingRect.assert_called_once()
        mock_resize.assert_called_once()
        mock_reader.readtext.assert_called_once()
        mock_contourArea.assert_called_once()
        mock_arcLength.assert_called_once()

    @patch('cv2.cvtColor')
    @patch('cv2.threshold')
    @patch('cv2.findContours')
    @patch('np.count_nonzero')
    def test_handle_empty_cell_result_with_few_pixels(self, mock_count_nonzero, mock_findContours, 
                                                   mock_threshold, mock_cvtColor):
        """Test handling empty cell result when a few non-zero pixels are found."""
        # Set up the mocks
        mock_cvtColor.return_value = np.zeros((100, 100), dtype=np.uint8)
        thresh = np.zeros((100, 100), dtype=np.uint8)
        mock_threshold.return_value = (None, thresh)
        mock_findContours.return_value = ([], None)  # No significant contours
        mock_count_nonzero.return_value = 50  # A few non-zero pixels
        
        # Create a sample cell image and reader
        cell_image = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_reader = MagicMock()
        
        # Call the function
        result = _handle_empty_cell_result_easyocr(cell_image, mock_reader)
        
        # Verify the result
        assert result == "0"  # Should detect as '0' based on pixel count
        mock_cvtColor.assert_called_once()
        mock_threshold.assert_called_once()
        mock_findContours.assert_called_once()
        mock_count_nonzero.assert_called_once()
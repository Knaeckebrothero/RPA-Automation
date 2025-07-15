"""
Unit tests for the detect module.

This module contains tests for the document detection functionality, including
table detection, signature detection, date detection, and other image processing
operations.
"""
import pytest
import numpy as np
from unittest.mock import patch, MagicMock

from processing.detect import (
    normalize_image_resolution,
    estimate_dpi,
    tables,
    _is_contour_inside,
    rows,
    cells,
    bafin_id,
    _similar,
    signature,
    _detect_potential_signature_regions,
    _detect_potential_date_regions,
    date,
    detect_document_completeness
)


class TestDetect:
    """Test suite for the detect module."""

    def test_normalize_image_resolution_already_at_target(self):
        """Test normalizing an image that's already at the target resolution."""
        # Create a sample image
        image = np.zeros((400, 400), dtype=np.uint8)
        
        # Mock the estimate_dpi function to return the target DPI
        with patch('processing.detect.estimate_dpi', return_value=400):
            # Call the function
            result = normalize_image_resolution(image, target_dpi=400)
            
            # Verify the result
            assert result.shape == image.shape
            # No resizing should have occurred
            assert np.array_equal(result, image)

    def test_normalize_image_resolution_upscale(self):
        """Test normalizing an image that needs to be upscaled."""
        # Create a sample image
        image = np.zeros((200, 200), dtype=np.uint8)
        
        # Mock the estimate_dpi function to return a lower DPI
        with patch('processing.detect.estimate_dpi', return_value=200):
            # Call the function
            result = normalize_image_resolution(image, target_dpi=400)
            
            # Verify the result
            assert result.shape == (400, 400)  # Should be upscaled by 2x

    def test_normalize_image_resolution_downscale(self):
        """Test normalizing an image that needs to be downscaled."""
        # Create a sample image
        image = np.zeros((800, 800), dtype=np.uint8)
        
        # Mock the estimate_dpi function to return a higher DPI
        with patch('processing.detect.estimate_dpi', return_value=800):
            # Call the function
            result = normalize_image_resolution(image, target_dpi=400)
            
            # Verify the result
            assert result.shape == (400, 400)  # Should be downscaled by 0.5x

    def test_estimate_dpi_standard_a4(self):
        """Test estimating DPI for a standard A4 document."""
        # A4 dimensions at 300 DPI would be approximately 2480 x 3508 pixels
        height, width = 3508, 2480
        
        # Call the function
        result = estimate_dpi(height, width)
        
        # Verify the result is close to 300 DPI
        assert 290 <= result <= 310

    def test_estimate_dpi_small_image(self):
        """Test estimating DPI for a small image."""
        # Small image dimensions
        height, width = 500, 350
        
        # Call the function
        result = estimate_dpi(height, width)
        
        # Verify the result is reasonable
        assert result > 0

    def test_estimate_dpi_large_image(self):
        """Test estimating DPI for a large image."""
        # Large image dimensions
        height, width = 7000, 5000
        
        # Call the function
        result = estimate_dpi(height, width)
        
        # Verify the result is reasonable
        assert result > 0

    @patch('cv2.cvtColor')
    @patch('cv2.GaussianBlur')
    @patch('cv2.Canny')
    @patch('cv2.findContours')
    @patch('cv2.contourArea')
    @patch('cv2.approxPolyDP')
    def test_tables_with_tables(self, mock_approx, mock_area, mock_find_contours, 
                              mock_canny, mock_blur, mock_cvt_color):
        """Test table detection when tables are present."""
        # Set up the mocks
        mock_cvt_color.return_value = np.zeros((100, 100), dtype=np.uint8)
        mock_blur.return_value = np.zeros((100, 100), dtype=np.uint8)
        mock_canny.return_value = np.zeros((100, 100), dtype=np.uint8)
        
        # Create mock contours
        mock_contour1 = np.array([[[10, 10]], [[90, 10]], [[90, 90]], [[10, 90]]])
        mock_contour2 = np.array([[[20, 20]], [[80, 20]], [[80, 80]], [[20, 80]]])
        mock_find_contours.return_value = ([mock_contour1, mock_contour2], None)
        
        # Set up area and approximation mocks
        mock_area.side_effect = [8100, 3600]  # Areas for the two contours
        mock_approx.side_effect = [mock_contour1, mock_contour2]
        
        # Create a sample image
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        
        # Call the function
        result = tables(image)
        
        # Verify the result
        assert len(result) == 2
        assert np.array_equal(result[0], mock_contour1)
        assert np.array_equal(result[1], mock_contour2)

    @patch('cv2.cvtColor')
    @patch('cv2.GaussianBlur')
    @patch('cv2.Canny')
    @patch('cv2.findContours')
    def test_tables_no_tables(self, mock_find_contours, mock_canny, mock_blur, mock_cvt_color):
        """Test table detection when no tables are present."""
        # Set up the mocks
        mock_cvt_color.return_value = np.zeros((100, 100), dtype=np.uint8)
        mock_blur.return_value = np.zeros((100, 100), dtype=np.uint8)
        mock_canny.return_value = np.zeros((100, 100), dtype=np.uint8)
        mock_find_contours.return_value = ([], None)  # No contours found
        
        # Create a sample image
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        
        # Call the function
        result = tables(image)
        
        # Verify the result
        assert len(result) == 0

    def test_is_contour_inside_true(self):
        """Test checking if one contour is inside another (true case)."""
        # Create outer contour
        outer = np.array([[[0, 0]], [[100, 0]], [[100, 100]], [[0, 100]]])
        
        # Create inner contour
        inner = np.array([[[25, 25]], [[75, 25]], [[75, 75]], [[25, 75]]])
        
        # Call the function
        result = _is_contour_inside(inner, outer, (100, 100))
        
        # Verify the result
        assert result is True

    def test_is_contour_inside_false(self):
        """Test checking if one contour is inside another (false case)."""
        # Create two non-nested contours
        contour1 = np.array([[[0, 0]], [[40, 0]], [[40, 40]], [[0, 40]]])
        contour2 = np.array([[[60, 60]], [[100, 60]], [[100, 100]], [[60, 100]]])
        
        # Call the function
        result = _is_contour_inside(contour1, contour2, (100, 100))
        
        # Verify the result
        assert result is False

    @patch('cv2.cvtColor')
    @patch('cv2.GaussianBlur')
    @patch('cv2.Canny')
    @patch('cv2.HoughLinesP')
    def test_rows_with_horizontal_lines(self, mock_hough, mock_canny, mock_blur, mock_cvt_color):
        """Test row detection when horizontal lines are present."""
        # Set up the mocks
        mock_cvt_color.return_value = np.zeros((100, 100), dtype=np.uint8)
        mock_blur.return_value = np.zeros((100, 100), dtype=np.uint8)
        mock_canny.return_value = np.zeros((100, 100), dtype=np.uint8)
        
        # Create mock horizontal lines
        mock_hough.return_value = np.array([
            [0, 20, 100, 20],    # y=20
            [0, 50, 100, 50],    # y=50
            [0, 80, 100, 80],    # y=80
            [20, 0, 20, 100]     # x=20 (vertical, should be ignored)
        ])
        
        # Create a sample image
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        
        # Call the function
        result = rows(image)
        
        # Verify the result
        assert len(result) == 4  # 3 horizontal lines create 4 rows
        # Check that rows are sorted by y-coordinate
        assert result[0][0] == 0
        assert result[1][0] == 20
        assert result[2][0] == 50
        assert result[3][0] == 80

    @patch('cv2.cvtColor')
    @patch('cv2.GaussianBlur')
    @patch('cv2.Canny')
    @patch('cv2.HoughLinesP')
    def test_rows_no_horizontal_lines(self, mock_hough, mock_canny, mock_blur, mock_cvt_color):
        """Test row detection when no horizontal lines are present."""
        # Set up the mocks
        mock_cvt_color.return_value = np.zeros((100, 100), dtype=np.uint8)
        mock_blur.return_value = np.zeros((100, 100), dtype=np.uint8)
        mock_canny.return_value = np.zeros((100, 100), dtype=np.uint8)
        
        # No lines detected
        mock_hough.return_value = None
        
        # Create a sample image
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        
        # Call the function
        result = rows(image)
        
        # Verify the result
        assert len(result) == 1  # Should return a single row covering the whole image
        assert result[0][0] == 0
        assert result[0][1] == 100

    @patch('cv2.cvtColor')
    @patch('cv2.GaussianBlur')
    @patch('cv2.Canny')
    @patch('cv2.HoughLinesP')
    def test_cells_with_vertical_lines(self, mock_hough, mock_canny, mock_blur, mock_cvt_color):
        """Test cell detection when vertical lines are present."""
        # Set up the mocks
        mock_cvt_color.return_value = np.zeros((100, 100), dtype=np.uint8)
        mock_blur.return_value = np.zeros((100, 100), dtype=np.uint8)
        mock_canny.return_value = np.zeros((100, 100), dtype=np.uint8)
        
        # Create mock vertical lines
        mock_hough.return_value = np.array([
            [20, 0, 20, 100],    # x=20
            [50, 0, 50, 100],    # x=50
            [80, 0, 80, 100],    # x=80
            [0, 20, 100, 20]     # y=20 (horizontal, should be ignored)
        ])
        
        # Create a sample image
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        
        # Call the function
        result = cells(image)
        
        # Verify the result
        assert len(result) == 4  # 3 vertical lines create 4 cells
        # Check that cells are sorted by x-coordinate
        assert result[0][0] == 0
        assert result[1][0] == 20
        assert result[2][0] == 50
        assert result[3][0] == 80

    def test_bafin_id_valid(self):
        """Test extracting a valid BaFin ID."""
        # Test with various valid BaFin ID formats
        assert bafin_id("BaFin-ID: 12345") == 12345
        assert bafin_id("BaFin ID: 12345") == 12345
        assert bafin_id("BaFin-ID 12345") == 12345
        assert bafin_id("BaFin ID 12345") == 12345
        assert bafin_id("BaFin: 12345") == 12345
        assert bafin_id("ID: 12345") == 12345
        assert bafin_id("12345") == 12345

    def test_bafin_id_invalid(self):
        """Test extracting an invalid BaFin ID."""
        # Test with invalid inputs
        assert bafin_id("No ID here") is None
        assert bafin_id("BaFin-ID: ABC") is None
        assert bafin_id("") is None
        assert bafin_id(None) is None

    def test_similar_high_similarity(self):
        """Test similarity function with highly similar strings."""
        assert _similar("hello", "hallo") > 0.8
        assert _similar("BaFin ID", "BaFin-ID") > 0.8

    def test_similar_low_similarity(self):
        """Test similarity function with dissimilar strings."""
        assert _similar("hello", "goodbye") < 0.5
        assert _similar("BaFin ID", "Document Number") < 0.5

    @patch('cv2.cvtColor')
    @patch('cv2.threshold')
    @patch('cv2.findContours')
    @patch('cv2.contourArea')
    def test_signature_with_signature(self, mock_area, mock_find_contours, 
                                    mock_threshold, mock_cvt_color):
        """Test signature detection when a signature is present."""
        # Set up the mocks
        mock_cvt_color.return_value = np.zeros((100, 100), dtype=np.uint8)
        mock_threshold.return_value = (None, np.zeros((100, 100), dtype=np.uint8))
        
        # Create mock contours with significant area
        mock_contour = MagicMock()
        mock_find_contours.return_value = ([mock_contour], None)
        mock_area.return_value = 500  # Significant area
        
        # Create a sample image
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        
        # Define signature regions
        signature_regions = [(0, 0, 100, 100)]
        
        # Call the function
        result = signature(image, signature_regions)
        
        # Verify the result
        assert result is True

    @patch('cv2.cvtColor')
    @patch('cv2.threshold')
    @patch('cv2.findContours')
    @patch('cv2.contourArea')
    def test_signature_no_signature(self, mock_area, mock_find_contours, 
                                  mock_threshold, mock_cvt_color):
        """Test signature detection when no signature is present."""
        # Set up the mocks
        mock_cvt_color.return_value = np.zeros((100, 100), dtype=np.uint8)
        mock_threshold.return_value = (None, np.zeros((100, 100), dtype=np.uint8))
        
        # Create mock contours with insignificant area
        mock_contour = MagicMock()
        mock_find_contours.return_value = ([mock_contour], None)
        mock_area.return_value = 5  # Insignificant area
        
        # Create a sample image
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        
        # Define signature regions
        signature_regions = [(0, 0, 100, 100)]
        
        # Call the function
        result = signature(image, signature_regions)
        
        # Verify the result
        assert result is False

    @patch('cv2.cvtColor')
    @patch('cv2.threshold')
    @patch('cv2.findContours')
    @patch('cv2.contourArea')
    @patch('processing.detect._detect_potential_signature_regions')
    def test_signature_auto_detect_regions(self, mock_detect_regions, mock_area, 
                                         mock_find_contours, mock_threshold, mock_cvt_color):
        """Test signature detection with automatic region detection."""
        # Set up the mocks
        mock_cvt_color.return_value = np.zeros((100, 100), dtype=np.uint8)
        mock_threshold.return_value = (None, np.zeros((100, 100), dtype=np.uint8))
        
        # Mock region detection
        mock_detect_regions.return_value = [(0, 0, 100, 100)]
        
        # Create mock contours with significant area
        mock_contour = MagicMock()
        mock_find_contours.return_value = ([mock_contour], None)
        mock_area.return_value = 500  # Significant area
        
        # Create a sample image
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        
        # Call the function without providing regions
        result = signature(image)
        
        # Verify the result
        assert result is True
        mock_detect_regions.assert_called_once()

    @patch('cv2.cvtColor')
    @patch('cv2.threshold')
    @patch('cv2.findContours')
    @patch('cv2.contourArea')
    @patch('processing.detect._detect_potential_date_regions')
    def test_date_with_date(self, mock_detect_regions, mock_area, 
                          mock_find_contours, mock_threshold, mock_cvt_color):
        """Test date detection when a date is present."""
        # Set up the mocks
        mock_cvt_color.return_value = np.zeros((100, 100), dtype=np.uint8)
        mock_threshold.return_value = (None, np.zeros((100, 100), dtype=np.uint8))
        
        # Mock region detection
        mock_detect_regions.return_value = [(0, 0, 100, 100)]
        
        # Create mock contours with significant area
        mock_contour1 = MagicMock()
        mock_contour2 = MagicMock()
        mock_find_contours.return_value = ([mock_contour1, mock_contour2], None)
        mock_area.return_value = 20  # Significant area for date
        
        # Create a sample image
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        
        # Call the function
        result = date(image)
        
        # Verify the result
        assert result is True
        mock_detect_regions.assert_called_once()

    @patch('cv2.cvtColor')
    @patch('cv2.threshold')
    @patch('cv2.findContours')
    @patch('cv2.contourArea')
    def test_date_no_date(self, mock_area, mock_find_contours, 
                        mock_threshold, mock_cvt_color):
        """Test date detection when no date is present."""
        # Set up the mocks
        mock_cvt_color.return_value = np.zeros((100, 100), dtype=np.uint8)
        mock_threshold.return_value = (None, np.zeros((100, 100), dtype=np.uint8))
        
        # Create mock contours with insignificant area
        mock_contour = MagicMock()
        mock_find_contours.return_value = ([mock_contour], None)
        mock_area.return_value = 1  # Insignificant area
        
        # Create a sample image
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        
        # Define date regions
        date_regions = [(0, 0, 100, 100)]
        
        # Call the function
        result = date(image, date_regions)
        
        # Verify the result
        assert result is False

    @patch('processing.detect.signature')
    @patch('processing.detect.date')
    def test_detect_document_completeness_complete(self, mock_date, mock_signature):
        """Test document completeness detection for a complete document."""
        # Set up the mocks
        mock_signature.return_value = True
        mock_date.return_value = True
        
        # Create a sample image
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        
        # Call the function
        result = detect_document_completeness(image)
        
        # Verify the result
        assert result['has_signature'] is True
        assert result['has_date'] is True
        assert result['is_complete'] is True

    @patch('processing.detect.signature')
    @patch('processing.detect.date')
    def test_detect_document_completeness_incomplete(self, mock_date, mock_signature):
        """Test document completeness detection for an incomplete document."""
        # Set up the mocks
        mock_signature.return_value = True
        mock_date.return_value = False
        
        # Create a sample image
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        
        # Call the function
        result = detect_document_completeness(image)
        
        # Verify the result
        assert result['has_signature'] is True
        assert result['has_date'] is False
        assert result['is_complete'] is False

    @patch('processing.detect.signature')
    @patch('processing.detect.date')
    def test_detect_document_completeness_empty(self, mock_date, mock_signature):
        """Test document completeness detection for an empty document."""
        # Set up the mocks
        mock_signature.return_value = False
        mock_date.return_value = False
        
        # Create a sample image
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        
        # Call the function
        result = detect_document_completeness(image)
        
        # Verify the result
        assert result['has_signature'] is False
        assert result['has_date'] is False
        assert result['is_complete'] is False
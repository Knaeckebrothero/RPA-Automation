"""
Unit tests for the table_detection.py module.

This module contains tests for the table detection Streamlit page that provides
UI for testing PDF table, signature, and date detection functionality.
"""
import pytest
from unittest.mock import patch, MagicMock, call
import numpy as np
import cv2
from io import BytesIO

import streamlit as st


class TestTableDetection:
    """Test suite for the table_detection.py module."""

    @pytest.fixture
    def mock_streamlit_components(self):
        """Mock all Streamlit components used in table_detection.py."""
        with patch('table_detection.st') as mock_st:
            # Configure file uploader
            mock_file = MagicMock()
            mock_file.read.return_value = b'mock_pdf_content'
            mock_st.file_uploader.return_value = mock_file
            
            # Configure checkboxes
            mock_st.checkbox.side_effect = [True, True, True]  # tables, signatures, dates
            
            # Configure other components
            mock_st.columns.return_value = [MagicMock(), MagicMock()]
            mock_st.info = MagicMock()
            mock_st.warning = MagicMock()
            mock_st.write = MagicMock()
            mock_st.image = MagicMock()
            mock_st.table = MagicMock()
            
            yield mock_st

    @pytest.fixture
    def mock_image_array(self):
        """Create a mock image array for testing."""
        # Create a simple 100x100 RGB image
        return np.zeros((100, 100, 3), dtype=np.uint8)

    @pytest.fixture
    def mock_dependencies(self):
        """Mock all external dependencies."""
        with patch('table_detection.get_images_from_pdf') as mock_get_images, \
             patch('table_detection.create_ocr_reader') as mock_create_ocr, \
             patch('table_detection.PDF') as mock_pdf_class, \
             patch('table_detection.dtct') as mock_detect, \
             patch('table_detection.ocr_cell') as mock_ocr_cell, \
             patch('table_detection.cv2') as mock_cv2:
            
            # Configure mocks
            mock_ocr_reader = MagicMock()
            mock_create_ocr.return_value = mock_ocr_reader
            
            # Mock PDF instance
            mock_pdf_instance = MagicMock()
            mock_pdf_instance._signature_page_index = 0
            mock_pdf_class.return_value = mock_pdf_instance
            
            # Mock detection functions
            mock_detect.normalize_image_resolution.side_effect = lambda x: x
            mock_detect.tables.return_value = [np.array([[10, 10], [50, 10], [50, 50], [10, 50]])]
            mock_detect._detect_potential_signature_regions.return_value = [(60, 60, 20, 20)]
            mock_detect._detect_potential_date_regions.return_value = [(10, 80, 30, 10)]
            mock_detect.rows.return_value = [(0, 20), (20, 40)]
            mock_detect.cells.return_value = [(0, 25), (25, 50)]
            
            # Mock OCR
            mock_ocr_cell.return_value = "Test Text"
            
            # Mock cv2 functions
            mock_cv2.cvtColor.side_effect = lambda img, code: img
            mock_cv2.Canny.return_value = np.zeros((100, 100), dtype=np.uint8)
            mock_cv2.drawContours = MagicMock()
            mock_cv2.rectangle = MagicMock()
            mock_cv2.boundingRect.return_value = (10, 10, 40, 40)
            
            yield {
                'get_images_from_pdf': mock_get_images,
                'create_ocr_reader': mock_create_ocr,
                'ocr_reader': mock_ocr_reader,
                'pdf_class': mock_pdf_class,
                'pdf_instance': mock_pdf_instance,
                'detect': mock_detect,
                'ocr_cell': mock_ocr_cell,
                'cv2': mock_cv2
            }

    def test_no_file_uploaded(self):
        """Test behavior when no file is uploaded."""
        with patch('table_detection.st') as mock_st:
            mock_st.file_uploader.return_value = None
            mock_st.checkbox.side_effect = [False, False, False]
            
            # Import and run the module
            import table_detection
            
            # Verify only file uploader and checkboxes are called
            mock_st.file_uploader.assert_called_once()
            assert mock_st.checkbox.call_count == 3
            # No other processing should occur
            mock_st.image.assert_not_called()

    def test_file_upload_and_basic_display(self, mock_streamlit_components, mock_dependencies, mock_image_array):
        """Test file upload and basic image display."""
        # Set up mock images
        mock_dependencies['get_images_from_pdf'].return_value = [mock_image_array]
        
        # Import and run the module
        import table_detection
        
        # Verify file was processed
        mock_streamlit_components.file_uploader.assert_called_once_with(
            label="Upload PDF here", 
            type=["pdf"]
        )
        
        # Verify PDF content was read
        mock_file = mock_streamlit_components.file_uploader.return_value
        mock_file.read.assert_called_once()
        
        # Verify images were extracted
        mock_dependencies['get_images_from_pdf'].assert_called_once_with(b'mock_pdf_content')
        
        # Verify OCR reader was created
        mock_dependencies['create_ocr_reader'].assert_called_once_with(use_gpu=True)

    def test_signature_page_detection(self, mock_streamlit_components, mock_dependencies, mock_image_array):
        """Test signature page detection and display."""
        # Set up mock images and signature page
        mock_dependencies['get_images_from_pdf'].return_value = [mock_image_array, mock_image_array]
        mock_dependencies['pdf_instance']._signature_page_index = 1
        
        # Import and run the module
        import table_detection
        
        # Verify PDF processing
        mock_dependencies['pdf_instance'].extract_table_data.assert_called_once_with(
            ocr_reader=mock_dependencies['ocr_reader']
        )
        
        # Verify signature page info is displayed
        mock_streamlit_components.info.assert_called_with(
            "The application logic identified Page 2 as the signature page."
        )

    def test_no_signature_page_detected(self, mock_streamlit_components, mock_dependencies, mock_image_array):
        """Test behavior when no signature page is detected."""
        # Set up mock images with no signature page
        mock_dependencies['get_images_from_pdf'].return_value = [mock_image_array]
        mock_dependencies['pdf_instance']._signature_page_index = -1
        
        # Import and run the module
        import table_detection
        
        # Verify warning is displayed
        mock_streamlit_components.warning.assert_called_with(
            "Signature page could not be determined by the PDF class logic."
        )

    def test_edge_detection_display(self, mock_streamlit_components, mock_dependencies, mock_image_array):
        """Test edge detection and display."""
        # Set up mock images
        mock_dependencies['get_images_from_pdf'].return_value = [mock_image_array]
        
        # Import and run the module
        import table_detection
        
        # Verify edge detection
        mock_dependencies['cv2'].Canny.assert_called()
        
        # Verify columns are created for display
        mock_streamlit_components.columns.assert_called_with(2)
        
        # Verify images are displayed in columns
        assert mock_streamlit_components.image.call_count >= 2  # Original and edges

    def test_table_detection_enabled(self, mock_streamlit_components, mock_dependencies, mock_image_array):
        """Test table detection when enabled."""
        # Set up checkboxes: tables=True, signatures=False, dates=False
        mock_streamlit_components.checkbox.side_effect = [True, False, False]
        mock_dependencies['get_images_from_pdf'].return_value = [mock_image_array]
        
        # Import and run the module
        import table_detection
        
        # Verify table detection
        mock_dependencies['detect'].tables.assert_called()
        
        # Verify contours are drawn
        mock_dependencies['cv2'].drawContours.assert_called()
        
        # Verify table count is displayed
        calls = mock_streamlit_components.write.call_args_list
        assert any("Number of tables detected" in str(call) for call in calls)

    def test_signature_detection_on_signature_page(self, mock_streamlit_components, mock_dependencies, mock_image_array):
        """Test signature detection on the identified signature page."""
        # Set up checkboxes: tables=False, signatures=True, dates=False
        mock_streamlit_components.checkbox.side_effect = [False, True, False]
        mock_dependencies['get_images_from_pdf'].return_value = [mock_image_array]
        mock_dependencies['pdf_instance']._signature_page_index = 0
        
        # Import and run the module
        import table_detection
        
        # Verify signature detection
        mock_dependencies['detect']._detect_potential_signature_regions.assert_called()
        
        # Verify rectangles are drawn for signatures
        mock_dependencies['cv2'].rectangle.assert_called()
        
        # Verify signature region count is displayed
        calls = mock_streamlit_components.write.call_args_list
        assert any("potential signature regions detected" in str(call) for call in calls)

    def test_date_detection_on_signature_page(self, mock_streamlit_components, mock_dependencies, mock_image_array):
        """Test date detection on the identified signature page."""
        # Set up checkboxes: tables=False, signatures=False, dates=True
        mock_streamlit_components.checkbox.side_effect = [False, False, True]
        mock_dependencies['get_images_from_pdf'].return_value = [mock_image_array]
        mock_dependencies['pdf_instance']._signature_page_index = 0
        
        # Import and run the module
        import table_detection
        
        # Verify date detection
        mock_dependencies['detect']._detect_potential_date_regions.assert_called()
        
        # Verify rectangles are drawn for dates
        mock_dependencies['cv2'].rectangle.assert_called()
        
        # Verify date region count is displayed
        calls = mock_streamlit_components.write.call_args_list
        assert any("potential date regions detected" in str(call) for call in calls)

    def test_skip_detection_on_non_signature_page(self, mock_streamlit_components, mock_dependencies, mock_image_array):
        """Test that signature/date detection is skipped on non-signature pages."""
        # Set up checkboxes: all enabled
        mock_streamlit_components.checkbox.side_effect = [True, True, True]
        mock_dependencies['get_images_from_pdf'].return_value = [mock_image_array, mock_image_array]
        mock_dependencies['pdf_instance']._signature_page_index = 1  # Second page is signature page
        
        # Import and run the module
        import table_detection
        
        # Verify skip messages for first page
        calls = mock_streamlit_components.write.call_args_list
        assert any("is not the identified signature page" in str(call) for call in calls)

    def test_detailed_table_processing(self, mock_streamlit_components, mock_dependencies, mock_image_array):
        """Test detailed table processing with OCR."""
        # Set up to show detailed table processing (tables checkbox = False but tables exist)
        mock_streamlit_components.checkbox.side_effect = [False, False, False]
        mock_dependencies['get_images_from_pdf'].return_value = [mock_image_array]
        
        # Import and run the module
        import table_detection
        
        # Verify table processing
        mock_dependencies['detect'].rows.assert_called()
        mock_dependencies['detect'].cells.assert_called()
        mock_dependencies['ocr_cell'].assert_called()
        
        # Verify extracted table data is displayed
        mock_streamlit_components.table.assert_called()

    def test_no_signature_regions_detected(self, mock_streamlit_components, mock_dependencies, mock_image_array):
        """Test behavior when no signature regions are detected."""
        # Set up with no signature regions
        mock_streamlit_components.checkbox.side_effect = [False, True, False]
        mock_dependencies['get_images_from_pdf'].return_value = [mock_image_array]
        mock_dependencies['pdf_instance']._signature_page_index = 0
        mock_dependencies['detect']._detect_potential_signature_regions.return_value = []
        
        # Import and run the module
        import table_detection
        
        # Verify message about no signature regions
        calls = mock_streamlit_components.write.call_args_list
        assert any("No signature regions detected" in str(call) for call in calls)

    def test_no_date_regions_detected(self, mock_streamlit_components, mock_dependencies, mock_image_array):
        """Test behavior when no date regions are detected."""
        # Set up with no date regions
        mock_streamlit_components.checkbox.side_effect = [False, False, True]
        mock_dependencies['get_images_from_pdf'].return_value = [mock_image_array]
        mock_dependencies['pdf_instance']._signature_page_index = 0
        mock_dependencies['detect']._detect_potential_date_regions.return_value = []
        
        # Import and run the module
        import table_detection
        
        # Verify message about no date regions
        calls = mock_streamlit_components.write.call_args_list
        assert any("No date regions detected" in str(call) for call in calls)

    def test_multiple_pages_processing(self, mock_streamlit_components, mock_dependencies, mock_image_array):
        """Test processing multiple PDF pages."""
        # Set up multiple pages
        mock_dependencies['get_images_from_pdf'].return_value = [
            mock_image_array, 
            mock_image_array, 
            mock_image_array
        ]
        
        # Import and run the module
        import table_detection
        
        # Verify all pages are processed
        assert mock_dependencies['detect'].normalize_image_resolution.call_count == 3
        assert mock_dependencies['cv2'].Canny.call_count == 3

    def test_ocr_text_extraction(self, mock_streamlit_components, mock_dependencies, mock_image_array):
        """Test OCR text extraction from table cells."""
        # Set up for detailed table processing
        mock_streamlit_components.checkbox.side_effect = [False, False, False]
        mock_dependencies['get_images_from_pdf'].return_value = [mock_image_array]
        mock_dependencies['ocr_cell'].return_value = "Extracted Text"
        
        # Import and run the module
        import table_detection
        
        # Verify OCR was called for each cell
        assert mock_dependencies['ocr_cell'].call_count > 0
        
        # Verify extracted text is used
        mock_streamlit_components.table.assert_called_with([["Extracted Text", "Extracted Text"]] * 2)

    def test_image_color_conversion(self, mock_streamlit_components, mock_dependencies, mock_image_array):
        """Test proper image color space conversions."""
        mock_dependencies['get_images_from_pdf'].return_value = [mock_image_array]
        
        # Import and run the module
        import table_detection
        
        # Verify color conversions
        cv2_calls = mock_dependencies['cv2'].cvtColor.call_args_list
        # Should have RGB to BGR, BGR to RGB for edges, and BGR to RGB for result
        assert len(cv2_calls) >= 3
        
        # Check conversion codes were used
        assert any(call[0][1] == cv2.COLOR_RGB2BGR for call in cv2_calls)
        assert any(call[0][1] == cv2.COLOR_BGR2RGB for call in cv2_calls)
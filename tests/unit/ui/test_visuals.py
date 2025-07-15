"""
Unit tests for the ui.visuals module.

This module contains tests for the ui.visuals module, focusing on the logic
within the UI components rather than the Streamlit-specific rendering.
"""
import pytest
from unittest.mock import patch, MagicMock

import matplotlib.pyplot as plt
import streamlit as st

from ui.visuals import pie_submission_ratio, stage_badge, client_info_box


class TestVisuals:
    """Test suite for the ui.visuals module."""

    @pytest.fixture
    def mock_database(self):
        """Create a mock database for testing."""
        mock_db = MagicMock()
        mock_db.get_instance.return_value = mock_db
        return mock_db

    @patch('matplotlib.pyplot.subplots')
    def test_pie_submission_ratio_with_data(self, mock_subplots, mock_database):
        """Test pie_submission_ratio with actual data."""
        # Configure mock database to return data
        mock_database.query.side_effect = [
            [(5,)],  # clients_processed
            [(3,)],  # clients_processing
            [(10,)]  # total clients
        ]

        # Configure mock subplots
        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_subplots.return_value = (mock_fig, mock_ax)

        # Call the function
        with patch('cls.database.Database.get_instance', return_value=mock_database):
            result = pie_submission_ratio()

        # Verify the result
        assert result == mock_fig
        mock_ax.pie.assert_called_once()
        # Check that the sizes are correct (5 processed, 3 processing, 2 no submission)
        sizes = mock_ax.pie.call_args[0][0]
        assert sizes == [5, 3, 2]  # 10 total - 5 processed - 3 processing = 2 no submission

    @patch('matplotlib.pyplot.subplots')
    def test_pie_submission_ratio_no_data(self, mock_subplots, mock_database):
        """Test pie_submission_ratio with no data."""
        # Configure mock database to return no data
        mock_database.query.side_effect = [
            [(0,)],  # clients_processed
            [(0,)],  # clients_processing
            [(0,)]   # total clients
        ]

        # Configure mock subplots
        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_subplots.return_value = (mock_fig, mock_ax)

        # Call the function
        with patch('cls.database.Database.get_instance', return_value=mock_database):
            result = pie_submission_ratio()

        # Verify the result
        assert result == mock_fig
        mock_ax.pie.assert_called_once()
        # Check that the sizes are correct (1 for 'No data')
        sizes = mock_ax.pie.call_args[0][0]
        assert sizes == [1]

    def test_stage_badge_with_valid_stage(self):
        """Test stage_badge with a valid stage."""
        # Test with stage 1
        result = stage_badge(1)
        assert "Waiting for documents" in result
        assert "#FFA500" in result  # Orange color

        # Test with stage 3
        result = stage_badge(3)
        assert "Certification" in result
        assert "#9370DB" in result  # Purple color

    def test_stage_badge_with_invalid_stage(self):
        """Test stage_badge with an invalid stage."""
        result = stage_badge(99)
        assert "Unknown" in result
        assert "#FF0000" in result  # Red color

    def test_stage_badge_pure_string(self):
        """Test stage_badge with pure_string=True."""
        # Test with stage 2
        result = stage_badge(2, pure_string=True)
        assert result == "Data verification"

        # Test with invalid stage
        result = stage_badge(99, pure_string=True)
        assert result == "Unknown"

    @patch('streamlit.subheader')
    @patch('streamlit.markdown')
    @patch('streamlit.columns')
    @patch('streamlit.divider')
    def test_client_info_box_with_data(self, mock_divider, mock_columns, mock_markdown, mock_subheader):
        """Test client_info_box with client data."""
        # Create mock columns
        col1 = MagicMock()
        col2 = MagicMock()
        mock_columns.return_value = [col1, col2]

        # Create client data
        client_data = {
            'institute': 'Test Bank',
            'bafin_id': '12345',
            'address': '123 Test St',
            'city': 'Test City',
            'contact_person': 'John Doe',
            'phone': '123-456-7890',
            'fax': '123-456-7891',
            'email': 'john@example.com'
        }

        # Call the function
        client_info_box(client_data)

        # Verify the function calls
        mock_subheader.assert_called_once_with("Client Information")
        mock_columns.assert_called_once_with(2)
        mock_divider.assert_called_once()

        # Verify column content
        assert col1.markdown.call_count == 4
        assert col2.markdown.call_count == 4

    @patch('streamlit.warning')
    def test_client_info_box_no_data(self, mock_warning):
        """Test client_info_box with no client data."""
        # Call the function with None
        client_info_box(None)

        # Verify warning was shown
        mock_warning.assert_called_once_with("No client data available")
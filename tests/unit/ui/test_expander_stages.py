"""
Unit tests for the ui.expander_stages module.

This module contains tests for the ui.expander_stages module, focusing on the logic
within the UI components rather than the Streamlit-specific rendering.
"""
import pytest
from unittest.mock import patch, MagicMock

import streamlit as st
import pandas as pd

from ui.expander_stages import stage_1, stage_2, stage_3, stage_4, _icon


class TestExpanderStages:
    """Test suite for the ui.expander_stages module."""

    @pytest.fixture
    def mock_database(self):
        """Create a mock database for testing."""
        mock_db = MagicMock()
        mock_db.get_instance.return_value = mock_db
        return mock_db

    def test_icon_function_true(self):
        """Test _icon function with icon=True."""
        result = _icon(True)
        assert "✅" in result

    def test_icon_function_false(self):
        """Test _icon function with icon=False."""
        result = _icon(False)
        assert "❌" in result

    @patch('streamlit.expander')
    def test_stage_1_not_current(self, mock_expander, mock_database):
        """Test stage_1 when it's not the current stage."""
        # Configure mock
        mock_expander_instance = MagicMock()
        mock_expander.return_value.__enter__.return_value = mock_expander_instance
        
        # Call the function with stage 2 as current
        stage_1(case_id=1, current_stage=2, db=mock_database)
        
        # Verify the expander was created with the correct label
        mock_expander.assert_called_once()
        assert "Stage 1" in mock_expander.call_args[0][0]
        # Verify no interactions with the expander content since it's not the current stage
        assert mock_expander_instance.button.call_count == 0

    @patch('streamlit.expander')
    def test_stage_1_is_current(self, mock_expander, mock_database):
        """Test stage_1 when it is the current stage."""
        # Configure mocks
        mock_expander_instance = MagicMock()
        mock_expander.return_value.__enter__.return_value = mock_expander_instance
        
        # Configure database mock to return case data
        mock_database.query.return_value = [(1, 'Test Bank', 12345, 'test@example.com')]
        
        # Call the function with stage 1 as current
        stage_1(case_id=1, current_stage=1, db=mock_database)
        
        # Verify the expander was created and is open
        mock_expander.assert_called_once()
        assert mock_expander.call_args[1].get('expanded', False) is True
        
        # Verify interactions with the expander content
        assert mock_expander_instance.markdown.call_count > 0
        assert mock_expander_instance.button.call_count > 0

    @patch('streamlit.expander')
    def test_stage_2_not_current(self, mock_expander, mock_database):
        """Test stage_2 when it's not the current stage."""
        # Configure mock
        mock_expander_instance = MagicMock()
        mock_expander.return_value.__enter__.return_value = mock_expander_instance
        
        # Call the function with stage 1 as current (before stage 2)
        stage_2(case_id=1, current_stage=1, db=mock_database)
        
        # Verify the expander was created with the correct label
        mock_expander.assert_called_once()
        assert "Stage 2" in mock_expander.call_args[0][0]
        # Verify it's disabled (not expanded and no interactions)
        assert mock_expander.call_args[1].get('expanded', False) is False
        assert mock_expander_instance.markdown.call_count == 0

    @patch('streamlit.expander')
    def test_stage_2_is_current(self, mock_expander, mock_database):
        """Test stage_2 when it is the current stage."""
        # Configure mocks
        mock_expander_instance = MagicMock()
        mock_expander.return_value.__enter__.return_value = mock_expander_instance
        
        # Configure database mock to return document data
        mock_database.query.return_value = [(1, 'document1.pdf', 'path/to/doc1.pdf', 'hash1')]
        
        # Call the function with stage 2 as current
        stage_2(case_id=1, current_stage=2, db=mock_database)
        
        # Verify the expander was created and is open
        mock_expander.assert_called_once()
        assert mock_expander.call_args[1].get('expanded', False) is True
        
        # Verify interactions with the expander content
        assert mock_expander_instance.markdown.call_count > 0
        assert mock_expander_instance.dataframe.call_count > 0

    @patch('streamlit.expander')
    def test_stage_3_not_current(self, mock_expander, mock_database):
        """Test stage_3 when it's not the current stage."""
        # Configure mock
        mock_expander_instance = MagicMock()
        mock_expander.return_value.__enter__.return_value = mock_expander_instance
        
        # Call the function with stage 2 as current (before stage 3)
        stage_3(case_id=1, current_stage=2, db=mock_database)
        
        # Verify the expander was created with the correct label
        mock_expander.assert_called_once()
        assert "Stage 3" in mock_expander.call_args[0][0]
        # Verify it's disabled (not expanded and no interactions)
        assert mock_expander.call_args[1].get('expanded', False) is False
        assert mock_expander_instance.markdown.call_count == 0

    @patch('streamlit.expander')
    def test_stage_3_is_current(self, mock_expander, mock_database):
        """Test stage_3 when it is the current stage."""
        # Configure mocks
        mock_expander_instance = MagicMock()
        mock_expander.return_value.__enter__.return_value = mock_expander_instance
        
        # Configure database mock to return document data
        mock_database.query.side_effect = [
            [(1, 'Test Bank', 12345)],  # Client info
            [(1, 'document1.pdf', 'path/to/doc1.pdf', 'hash1')]  # Document info
        ]
        
        # Call the function with stage 3 as current
        stage_3(case_id=1, current_stage=3, db=mock_database)
        
        # Verify the expander was created and is open
        mock_expander.assert_called_once()
        assert mock_expander.call_args[1].get('expanded', False) is True
        
        # Verify interactions with the expander content
        assert mock_expander_instance.markdown.call_count > 0
        assert mock_expander_instance.button.call_count > 0

    @patch('streamlit.expander')
    def test_stage_4_not_current(self, mock_expander, mock_database):
        """Test stage_4 when it's not the current stage."""
        # Configure mock
        mock_expander_instance = MagicMock()
        mock_expander.return_value.__enter__.return_value = mock_expander_instance
        
        # Call the function with stage 3 as current (before stage 4)
        stage_4(case_id=1, current_stage=3, db=mock_database)
        
        # Verify the expander was created with the correct label
        mock_expander.assert_called_once()
        assert "Stage 4" in mock_expander.call_args[0][0]
        # Verify it's disabled (not expanded and no interactions)
        assert mock_expander.call_args[1].get('expanded', False) is False
        assert mock_expander_instance.markdown.call_count == 0

    @patch('streamlit.expander')
    def test_stage_4_is_current(self, mock_expander, mock_database):
        """Test stage_4 when it is the current stage."""
        # Configure mocks
        mock_expander_instance = MagicMock()
        mock_expander.return_value.__enter__.return_value = mock_expander_instance
        
        # Configure database mock to return client data
        mock_database.query.return_value = [(1, 'Test Bank', 12345)]
        
        # Call the function with stage 4 as current
        stage_4(case_id=1, current_stage=4, db=mock_database)
        
        # Verify the expander was created and is open
        mock_expander.assert_called_once()
        assert mock_expander.call_args[1].get('expanded', False) is True
        
        # Verify interactions with the expander content
        assert mock_expander_instance.markdown.call_count > 0
        assert mock_expander_instance.button.call_count > 0

    @patch('streamlit.expander')
    def test_stage_4_completed(self, mock_expander, mock_database):
        """Test stage_4 when the case is already completed (stage 5)."""
        # Configure mocks
        mock_expander_instance = MagicMock()
        mock_expander.return_value.__enter__.return_value = mock_expander_instance
        
        # Call the function with stage 5 (completed)
        stage_4(case_id=1, current_stage=5, db=mock_database)
        
        # Verify the expander was created with the correct label
        mock_expander.assert_called_once()
        assert "Stage 4" in mock_expander.call_args[0][0]
        assert "Completed" in mock_expander.call_args[0][0]
        
        # Verify interactions with the expander content
        assert mock_expander_instance.markdown.call_count > 0
        # No buttons should be shown for completed stage
        assert mock_expander_instance.button.call_count == 0
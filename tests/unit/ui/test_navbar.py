"""
Unit tests for the ui.navbar module.

This module contains tests for the ui.navbar module, focusing on the logic
within the UI components rather than the Streamlit-specific rendering.
"""
import pytest
from unittest.mock import patch, MagicMock

import streamlit as st

from ui.navbar import navbar
from cls.accesscontrol import AccessControl


class TestNavbar:
    """Test suite for the ui.navbar module."""

    @pytest.fixture
    def mock_database(self):
        """Create a mock database for testing."""
        mock_db = MagicMock()
        mock_db.get_instance.return_value = mock_db
        return mock_db

    @pytest.fixture
    def setup_session_state(self):
        """Set up session state for testing."""
        # Clear any existing session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        
        # Set up basic session state
        st.session_state['user_role'] = 'admin'
        st.session_state['user_id'] = 1
        st.session_state['username'] = 'testuser'
        st.session_state['session_key'] = 'test_session_key'

    @patch('streamlit.sidebar.title')
    @patch('streamlit.sidebar.write')
    @patch('streamlit.sidebar.button')
    @patch('streamlit.sidebar.markdown')
    @patch('cls.accesscontrol.AccessControl.can_access_feature')
    def test_navbar_admin_user(self, mock_can_access_feature, mock_markdown, 
                              mock_button, mock_write, mock_title, setup_session_state):
        """Test navbar with admin user."""
        # Configure mocks
        mock_can_access_feature.return_value = True
        mock_button.side_effect = [False, False, False, False, False]  # No buttons clicked
        
        # Call the navbar function
        page = navbar()
        
        # Verify the result
        assert page == 0  # Default page for admin
        mock_title.assert_called_once_with('Navigation')
        assert mock_button.call_count == 5  # Home, Active Cases, Settings, About, Logout
        mock_can_access_feature.assert_called_once()

    @patch('streamlit.sidebar.title')
    @patch('streamlit.sidebar.write')
    @patch('streamlit.sidebar.button')
    @patch('streamlit.sidebar.markdown')
    @patch('cls.accesscontrol.AccessControl.can_access_feature')
    @patch('cls.accesscontrol.AccessControl.get_accessible_clients')
    def test_navbar_auditor_with_cases(self, mock_get_accessible_clients, mock_can_access_feature,
                                      mock_markdown, mock_button, mock_write, mock_title):
        """Test navbar with auditor user who has assigned cases."""
        # Set up session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.session_state['user_role'] = 'auditor'
        st.session_state['user_id'] = 2
        st.session_state['username'] = 'auditor'
        
        # Configure mocks
        mock_can_access_feature.return_value = False  # Auditor can't access settings
        mock_get_accessible_clients.return_value = [1, 2]  # Has assigned clients
        mock_button.side_effect = [False, False, False, False]  # No buttons clicked
        
        # Call the navbar function
        page = navbar()
        
        # Verify the result
        assert page == 1  # Default page for auditor with cases is Active Cases
        mock_title.assert_called_once_with('Navigation')
        assert mock_button.call_count == 4  # Home, Active Cases, About, Logout
        mock_can_access_feature.assert_called_once()
        mock_get_accessible_clients.assert_called()

    @patch('streamlit.sidebar.title')
    @patch('streamlit.sidebar.write')
    @patch('streamlit.sidebar.button')
    @patch('streamlit.sidebar.markdown')
    @patch('cls.accesscontrol.AccessControl.can_access_feature')
    @patch('cls.accesscontrol.AccessControl.get_accessible_clients')
    def test_navbar_auditor_no_cases(self, mock_get_accessible_clients, mock_can_access_feature,
                                    mock_markdown, mock_button, mock_write, mock_title):
        """Test navbar with auditor user who has no assigned cases."""
        # Set up session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.session_state['user_role'] = 'auditor'
        st.session_state['user_id'] = 2
        st.session_state['username'] = 'auditor'
        
        # Configure mocks
        mock_can_access_feature.return_value = False  # Auditor can't access settings
        mock_get_accessible_clients.return_value = []  # No assigned clients
        mock_button.side_effect = [False, False, False, False]  # No buttons clicked
        
        # Call the navbar function
        page = navbar()
        
        # Verify the result
        assert page == 0  # Default page for auditor with no cases is Home
        mock_title.assert_called_once_with('Navigation')
        assert mock_button.call_count == 4  # Home, Active Cases, About, Logout
        mock_can_access_feature.assert_called_once()
        mock_get_accessible_clients.assert_called()

    @patch('streamlit.sidebar.title')
    @patch('streamlit.sidebar.write')
    @patch('streamlit.sidebar.button')
    @patch('streamlit.sidebar.markdown')
    @patch('cls.accesscontrol.AccessControl.can_access_feature')
    def test_navbar_button_clicks(self, mock_can_access_feature, mock_markdown, 
                                 mock_button, mock_write, mock_title, setup_session_state):
        """Test navbar button clicks."""
        # Configure mocks
        mock_can_access_feature.return_value = True
        
        # Test Home button
        mock_button.side_effect = [True, False, False, False, False]  # Home button clicked
        page = navbar()
        assert page == 0
        
        # Test Active Cases button
        mock_button.side_effect = [False, True, False, False, False]  # Active Cases button clicked
        page = navbar()
        assert page == 1
        
        # Test Settings button
        mock_button.side_effect = [False, False, True, False, False]  # Settings button clicked
        page = navbar()
        assert page == 2
        
        # Test About button
        mock_button.side_effect = [False, False, False, True, False]  # About button clicked
        page = navbar()
        assert page == 3

    @patch('streamlit.sidebar.title')
    @patch('streamlit.sidebar.write')
    @patch('streamlit.sidebar.button')
    @patch('streamlit.sidebar.markdown')
    @patch('cls.accesscontrol.AccessControl.can_access_feature')
    @patch('workflow.security.logout')
    @patch('streamlit.rerun')
    def test_navbar_logout(self, mock_rerun, mock_logout, mock_can_access_feature, 
                          mock_markdown, mock_button, mock_write, mock_title, 
                          setup_session_state, mock_database):
        """Test navbar logout functionality."""
        # Configure mocks
        mock_can_access_feature.return_value = True
        mock_button.side_effect = [False, False, False, False, True]  # Logout button clicked
        
        # Call the navbar function
        navbar(database=mock_database)
        
        # Verify the logout functionality
        mock_logout.assert_called_once_with('test_session_key', mock_database)
        assert st.session_state['session_key'] is None
        assert st.session_state['user_id'] is None
        assert st.session_state['user_role'] is None
        assert st.session_state['username'] is None
        mock_rerun.assert_called_once()

    @patch('streamlit.sidebar.title')
    @patch('streamlit.sidebar.write')
    @patch('streamlit.sidebar.button')
    @patch('streamlit.sidebar.markdown')
    @patch('cls.accesscontrol.AccessControl.can_access_feature')
    def test_navbar_existing_page(self, mock_can_access_feature, mock_markdown, 
                                 mock_button, mock_write, mock_title, setup_session_state):
        """Test navbar with existing page in session state."""
        # Set existing page in session state
        st.session_state['page'] = 2
        
        # Configure mocks
        mock_can_access_feature.return_value = True
        mock_button.side_effect = [False, False, False, False, False]  # No buttons clicked
        
        # Call the navbar function
        page = navbar()
        
        # Verify the result
        assert page == 2  # Should return the existing page
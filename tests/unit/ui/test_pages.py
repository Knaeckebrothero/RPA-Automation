"""
Unit tests for the ui.pages module.

This module contains tests for the ui.pages module, focusing on the logic
within the UI components rather than the Streamlit-specific rendering.
"""
import pytest
from unittest.mock import patch, MagicMock

import streamlit as st
import pandas as pd

from ui.pages import home, active_cases, settings, about, login
from cls.database import Database
from cls.mailclient import Mailclient
from cls.accesscontrol import AccessControl


class TestPages:
    """Test suite for the ui.pages module."""

    @pytest.fixture
    def mock_database(self):
        """Create a mock database for testing."""
        mock_db = MagicMock(spec=Database)
        mock_db.get_instance.return_value = mock_db
        return mock_db

    @patch('streamlit.header')
    @patch('streamlit.markdown')
    @patch('streamlit.info')
    @patch('ui.visuals.display_welcome_message')
    def test_home_no_cases(self, mock_welcome, mock_info, mock_markdown, mock_header, mock_database):
        """Test home page with no active cases."""
        # Configure mock database to return empty dataframe
        mock_database.get_active_client_cases.return_value = pd.DataFrame()

        # Call the home function
        home(database=mock_database)

        # Verify expected behavior
        mock_header.assert_called_once_with('Document Fetcher Dashboard')
        mock_welcome.assert_called_once()
        mock_info.assert_called_once()  # Should show info message about no active cases

    @patch('streamlit.header')
    @patch('streamlit.markdown')
    @patch('streamlit.info')
    @patch('ui.visuals.display_welcome_message')
    def test_home_with_cases(self, mock_welcome, mock_info, mock_markdown, mock_header, mock_database):
        """Test home page with active cases."""
        # Configure mock database to return a dataframe with cases
        mock_database.get_active_client_cases.return_value = pd.DataFrame({
            'case_id': [1, 2],
            'institute': ['Test Bank 1', 'Test Bank 2'],
            'stage': [1, 2]
        })

        # Call the home function
        home(database=mock_database)

        # Verify expected behavior
        mock_header.assert_called_once_with('Document Fetcher Dashboard')
        mock_welcome.assert_called_once()
        # Should not show info message about no active cases
        mock_info.assert_not_called()

    @patch('streamlit.header')
    @patch('streamlit.markdown')
    @patch('streamlit.info')
    @patch('ui.visuals.display_welcome_message')
    def test_home_with_mailclient(self, mock_welcome, mock_info, mock_markdown, mock_header, mock_database):
        """Test home page with mailclient provided."""
        # Configure mock database to return a dataframe with cases
        mock_database.get_active_client_cases.return_value = pd.DataFrame({
            'case_id': [1, 2],
            'institute': ['Test Bank 1', 'Test Bank 2'],
            'stage': [1, 2]
        })

        # Create mock mailclient
        mock_mailclient = MagicMock(spec=Mailclient)

        # Call the home function with mailclient
        home(mailclient=mock_mailclient, database=mock_database)

        # Verify expected behavior
        mock_header.assert_called_once_with('Document Fetcher Dashboard')
        mock_welcome.assert_called_once()
        # Should not show info message about no active cases
        mock_info.assert_not_called()
        # Mailclient should be used (this would depend on the implementation details)

    @patch('streamlit.header')
    @patch('streamlit.selectbox')
    @patch('streamlit.tabs')
    @patch('streamlit.info')
    def test_active_cases_no_cases(self, mock_info, mock_tabs, mock_selectbox, mock_header, mock_database):
        """Test active cases page with no active cases."""
        # Configure mock database to return empty dataframe
        mock_database.get_active_client_cases.return_value = pd.DataFrame()

        # Call the active_cases function
        active_cases(database=mock_database)

        # Verify expected behavior
        mock_header.assert_called_once_with('Active Cases')
        mock_info.assert_called_once()  # Should show info message about no active cases
        # Should not create tabs or selectbox if no cases
        mock_tabs.assert_not_called()
        mock_selectbox.assert_not_called()

    @patch('streamlit.header')
    @patch('streamlit.selectbox')
    @patch('streamlit.tabs')
    @patch('streamlit.info')
    @patch('ui.expander_stages.stage_1')
    @patch('ui.expander_stages.stage_2')
    @patch('ui.expander_stages.stage_3')
    @patch('ui.expander_stages.stage_4')
    @patch('cls.accesscontrol.AccessControl.can_access_client')
    @patch('cls.accesscontrol.AccessControl.can_access_feature')
    def test_active_cases_with_cases(self, mock_can_access_feature, mock_can_access_client, 
                                    mock_stage_4, mock_stage_3, mock_stage_2, mock_stage_1,
                                    mock_info, mock_tabs, mock_selectbox, mock_header, mock_database):
        """Test active cases page with active cases."""
        # Configure mock database to return a dataframe with cases
        mock_database.get_active_client_cases.return_value = pd.DataFrame({
            'case_id': [1],
            'client_id': [100],
            'institute': ['Test Bank'],
            'stage': [2]
        })

        # Configure mocks
        mock_can_access_client.return_value = True
        mock_can_access_feature.return_value = True
        mock_tabs.return_value = [MagicMock(), MagicMock()]
        mock_selectbox.return_value = 'Test Bank (Case #1)'

        # Set up session state
        if 'selected_case_id' in st.session_state:
            del st.session_state['selected_case_id']

        # Call the active_cases function
        active_cases(database=mock_database)

        # Verify expected behavior
        mock_header.assert_called_once_with('Active Cases')
        mock_info.assert_not_called()  # Should not show info message about no active cases
        mock_tabs.assert_called_once()
        mock_selectbox.assert_called_once()
        mock_stage_1.assert_called_once()
        mock_stage_2.assert_called_once()
        mock_stage_3.assert_called_once()
        mock_stage_4.assert_called_once()

    @patch('streamlit.header')
    @patch('streamlit.selectbox')
    @patch('streamlit.tabs')
    @patch('streamlit.info')
    @patch('streamlit.error')
    @patch('cls.accesscontrol.AccessControl.can_access_client')
    def test_active_cases_no_access(self, mock_can_access_client, mock_error, 
                                   mock_info, mock_tabs, mock_selectbox, mock_header, mock_database):
        """Test active cases page when user doesn't have access to the selected case."""
        # Configure mock database to return a dataframe with cases
        mock_database.get_active_client_cases.return_value = pd.DataFrame({
            'case_id': [1],
            'client_id': [100],
            'institute': ['Test Bank'],
            'stage': [2]
        })

        # Configure mocks
        mock_can_access_client.return_value = False  # User doesn't have access
        mock_tabs.return_value = [MagicMock(), MagicMock()]
        mock_selectbox.return_value = 'Test Bank (Case #1)'

        # Set up session state
        if 'selected_case_id' in st.session_state:
            del st.session_state['selected_case_id']

        # Call the active_cases function
        active_cases(database=mock_database)

        # Verify expected behavior
        mock_header.assert_called_once_with('Active Cases')
        mock_error.assert_called_once()  # Should show error message about no access

    @patch('streamlit.header')
    def test_about(self, mock_header):
        """Test about page."""
        # Call the about function
        about()

        # Verify expected behavior
        mock_header.assert_called_once_with('About Document Fetcher')

    @patch('streamlit.title')
    @patch('streamlit.text_input')
    @patch('streamlit.button')
    @patch('streamlit.error')
    @patch('workflow.security.verify_password')
    def test_login_successful(self, mock_verify_password, mock_error, mock_button, 
                             mock_text_input, mock_title, mock_database):
        """Test successful login."""
        # Configure mocks
        mock_text_input.side_effect = ['testuser', 'password']
        mock_button.return_value = True
        mock_verify_password.return_value = (True, 1, 'admin')

        # Set up session state
        if 'authenticated' in st.session_state:
            del st.session_state['authenticated']

        # Call the login function
        login(database=mock_database)

        # Verify expected behavior
        assert st.session_state['authenticated'] == True
        assert st.session_state['user_id'] == 1
        assert st.session_state['username'] == 'testuser'
        assert st.session_state['user_role'] == 'admin'
        mock_error.assert_not_called()

    @patch('streamlit.title')
    @patch('streamlit.text_input')
    @patch('streamlit.button')
    @patch('streamlit.error')
    @patch('workflow.security.verify_password')
    def test_login_failed(self, mock_verify_password, mock_error, mock_button, 
                         mock_text_input, mock_title, mock_database):
        """Test failed login."""
        # Configure mocks
        mock_text_input.side_effect = ['testuser', 'wrong_password']
        mock_button.return_value = True
        mock_verify_password.return_value = (False, None, None)

        # Set up session state
        if 'authenticated' in st.session_state:
            del st.session_state['authenticated']

        # Call the login function
        login(database=mock_database)

        # Verify expected behavior
        assert 'authenticated' not in st.session_state
        mock_error.assert_called_once()

    @patch('streamlit.title')
    @patch('streamlit.text_input')
    @patch('streamlit.button')
    @patch('streamlit.error')
    @patch('workflow.security.verify_password')
    def test_login_no_button_click(self, mock_verify_password, mock_error, mock_button, 
                                  mock_text_input, mock_title, mock_database):
        """Test login page when login button is not clicked."""
        # Configure mocks
        mock_text_input.side_effect = ['testuser', 'password']
        mock_button.return_value = False  # Button not clicked

        # Set up session state
        if 'authenticated' in st.session_state:
            del st.session_state['authenticated']

        # Call the login function
        login(database=mock_database)

        # Verify expected behavior
        assert 'authenticated' not in st.session_state
        mock_verify_password.assert_not_called()  # Password verification should not be called
        mock_error.assert_not_called()  # No error should be displayed

    @patch('streamlit.header')
    @patch('streamlit.tabs')
    @patch('streamlit.selectbox')
    @patch('streamlit.text_input')
    @patch('streamlit.button')
    def test_settings_user_management(self, mock_button, mock_text_input, mock_selectbox, 
                                     mock_tabs, mock_header, mock_database):
        """Test settings page user management tab."""
        # Configure mocks
        mock_tabs.return_value = [MagicMock(), MagicMock(), MagicMock(), MagicMock()]

        # Set up session state for admin user
        st.session_state['user_role'] = 'admin'

        # Call the settings function
        settings(database=mock_database)

        # Verify expected behavior
        mock_header.assert_called_once_with('Settings')
        mock_tabs.assert_called_once()

    @patch('streamlit.header')
    @patch('streamlit.tabs')
    @patch('streamlit.warning')
    def test_settings_non_admin_user(self, mock_warning, mock_tabs, mock_header, mock_database):
        """Test settings page with non-admin user."""
        # Configure mocks
        mock_tabs.return_value = [MagicMock(), MagicMock(), MagicMock(), MagicMock()]

        # Set up session state for non-admin user
        st.session_state['user_role'] = 'user'

        # Call the settings function
        settings(database=mock_database)

        # Verify expected behavior
        mock_header.assert_called_once_with('Settings')
        mock_tabs.assert_called_once()
        # Should show warning for restricted tabs
        assert mock_warning.call_count > 0

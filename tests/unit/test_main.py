"""
Unit tests for the main.py module.

This module contains tests for the main application entry point, including
Streamlit configuration, session state management, authentication flow, and
page routing logic.
"""
import pytest
from unittest.mock import patch, MagicMock, call
import os
import sys

# Add src to path for imports
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src'))
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from main import main, _get_database, _get_mailclient


class TestMain:
    """Test suite for the main.py module."""

    @pytest.fixture
    def mock_streamlit(self):
        """Mock all Streamlit components used in main.py."""
        with patch('main.st') as mock_st:
            # Create a mock session state
            mock_session_state = {
                'rerun_counter': 0,
                'session_key': None,
                'user_id': None,
                'user_role': None,
                'page': 0
            }
            
            # Configure mock
            mock_st.session_state = mock_session_state
            mock_st.rerun = MagicMock()
            mock_st.stop = MagicMock()
            
            yield mock_st

    @pytest.fixture
    def mock_env_vars(self):
        """Set up environment variables for testing."""
        env_vars = {
            'LOG_LEVEL_CONSOLE': '20',
            'LOG_LEVEL_FILE': '10',
            'LOG_PATH': '/tmp/test_logs',
            'DEV_MODE': 'false'
        }
        with patch.dict(os.environ, env_vars):
            yield env_vars

    @pytest.fixture
    def mock_dependencies(self):
        """Mock all external dependencies."""
        with patch('main.load_dotenv') as mock_load_dotenv, \
             patch('main.find_dotenv') as mock_find_dotenv, \
             patch('main.configure_global_logger') as mock_configure_logger, \
             patch('main.cls.Database') as mock_db_class, \
             patch('main.cls.Mailclient') as mock_mail_class, \
             patch('main.navbar') as mock_navbar, \
             patch('main.page') as mock_pages, \
             patch('main.sec') as mock_security:
            
            # Configure mocks
            mock_find_dotenv.return_value = '.env'
            mock_db_instance = MagicMock()
            mock_mail_instance = MagicMock()
            mock_db_class.return_value.get_instance.return_value = mock_db_instance
            mock_mail_class.get_instance.return_value = mock_mail_instance
            mock_navbar.return_value = 0  # Default to home page
            
            yield {
                'load_dotenv': mock_load_dotenv,
                'find_dotenv': mock_find_dotenv,
                'configure_logger': mock_configure_logger,
                'database_class': mock_db_class,
                'mailclient_class': mock_mail_class,
                'navbar': mock_navbar,
                'pages': mock_pages,
                'security': mock_security,
                'db_instance': mock_db_instance,
                'mail_instance': mock_mail_instance
            }

    def test_get_database_cached(self, mock_dependencies):
        """Test that _get_database returns a cached database instance."""
        # First call
        db1 = _get_database()
        # Second call should return same instance (cached)
        db2 = _get_database()
        
        assert db1 == db2
        assert db1 == mock_dependencies['db_instance']
        # Should only create one instance due to caching
        mock_dependencies['database_class'].assert_called_once()

    def test_get_mailclient_cached(self, mock_dependencies):
        """Test that _get_mailclient returns a cached mailclient instance."""
        # First call
        mail1 = _get_mailclient()
        # Second call should return same instance (cached)
        mail2 = _get_mailclient()
        
        assert mail1 == mail2
        assert mail1 == mock_dependencies['mail_instance']
        # Should only call get_instance once due to caching
        mock_dependencies['mailclient_class'].get_instance.assert_called_once()

    def test_main_initial_setup(self, mock_streamlit, mock_env_vars, mock_dependencies):
        """Test main function initial setup and configuration."""
        # Run main
        main()
        
        # Verify Streamlit configuration
        mock_streamlit.set_page_config.assert_called_once_with(
            layout="wide",
            page_title="Document Fetcher",
            initial_sidebar_state="collapsed",
            page_icon=":page_with_curl:",
            menu_items={
                'Get Help': 'https://www.extremelycoolapp.com/help',
                'Report a bug': "https://www.extremelycoolapp.com/bug",
                'About': "# This is a header. This is an *extremely* cool app!"
            }
        )
        
        # Verify logo is set
        mock_streamlit.logo.assert_called_once()
        
        # Verify environment variables are loaded
        mock_dependencies['load_dotenv'].assert_called_once()
        
        # Verify logger is configured
        mock_dependencies['configure_logger'].assert_called_once_with(
            console_level=20,
            file_level=10,
            logging_directory='/tmp/test_logs'
        )

    def test_main_dev_mode_warning(self, mock_streamlit, mock_dependencies):
        """Test that DEV_MODE triggers a warning."""
        with patch.dict(os.environ, {'DEV_MODE': 'true'}):
            with patch('main.log') as mock_log:
                main()
                mock_log.warning.assert_called_with('DEV_MODE flag set, app is running in development mode.')

    def test_main_unauthenticated_user(self, mock_streamlit, mock_env_vars, mock_dependencies):
        """Test main function behavior for unauthenticated users."""
        # Set up unauthenticated state
        mock_streamlit.session_state['session_key'] = None
        mock_dependencies['pages'].login.return_value = False
        
        # Run main
        main()
        
        # Verify login page is shown
        mock_dependencies['pages'].login.assert_called_once_with(database=mock_dependencies['db_instance'])
        
        # Verify execution stops
        mock_streamlit.stop.assert_called_once()

    def test_main_successful_authentication(self, mock_streamlit, mock_env_vars, mock_dependencies):
        """Test main function behavior when user successfully authenticates."""
        # Set up login success
        mock_streamlit.session_state['session_key'] = None
        mock_dependencies['pages'].login.return_value = True
        
        # Run main
        main()
        
        # Verify login page is shown
        mock_dependencies['pages'].login.assert_called_once()
        
        # Verify page rerun is triggered
        mock_streamlit.rerun.assert_called_once()

    def test_main_authenticated_user(self, mock_streamlit, mock_env_vars, mock_dependencies):
        """Test main function behavior for authenticated users."""
        # Set up authenticated state
        mock_streamlit.session_state['session_key'] = 'valid_session_key'
        mock_dependencies['security'].validate_session.return_value = 'user123'
        mock_dependencies['security'].get_user_role.return_value = 'admin'
        
        # Run main
        main()
        
        # Verify session validation
        mock_dependencies['security'].validate_session.assert_called_once_with(
            'valid_session_key', 
            mock_dependencies['db_instance']
        )
        
        # Verify user role is fetched
        mock_dependencies['security'].get_user_role.assert_called_once_with(
            'user123', 
            mock_dependencies['db_instance']
        )
        
        # Verify session state is updated
        assert mock_streamlit.session_state['user_id'] == 'user123'
        assert mock_streamlit.session_state['user_role'] == 'admin'
        
        # Verify navbar is rendered
        mock_dependencies['navbar'].assert_called_once()
        
        # Verify default page (home) is rendered
        mock_dependencies['pages'].home.assert_called_once_with(
            mailclient=mock_dependencies['mail_instance'],
            database=mock_dependencies['db_instance']
        )

    def test_main_page_routing_home(self, mock_streamlit, mock_env_vars, mock_dependencies):
        """Test page routing to home page."""
        # Set up authenticated state and home page selection
        mock_streamlit.session_state['session_key'] = 'valid_session_key'
        mock_dependencies['security'].validate_session.return_value = 'user123'
        mock_dependencies['navbar'].return_value = 0
        
        # Run main
        main()
        
        # Verify home page is rendered
        mock_dependencies['pages'].home.assert_called_once_with(
            mailclient=mock_dependencies['mail_instance'],
            database=mock_dependencies['db_instance']
        )

    def test_main_page_routing_active_cases(self, mock_streamlit, mock_env_vars, mock_dependencies):
        """Test page routing to active cases page."""
        # Set up authenticated state and active cases page selection
        mock_streamlit.session_state['session_key'] = 'valid_session_key'
        mock_dependencies['security'].validate_session.return_value = 'user123'
        mock_dependencies['navbar'].return_value = 1
        
        # Run main
        main()
        
        # Verify active cases page is rendered
        mock_dependencies['pages'].active_cases.assert_called_once_with(
            database=mock_dependencies['db_instance']
        )

    def test_main_page_routing_settings(self, mock_streamlit, mock_env_vars, mock_dependencies):
        """Test page routing to settings page."""
        # Set up authenticated state and settings page selection
        mock_streamlit.session_state['session_key'] = 'valid_session_key'
        mock_dependencies['security'].validate_session.return_value = 'user123'
        mock_dependencies['navbar'].return_value = 2
        
        # Run main
        main()
        
        # Verify settings page is rendered
        mock_dependencies['pages'].settings.assert_called_once_with(
            database=mock_dependencies['db_instance']
        )

    def test_main_page_routing_about(self, mock_streamlit, mock_env_vars, mock_dependencies):
        """Test page routing to about page."""
        # Set up authenticated state and about page selection
        mock_streamlit.session_state['session_key'] = 'valid_session_key'
        mock_dependencies['security'].validate_session.return_value = 'user123'
        mock_dependencies['navbar'].return_value = 3
        
        # Run main
        main()
        
        # Verify about page is rendered
        mock_dependencies['pages'].about.assert_called_once()

    def test_main_page_routing_table_detection(self, mock_streamlit, mock_env_vars, mock_dependencies):
        """Test page routing to table detection page."""
        # Set up authenticated state and table detection page selection
        mock_streamlit.session_state['session_key'] = 'valid_session_key'
        mock_dependencies['security'].validate_session.return_value = 'user123'
        mock_dependencies['navbar'].return_value = 4
        
        # Run main
        main()
        
        # Verify table detection page is rendered
        mock_dependencies['pages'].table_detection.assert_called_once()

    def test_main_page_routing_invalid(self, mock_streamlit, mock_env_vars, mock_dependencies):
        """Test page routing with invalid page number."""
        # Set up authenticated state and invalid page selection
        mock_streamlit.session_state['session_key'] = 'valid_session_key'
        mock_dependencies['security'].validate_session.return_value = 'user123'
        mock_dependencies['navbar'].return_value = 99  # Invalid page number
        
        with patch('main.log') as mock_log:
            # Run main
            main()
            
            # Verify warning is logged
            mock_log.warning.assert_called_with('Invalid page selected: 99, defaulting to home page.')
        
        # Verify home page is rendered as fallback
        mock_dependencies['pages'].home.assert_called_once()
        
        # Verify page is reset to 0
        assert mock_streamlit.session_state['page'] == 0

    def test_main_rerun_counter(self, mock_streamlit, mock_env_vars, mock_dependencies):
        """Test that rerun counter is incremented."""
        # Set up authenticated state
        mock_streamlit.session_state['session_key'] = 'valid_session_key'
        mock_dependencies['security'].validate_session.return_value = 'user123'
        
        # Initial counter value
        initial_counter = mock_streamlit.session_state['rerun_counter']
        
        # Run main
        main()
        
        # Verify counter is incremented
        assert mock_streamlit.session_state['rerun_counter'] == initial_counter + 1

    def test_main_rerun_counter_logging(self, mock_streamlit, mock_env_vars, mock_dependencies):
        """Test that rerun counter triggers info log every 5 runs."""
        # Set up authenticated state
        mock_streamlit.session_state['session_key'] = 'valid_session_key'
        mock_dependencies['security'].validate_session.return_value = 'user123'
        
        # Set counter to 4 (next run will be 5th)
        mock_streamlit.session_state['rerun_counter'] = 4
        
        with patch('main.log') as mock_log:
            # Run main
            main()
            
            # Verify info log is called for 5th run
            mock_log.info.assert_called_with('script executed 5 times')

    def test_main_invalid_session_key(self, mock_streamlit, mock_env_vars, mock_dependencies):
        """Test main function behavior with invalid session key."""
        # Set up invalid session
        mock_streamlit.session_state['session_key'] = 'invalid_key'
        mock_dependencies['security'].validate_session.return_value = None  # Invalid session
        
        # Run main
        main()
        
        # Verify login page is shown
        mock_dependencies['pages'].login.assert_called_once()
        
        # Verify user_id and user_role are not updated
        assert mock_streamlit.session_state['user_id'] is None
        assert mock_streamlit.session_state['user_role'] is None

    @patch('main.st.cache_resource')
    def test_cache_resource_decorator(self, mock_cache_resource, mock_dependencies):
        """Test that cache_resource decorator is applied to resource functions."""
        # Mock the decorator to return the original function
        mock_cache_resource.side_effect = lambda f: f
        
        # Import should trigger decorator
        import main
        
        # Verify decorator was applied
        assert mock_cache_resource.call_count >= 2  # For _get_database and _get_mailclient
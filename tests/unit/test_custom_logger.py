"""
Unit tests for the custom_logger.py module.

This module contains tests for the custom logging configuration, including
the audit log decorator, logger configuration functions, and audit log
initialization.
"""
import pytest
from unittest.mock import patch, MagicMock, call, mock_open
import logging
import os
import datetime
from io import StringIO

import streamlit as st

# Import the module under test
from custom_logger import (
    add_audit_log_parameter,
    AuditableLogger,
    configure_global_logger,
    get_audit_case_logger,
    configure_custom_logger,
    initialize_audit_log,
    process_pending_log_initializations
)


class TestCustomLogger:
    """Test suite for the custom_logger.py module."""

    @pytest.fixture
    def mock_streamlit_session(self):
        """Mock Streamlit session state."""
        with patch('custom_logger.st') as mock_st:
            mock_st.session_state = {
                'user_id': 'test_user',
                'user_role': 'admin'
            }
            yield mock_st

    @pytest.fixture
    def temp_log_dir(self, tmp_path):
        """Create a temporary directory for log files."""
        log_dir = tmp_path / "logs"
        log_dir.mkdir()
        return str(log_dir)

    def test_add_audit_log_parameter_decorator(self, mock_streamlit_session):
        """Test the add_audit_log_parameter decorator functionality."""
        # Create a mock logger
        mock_logger = MagicMock()
        mock_method = MagicMock(return_value="log_result")
        mock_method.__name__ = "info"
        
        # Apply decorator
        decorated_method = add_audit_log_parameter(mock_method)
        
        # Call the decorated method
        result = decorated_method(mock_logger, "Test message", case_id=123)
        
        # Verify the original method was called with modified message
        expected_msg = "User: test_user, Role: admin - Test message"
        mock_method.assert_called_once_with(mock_logger, expected_msg)
        assert result == "log_result"

    def test_add_audit_log_parameter_without_user(self):
        """Test the decorator when no user is in session."""
        with patch('custom_logger.st') as mock_st:
            mock_st.session_state = {}
            
            mock_logger = MagicMock()
            mock_method = MagicMock()
            mock_method.__name__ = "debug"
            
            decorated_method = add_audit_log_parameter(mock_method)
            decorated_method(mock_logger, "Test message")
            
            # Message should not be modified
            mock_method.assert_called_once_with(mock_logger, "Test message")

    @patch('custom_logger.get_audit_case_logger')
    def test_add_audit_log_parameter_with_case_id(self, mock_get_audit_logger, mock_streamlit_session):
        """Test the decorator with case_id parameter."""
        # Setup mocks
        mock_audit_logger = MagicMock()
        mock_get_audit_logger.return_value = mock_audit_logger
        
        mock_logger = MagicMock()
        mock_method = MagicMock()
        mock_method.__name__ = "error"
        
        # Apply decorator and call
        decorated_method = add_audit_log_parameter(mock_method)
        decorated_method(mock_logger, "Error message", case_id=456)
        
        # Verify audit logger was called
        mock_get_audit_logger.assert_called_once_with(456)
        mock_audit_logger.log.assert_called_once_with(
            logging.ERROR,
            "User: test_user, Role: admin - Error message"
        )

    def test_auditable_logger_methods(self, mock_streamlit_session):
        """Test AuditableLogger class methods."""
        logger = AuditableLogger("test_logger")
        
        # Mock the parent class methods
        with patch.object(logging.Logger, 'debug') as mock_debug, \
             patch.object(logging.Logger, 'info') as mock_info, \
             patch.object(logging.Logger, 'warning') as mock_warning, \
             patch.object(logging.Logger, 'error') as mock_error:
            
            # Test each method
            logger.debug("Debug message")
            logger.info("Info message")
            logger.warning("Warning message")
            logger.error("Error message")
            
            # Verify parent methods were called with modified messages
            mock_debug.assert_called_once()
            mock_info.assert_called_once()
            mock_warning.assert_called_once()
            mock_error.assert_called_once()

    @patch('os.makedirs')
    @patch('logging.FileHandler')
    @patch('logging.StreamHandler')
    def test_configure_global_logger(self, mock_stream_handler, mock_file_handler, mock_makedirs, temp_log_dir):
        """Test global logger configuration."""
        # Create mock handlers
        mock_file_handler_instance = MagicMock()
        mock_stream_handler_instance = MagicMock()
        mock_file_handler.return_value = mock_file_handler_instance
        mock_stream_handler.return_value = mock_stream_handler_instance
        
        # Configure logger
        configure_global_logger(
            console_level=logging.INFO,
            file_level=logging.DEBUG,
            logging_directory=temp_log_dir + "/"
        )
        
        # Verify directory creation
        mock_makedirs.assert_called_once_with(temp_log_dir + "/")
        
        # Verify file handler setup
        mock_file_handler.assert_called_once_with(temp_log_dir + "/application.log")
        mock_file_handler_instance.setLevel.assert_called_once_with(logging.DEBUG)
        
        # Verify console handler setup
        mock_stream_handler.assert_called_once()
        mock_stream_handler_instance.setLevel.assert_called_once_with(logging.INFO)

    @patch('os.path.exists')
    def test_configure_global_logger_existing_directory(self, mock_exists):
        """Test global logger configuration with existing directory."""
        mock_exists.return_value = True
        
        with patch('logging.FileHandler'), \
             patch('logging.StreamHandler'):
            configure_global_logger(
                console_level=logging.WARNING,
                file_level=logging.INFO,
                logging_directory="/existing/path/"
            )
            
            # Verify makedirs was not called
            with patch('os.makedirs') as mock_makedirs:
                mock_makedirs.assert_not_called()

    @patch('os.makedirs')
    @patch('os.path.exists')
    @patch('os.path.dirname')
    @patch('logging.FileHandler')
    def test_get_audit_case_logger_new(self, mock_file_handler, mock_dirname, mock_exists, mock_makedirs):
        """Test creating a new audit case logger."""
        # Setup mocks
        mock_exists.side_effect = [False, True]  # Log file doesn't exist, then directory exists
        mock_dirname.return_value = "/test/path"
        mock_handler = MagicMock()
        mock_file_handler.return_value = mock_handler
        
        with patch.dict(os.environ, {'FILESYSTEM_PATH': '/test/filesystem'}):
            # Get logger
            logger = get_audit_case_logger(123)
            
            # Verify logger setup
            assert logger.name == "audit_case_123"
            assert logger.level == logging.INFO
            assert logger.propagate is False
            
            # Verify file handler was created
            expected_path = "/test/filesystem/documents/123/audit_log.txt"
            mock_file_handler.assert_called_once_with(expected_path)
            
            # Verify initial log entry
            logger.info.assert_called_once_with("Audit log created for case 123")

    @patch('os.path.exists')
    @patch('logging.getLogger')
    def test_get_audit_case_logger_existing(self, mock_get_logger, mock_exists):
        """Test getting an existing audit case logger."""
        # Setup mock logger with handlers
        mock_logger = MagicMock()
        mock_logger.handlers = [MagicMock()]  # Has handlers
        mock_get_logger.return_value = mock_logger
        
        # Get logger
        logger = get_audit_case_logger(456)
        
        # Verify no new handlers were added
        assert len(logger.handlers) == 1
        
        # Verify logger name
        mock_get_logger.assert_called_once_with("audit_case_456")

    @patch('os.path.getsize')
    @patch('os.path.exists')
    def test_get_audit_case_logger_empty_file(self, mock_exists, mock_getsize):
        """Test creating logger for empty audit log file."""
        mock_exists.return_value = True
        mock_getsize.return_value = 0  # Empty file
        
        with patch('logging.FileHandler'), \
             patch('os.makedirs'):
            logger = get_audit_case_logger(789)
            
            # Verify pending initialization was added
            import custom_logger
            assert hasattr(custom_logger, '_pending_log_initializations')
            assert 789 in custom_logger._pending_log_initializations

    def test_configure_custom_logger_no_handlers(self, temp_log_dir):
        """Test configuring a custom logger without existing handlers."""
        logger = logging.getLogger("custom_test_logger")
        log_file = os.path.join(temp_log_dir, "custom.log")
        
        with patch('logging.FileHandler') as mock_file_handler, \
             patch('logging.StreamHandler') as mock_stream_handler:
            
            configure_custom_logger(logger, log_file)
            
            # Verify handlers were added
            mock_file_handler.assert_called_once_with(log_file)
            mock_stream_handler.assert_called_once()
            
            # Verify logger level
            assert logger.level == logging.DEBUG

    def test_configure_custom_logger_with_handlers(self):
        """Test configuring a custom logger that already has handlers."""
        logger = logging.getLogger("existing_logger")
        logger.addHandler(MagicMock())  # Add existing handler
        
        with patch('logging.FileHandler') as mock_file_handler:
            configure_custom_logger(logger, "/path/to/log")
            
            # Verify no new handlers were added
            mock_file_handler.assert_not_called()

    @patch('custom_logger.get_audit_case_logger')
    @patch('os.path.getsize')
    @patch('os.path.exists')
    def test_initialize_audit_log_existing_file(self, mock_exists, mock_getsize, mock_get_logger):
        """Test initializing audit log for existing file with content."""
        mock_exists.return_value = True
        mock_getsize.return_value = 100  # Non-empty file
        
        mock_db = MagicMock()
        initialize_audit_log(123, mock_db)
        
        # Should return early without querying database
        mock_db.query.assert_not_called()

    @patch('custom_logger.get_audit_case_logger')
    @patch('os.path.getsize')
    @patch('os.path.exists')
    def test_initialize_audit_log_new_file(self, mock_exists, mock_getsize, mock_get_logger):
        """Test initializing audit log for new case."""
        mock_exists.return_value = False
        mock_audit_logger = MagicMock()
        mock_get_logger.return_value = mock_audit_logger
        
        # Mock database
        mock_db = MagicMock()
        mock_db.query.side_effect = [
            # Case info query
            [(1, 'email123', 3, '2023-01-01', 'BF123', 'Test Institute')],
            # Document info query
            [('document.pdf', '2023-01-02')],
            # Document match info query
            [('document.pdf', '/path/to/doc')]
        ]
        
        with patch('custom_logger.PDF') as mock_pdf:
            mock_pdf_instance = MagicMock()
            mock_pdf.from_json.return_value = mock_pdf_instance
            comparison_df = MagicMock()
            comparison_df.empty = False
            comparison_df.__len__.return_value = 10
            comparison_df['Match status'].value_counts.return_value.get.return_value = 8
            mock_pdf_instance.get_value_comparison_table.return_value = comparison_df
            
            initialize_audit_log(123, mock_db)
        
        # Verify log entries
        expected_calls = [
            call("Audit case created for Test Institute (BaFin ID: BF123)"),
            call("Email received with document 'document.pdf'"),
            call("Document verification process started"),
            call("Document verification completed with 80.0% match (8/10 fields)")
        ]
        for expected_call in expected_calls:
            assert expected_call in mock_audit_logger.info.call_args_list

    @patch('custom_logger.get_audit_case_logger')
    @patch('os.path.exists')
    def test_initialize_audit_log_all_stages(self, mock_exists, mock_get_logger):
        """Test initializing audit log for case in final stage."""
        mock_exists.side_effect = [False, True]  # Log doesn't exist, certificate exists
        mock_audit_logger = MagicMock()
        mock_get_logger.return_value = mock_audit_logger
        
        # Mock database with stage 5 case
        mock_db = MagicMock()
        mock_db.query.return_value = [(1, None, 5, '2023-01-01', 'BF456', 'Bank ABC')]
        
        with patch('os.path.getmtime') as mock_getmtime:
            mock_getmtime.return_value = 1672531200  # Some timestamp
            
            initialize_audit_log(456, mock_db)
        
        # Verify all stage logs
        log_calls = [call[0][0] for call in mock_audit_logger.info.call_args_list]
        assert any("Audit case created" in call for call in log_calls)
        assert any("Document verification process started" in call for call in log_calls)
        assert any("Certificate generated" in call for call in log_calls)
        assert any("Audit process completed" in call for call in log_calls)
        assert any("Case archived" in call for call in log_calls)

    @patch('custom_logger.get_audit_case_logger')
    @patch('os.path.exists')
    def test_initialize_audit_log_no_case(self, mock_exists, mock_get_logger):
        """Test initializing audit log when case doesn't exist."""
        mock_exists.return_value = False
        
        mock_db = MagicMock()
        mock_db.query.return_value = []  # No case found
        
        initialize_audit_log(999, mock_db)
        
        # Should return early without creating logger entries
        mock_get_logger.return_value.info.assert_not_called()

    @patch('custom_logger.initialize_audit_log')
    def test_process_pending_log_initializations(self, mock_initialize):
        """Test processing pending log initializations."""
        import custom_logger
        custom_logger._pending_log_initializations = [123, 456, 789]
        
        mock_db = MagicMock()
        process_pending_log_initializations(mock_db)
        
        # Verify each case was initialized
        expected_calls = [
            call(123, mock_db),
            call(456, mock_db),
            call(789, mock_db)
        ]
        mock_initialize.assert_has_calls(expected_calls)
        
        # Verify list was cleared
        assert custom_logger._pending_log_initializations == []

    @patch('custom_logger.initialize_audit_log')
    @patch('logging.getLogger')
    def test_process_pending_log_initializations_with_error(self, mock_get_logger, mock_initialize):
        """Test processing pending initializations with errors."""
        import custom_logger
        custom_logger._pending_log_initializations = [111, 222]
        
        # Make first initialization fail
        mock_initialize.side_effect = [Exception("Init failed"), None]
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        process_pending_log_initializations()
        
        # Verify error was logged
        mock_logger.error.assert_called_once()
        assert "Error initializing audit log for case 111" in mock_logger.error.call_args[0][0]
        
        # Verify second initialization still happened
        assert mock_initialize.call_count == 2

    def test_process_pending_log_initializations_no_pending(self):
        """Test processing when no pending initializations exist."""
        import custom_logger
        if hasattr(custom_logger, '_pending_log_initializations'):
            delattr(custom_logger, '_pending_log_initializations')
        
        with patch('custom_logger.initialize_audit_log') as mock_initialize:
            process_pending_log_initializations()
            
            # Should not attempt any initializations
            mock_initialize.assert_not_called()

    @patch('custom_logger.Database')
    @patch('custom_logger.initialize_audit_log')
    def test_process_pending_log_initializations_no_db(self, mock_initialize, mock_db_class):
        """Test processing pending initializations without database parameter."""
        import custom_logger
        custom_logger._pending_log_initializations = [333]
        
        mock_db_instance = MagicMock()
        mock_db_class.get_instance.return_value = mock_db_instance
        
        process_pending_log_initializations()
        
        # Verify database instance was obtained
        mock_db_class.get_instance.assert_called_once()
        
        # Verify initialization was called with db instance
        mock_initialize.assert_called_once_with(333, mock_db_instance)

    def test_logging_format_parameter(self):
        """Test custom logging format in configure_global_logger."""
        custom_format = '%(levelname)s - %(message)s'
        
        with patch('logging.Formatter') as mock_formatter, \
             patch('logging.FileHandler'), \
             patch('logging.StreamHandler'), \
             patch('os.makedirs'):
            
            configure_global_logger(
                console_level=logging.INFO,
                file_level=logging.DEBUG,
                logging_format=custom_format,
                logging_directory="/tmp/"
            )
            
            # Verify custom format was used
            mock_formatter.assert_called_once_with(custom_format)
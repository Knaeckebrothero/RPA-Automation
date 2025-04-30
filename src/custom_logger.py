"""
This is a custom logger configuration snippet that can be used to configure a custom logger for your application.
https://docs.python.org/3/library/logging.html?highlight=logger#module-logging
"""
import os
import logging
import inspect
import streamlit as st
from functools import wraps


# Add a custom audit_log parameter to logging methods
def add_audit_log_parameter(func) -> callable:
    """
    Decorator to add an audit_log parameter to logging methods.

    :param func: The function to decorate.
    :return: The decorated function.
    """
    @wraps(func)
    def wrapper(self, msg, *args, **kwargs):
        """
        Wrapper function to add audit_log parameter to logging methods.

        :param self: The instance of the logger class.
        :param msg: The message to log.
        """
        audit_log = kwargs.pop('audit_log', False)
        case_id = kwargs.pop('case_id', None)

        # Call the original logging function
        result = func(self, msg, *args, **kwargs)

        # If audit_log is True and case_id is provided, log to the audit case log
        if audit_log and case_id is not None:
            # Get audit case logger and log the message
            audit_logger = get_audit_case_logger(case_id)
            # Use the same level as the original call
            level_name = func.__name__.upper()
            level = getattr(logging, level_name)
            audit_logger.log(level, msg, *args)
        elif audit_log and case_id is None:
            # Try to determine case_id from the calling context or warn about missing case_id
            frame = inspect.currentframe().f_back
            while frame:
                if 'case_id' in frame.f_locals:
                    case_id = frame.f_locals['case_id']
                    audit_logger = get_audit_case_logger(case_id)
                    level_name = func.__name__.upper()
                    level = getattr(logging, level_name)
                    audit_logger.log(level, msg, *args)
                    break
                frame = frame.f_back
            else:
                # If case_id couldn't be determined, log a warning
                logging.getLogger().warning(
                    "Audit logging requested but case_id not provided and couldn't be determined from context")

        return result

    return wrapper


# Patch the Logger class to add the audit_log parameter
class AuditableLogger(logging.Logger):
    @add_audit_log_parameter
    def debug(self, msg, *args, **kwargs):
        return super().debug(msg, *args, **kwargs)

    @add_audit_log_parameter
    def info(self, msg, *args, **kwargs):
        return super().info(msg, *args, **kwargs)

    @add_audit_log_parameter
    def warning(self, msg, *args, **kwargs):
        return super().warning(msg, *args, **kwargs)

    @add_audit_log_parameter
    def error(self, msg, *args, **kwargs):
        return super().error(msg, *args, **kwargs)

    @add_audit_log_parameter
    def critical(self, msg, *args, **kwargs):
        return super().critical(msg, *args, **kwargs)


# Register our custom logger class
logging.setLoggerClass(AuditableLogger)


@st.cache_resource
def configure_global_logger(
        console_level: int = 20,
        file_level: int = 20,
        logging_format: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        logging_directory: str = './logs/',
):
    """
    This function configures a custom logger for printing and saving logs in a logfile.

    :param console_level: The logging level for logging in the console.
    :param file_level: The logging level for logging in the logfile.
    :param logging_format: Format used for logging.
    :param logging_directory: Path for the directory where the log files should be saved to.
    """
    # Configure the root logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(logging_format)

    # Set and create the logging directory if it does not exist
    if not os.path.exists(logging_directory):
        os.makedirs(logging_directory)

    # File handler for writing logs to a file
    # TODO: Implement some kind of log file rotation (perhaps daily)
    file_handler = logging.FileHandler(logging_directory + 'application.log')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(file_level)
    logger.addHandler(file_handler)

    # Console (stream) handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(console_level)
    logger.addHandler(console_handler)


def get_audit_case_logger(case_id):
    """
    Get or create a logger dedicated to a specific audit case.
    
    :param case_id: The ID of the audit case.
    :return: A Logger instance for the audit case.
    """
    logger_name = f"audit_case_{case_id}"
    logger = logging.getLogger(logger_name)

    # Check if this logger already has handlers
    if not logger.handlers:
        # Create case log directory if it doesn't exist
        case_log_path = os.path.join(
            os.getenv('FILESYSTEM_PATH', './.filesystem'),
            "documents",
            str(case_id),
            "audit_log.log"
        )

        # Ensure directory exists
        os.makedirs(os.path.dirname(case_log_path), exist_ok=True)

        # Set up case-specific file handler
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler = logging.FileHandler(case_log_path)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # Set level to INFO for audit logs
        logger.setLevel(logging.INFO)

        # Prevent propagation to avoid duplicate logs in the main log file
        logger.propagate = False

    return logger


@st.cache_resource
def configure_custom_logger(logger: logging.Logger, log_file: str):
    """Configure a custom logger with a specific log file."""
    if not logger.hasHandlers():
        logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

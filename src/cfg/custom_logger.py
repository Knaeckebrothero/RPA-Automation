"""
This is a custom logger configuration snippet that can be used to configure a custom logger for your application.
https://docs.python.org/3/library/logging.html?highlight=logger#module-logging
"""
import os
import logging
import streamlit as st


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
    :param logging_directory: Path for the directory where the log files should be saved to..
    """
    # Configure the root logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(logging_format)

    # Set and create the logging directory if it does not exist
    if not os.path.exists(logging_directory):
        os.makedirs(logging_directory)

    # File handler for writing logs to a file
    file_handler = logging.FileHandler(logging_directory + 'application.log')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(file_level)
    logger.addHandler(file_handler)

    # Console (stream) handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(console_level)
    logger.addHandler(console_handler)


@st.cache_resource
def configure_custom_logger(logger: logging.Logger, log_file: str):
    if not logger.hasHandlers():
        logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

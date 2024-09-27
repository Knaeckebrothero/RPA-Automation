"""
This module contains a set of functions that are used to cache resources.

This allows the resources to be fetched only once during a session,
which can help improve the performance of the application.
For more information on caching in Streamlit, see the documentation:
https://docs.streamlit.io/develop/concepts/architecture/caching
"""
import os
import streamlit as st
# Custom imports
from custom_logger import _configure_custom_logger  # Custom logger is only to be used in this module!!!
from src.cls import Mailclient


@st.cache_resource
def get_logger(module_name: str):
    """
    Get a logger instance for the specified module.

    This one is particularly important to prevent the logger from being duplicated
    and therefore causing the log file to be bloated.
    Since the logger isn't a singleton,
    it would be re-initialized on every action due to the way Streamlit works.
    Therefore, the _configure_custom_logger function is only to be used in the module.
    All other modules should use the get_logger function to cache their logger instances.

    :param module_name: The name of the module.
    :return: The logger instance.
    """
    return _configure_custom_logger(
        module_name=module_name,
        console_level=int(os.getenv('LOG_LEVEL_CONSOLE')),
        file_level=int(os.getenv('LOG_LEVEL_FILE')),
        logging_directory=os.getenv('LOG_PATH') if os.getenv('LOG_PATH') else None
    )


@st.cache_resource
def get_mailclient(
        imap_server: str = None,
        imap_port: int = None,
        username: str = None,
        password: str = None,
        inbox: str = None
):
    """
    Get the mail client instance.

    Parameters are optional and will be fetched from the environment variables if not specified.

    :param imap_server: The IMAP server.
    :param imap_port: The IMAP port.
    :param username: The username.
    :param password: The password.
    :param inbox: The inbox.

    :return: The mail client instance.
    """
    return Mailclient.get_instance(
        imap_server=imap_server if imap_server else os.getenv('IMAP_HOST'),
        imap_port=imap_port if imap_port else int(os.getenv('IMAP_PORT')),
        username=username if username else os.getenv('IMAP_USER'),
        password=password if password else os.getenv('IMAP_PASSWORD'),
        logger=get_logger(
            module_name='Mailclient',
            console_level=int(os.getenv('LOG_LEVEL_CONSOLE')),
            file_level=int(os.getenv('LOG_LEVEL_FILE')),
            logging_directory=os.getenv('LOG_PATH') if os.getenv('LOG_PATH') else None
        ),
        inbox=inbox if inbox else os.getenv('INBOX')
    )


@st.cache_data
def get_emails():
    """
    Fetch the emails from the mail client.

    :return: The emails fetched from the mail client.
    """
    return get_mailclient.get_mails()

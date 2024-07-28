"""
This module holds the startup configuration for the application.
"""
import os
import streamlit as st
# Custom imports
from config.custom_logger import configure_custom_logger
from src.email.client import Client
from src.storage.filehandler import Filehandler


@st.cache_resource
def get_logger(module_name: str):
    return configure_custom_logger(
        module_name=module_name,
        console_level=int(os.getenv('LOG_LEVEL_CONSOLE')),
        file_level=int(os.getenv('LOG_LEVEL_FILE')),
        logging_directory=os.getenv('LOG_PATH') if os.getenv('LOG_PATH') else None
    )


@st.cache_resource
def get_mailclient():
    return Client.get_instance(
        imap_server=os.getenv('IMAP_HOST'),
        imap_port=int(os.getenv('IMAP_PORT')),
        username=os.getenv('IMAP_USER'),
        password=os.getenv('IMAP_PASSWORD'),
        inbox=os.getenv('INBOX')
    )


@st.cache_resource
def get_filehandler():
    return Filehandler.get_instance(
        base_path=os.getenv('FILESYSTEM_PATH')
    )

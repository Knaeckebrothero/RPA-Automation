"""
This module holds the startup configuration for the application.
"""
import logging
import os
import streamlit as st
# Custom imports
from config.custom_logger import configure_custom_logger
from src.email.client import Client


def streamlit_session_state():
    """
    This function initializes the session state for the Streamlit application.
    """
    # Initialize the counter in session state if it doesn't exist
    st.session_state['rerun_counter'] = 0

    # Initialize the logger
    st.session_state['logger'] = configure_custom_logger(
        module_name='main',
        console_level=int(os.getenv('LOG_LEVEL')),
        file_level=int(os.getenv('LOG_LEVEL')),
        logging_directory=os.getenv('LOG_PATH') if os.getenv('LOG_PATH') else None
    )

    # Initialize the mail client
    st.session_state['mailbox'] = Client(
        imap_server=os.getenv('IMAP_HOST'),
        imap_port=int(os.getenv('IMAP_PORT')),
        username=os.getenv('IMAP_USER'),
        password=os.getenv('IMAP_PASSWORD'),
        inbox=os.getenv('INBOX')
    )


def streamlit_page():
    """
    This function initializes the webpage for the Streamlit application.
    """
    st.set_page_config(
        layout="wide",
        page_title="Doc Fetcher",
        initial_sidebar_state="collapsed",
        page_icon=":page_with_curl:",
        menu_items={
            'Get Help': 'https://www.extremelycoolapp.com/help',
            'Report a bug': "https://www.extremelycoolapp.com/bug",
            'About': "# This is a header. This is an *extremely* cool app!"
        }
    )

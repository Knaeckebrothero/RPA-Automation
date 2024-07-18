"""
This file holds the main function for the eBonFetcher application.
"""
import os
import streamlit as st
from dotenv import load_dotenv, find_dotenv

# Custom imports
from src.config.custom_logger import configure_custom_logger
from src.email.client import Client
import src.ui.home as ui



# Create a configuration method and move the initialization logic to it
# Also include env variables in the method so they don't get loaded every time the script runs





def main():
    # Load the environment variables
    load_dotenv(find_dotenv())

    # Initialize the logger
    if 'logger' not in st.session_state:
        st.session_state.logger = configure_custom_logger(
            module_name='main',
            console_level=int(os.getenv('LOG_LEVEL')),
            file_level=int(os.getenv('LOG_LEVEL')),
            logging_directory=os.getenv('LOG_PATH') if os.getenv('LOG_PATH') else None
        )
    logger = st.session_state.logger

    # Initialize the counter in session state if it doesn't exist
    if 'rerun_counter' not in st.session_state:
        st.session_state.rerun_counter = 0

    # Initialize the mail client
    if 'mailbox' not in st.session_state:
        st.session_state.mailbox = Client(
            imap_server=os.getenv('IMAP_HOST'),
            imap_port=int(os.getenv('IMAP_PORT')),
            username=os.getenv('IMAP_USER'),
            password=os.getenv('IMAP_PASSWORD'),
            inbox=os.getenv('INBOX')
        )
    mailbox = st.session_state.mailbox

    # Start the UI
    logger.debug('Starting the UI')
    ui.home(logger, mailbox)

    # Log end of script execution to track streamlit reruns
    st.session_state.rerun_counter += 1
    logger.info(f'script executed {st.session_state.rerun_counter} times')


if __name__ == '__main__':
    main()

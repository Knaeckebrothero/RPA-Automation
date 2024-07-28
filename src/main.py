"""
This file holds the main function for the application.

https://docs.streamlit.io/
"""
from dotenv import load_dotenv, find_dotenv
import streamlit as st
# Custom imports
import src.ui.home as ui
import config.startup as startup


@st.cache_data
def fetch_mails(_mailbox):
    return _mailbox.get_mails()


def main():
    st.set_page_config(
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

    with st.spinner(text="Initializing..."):
        # Initialize the session if the counter is not set
        if 'rerun_counter' not in st.session_state:
            st.session_state['rerun_counter'] = 0
            load_dotenv(find_dotenv())

            # TODO: Add a check for the existence of the .env file
            # TODO: Add json configuration file to load the non-sensitive configuration from

        # Initialize the logger, mail client, and file handler
        log = startup.get_logger('main')
        mailbox = startup.get_mailclient()
        filehandler = startup.get_filehandler()

    # Fetch the mails
    mails = fetch_mails(mailbox)
    log.debug('Mails fetched')

    # Start the UI
    log.debug('Starting the UI')
    ui.home(log, mails)
    log.debug('UI started')

    # Log end of script execution to track streamlit reruns
    st.session_state.rerun_counter += 1
    log.debug(f'script executed {st.session_state.rerun_counter} times')
    if st.session_state.rerun_counter % 5 == 0:
        log.info(f'script executed {st.session_state.rerun_counter} times')


if __name__ == '__main__':
    main()

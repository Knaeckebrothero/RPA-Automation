"""
This file holds the main function for the application.

https://docs.streamlit.io/
"""
import os
from dotenv import load_dotenv, find_dotenv
import streamlit as st
# Custom imports
import gui.pages as page
from gui.navbar import navbar
import cfg.cache as cache


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

    with st.spinner(text="Initializing..."):  # TODO: Fix loading spinner not being formatted correctly
        # Initialize the session if the counter is not set
        if 'rerun_counter' not in st.session_state:
            st.session_state['rerun_counter'] = 0
            load_dotenv(find_dotenv())

            # TODO: Add a check for the existence of the .env file
            # TODO: Add json configuration file to load the non-sensitive configuration from

        # Initialize the logger, mail client, and file handler
        log = cache.get_logger('main')
        mailbox = cache.get_mailclient()

    # Fetch the mails
    mails = cache.get_emails()
    log.debug('Mails fetched')

    # Render the navbar and store the selected page in the session
    st.session_state['page'] = navbar(log)

    # Render the page based on the selected option
    match st.session_state.page:
        case 0:
            log.debug('Home page selected')
            page.home(log, mailbox)
        case 1:
            log.debug('Settings page selected')
            page.settings(log)
        case 2:
            log.debug('About page selected')
            # TODO: Implement the about page
            # Display the contents of the log file in a code block (as a placeholder)
            with open(os.path.join(os.getenv('LOG_PATH', ''), 'main_log.log'), 'r') as file:
                st.code(file.read())
        case _:
            log.warning(f'Invalid page selected: {st.session_state.page}, defaulting to home page.')
            page.home(log, mailbox)
            st.session_state['page'] = 0

    # Log end of script execution to track streamlit reruns
    st.session_state.rerun_counter += 1
    log.debug(f'script executed {st.session_state.rerun_counter} times')
    if st.session_state.rerun_counter % 5 == 0:
        log.info(f'script executed {st.session_state.rerun_counter} times')


if __name__ == '__main__':
    main()

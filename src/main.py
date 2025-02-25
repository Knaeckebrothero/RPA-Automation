"""
This file holds the main function for the application.

https://docs.streamlit.io/
"""
from dotenv import load_dotenv, find_dotenv
import streamlit as st
import logging as log
import os

# Custom imports
from cfg.custom_logger import configure_global_logger
import ui.pages as page
from ui.navbar import navbar
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
            # Configure the global logger
            configure_global_logger(
                console_level=int(os.getenv('LOG_LEVEL_CONSOLE')),
                file_level=int(os.getenv('LOG_LEVEL_FILE')),
                logging_directory=os.getenv('LOG_PATH')
            )

            # Fetch the mails and store them in the cache
            cache.get_emails()
            # Initialize the database
            cache.get_database()

            # TODO: Add a check for the existence of the .env file
            # TODO: Add json configuration file to load the non-sensitive configuration from

    # Render the navbar and store the selected page in the session state
    st.session_state['page'] = navbar()

    # Render the page based on the selected option
    match st.session_state.page:
        case 0:
            log.debug('Home page selected')
            page.home()
        case 1:
            log.debug('Active cases page selected')
            page.active_cases()
        case 2:
            log.debug('Settings page selected')
            page.settings()
        case 3:
            log.debug('About page selected')
            page.about()
        case _:
            log.warning(f'Invalid page selected: {st.session_state.page}, defaulting to home page.')
            page.home()
            st.session_state['page'] = 0

    # Log end of script execution to track streamlit reruns
    st.session_state.rerun_counter += 1
    log.debug(f'script executed {st.session_state.rerun_counter} times')
    if st.session_state.rerun_counter % 5 == 0:
        log.info(f'script executed {st.session_state.rerun_counter} times')


if __name__ == '__main__':
    main()

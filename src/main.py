"""
This file holds the main function for the application.

https://docs.streamlit.io/
"""
from dotenv import load_dotenv, find_dotenv
import streamlit as st
import logging as log
import os

# TODO: Fix the issue with the page config not being the first thing in the script
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

# Custom imports
from custom_logger import configure_global_logger
import ui.pages as page
from ui.navbar import navbar
from cls.database import Database
from workflow.audit import get_emails as workflow_get_emails
from workflow.security import init_session_state, validate_session, get_user_role


def main():
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

            # TODO: Questionable value, check if this is necessary

            # Fetch the mails and store them in the cache
            workflow_get_emails()

            # Initialize the database
            Database().get_instance()

            # Initialize session state for authentication
            init_session_state()

            # TODO: Add a check for the existence of the .env file
            # TODO: Add json or yaml configuration file to load the non-sensitive configuration from

    is_authenticated = False
    if st.session_state['session_key']:
        db = Database().get_instance()
        user_id = validate_session(st.session_state['session_key'], db)
        if user_id:
            is_authenticated = True
            # Make sure role is up-to-date
            st.session_state['user_id'] = user_id
            st.session_state['user_role'] = get_user_role(user_id, db)

    # Show login page if not authenticated
    if not is_authenticated:
        page.login()
        st.stop()  # Stop execution here to prevent the rest of the app from loading

    # User is authenticated, proceed with the application

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

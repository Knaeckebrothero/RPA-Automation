"""
This file holds the main function for the application.

https://docs.streamlit.io/
"""
from dotenv import load_dotenv, find_dotenv
import streamlit as st
import logging
import os

from streamlit import session_state

# Custom imports
import cls
from custom_logger import configure_global_logger
from ui.navbar import navbar
import ui.pages as page
from workflow.audit import get_emails as workflow_get_emails
import workflow.security as sec

# Set up logging
log = logging.getLogger(__name__)


@st.cache_resource
def _get_database():
    """
    Helper function to cache the database instance.
    """
    return cls.Database().get_instance()


@st.cache_resource
def _get_mailclient():
    """
    Helper function to cache the mail client instance.
    """
    return cls.Mailclient.get_instance()


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

    # TODO: Replace with company logo
    st.logo(image=".streamlit/example_logo.png", size="large", link=None, icon_image=None)

    # Initialize the session if the counter is not set
    if 'rerun_counter' not in st.session_state:
        st.session_state['rerun_counter'] = 0
        load_dotenv(find_dotenv())  # TODO: Add a check for the existence of the .env file
        # TODO: Add json, yaml or cfg configuration file to load the non-sensitive configuration from

        # Configure the global logger
        configure_global_logger(
            console_level=int(os.getenv('LOG_LEVEL_CONSOLE')),
            file_level=int(os.getenv('LOG_LEVEL_FILE')),
            logging_directory=os.getenv('LOG_PATH')
        )

        if os.getenv('DEV_MODE') == 'true':
            log.warning('DEV_MODE flag set, app is running in development mode.')

        # Initialize session state variables
        st.session_state['session_key'] = None
        st.session_state['user_id'] = None
        st.session_state['user_role'] = None

    # Default to an unauthenticated session
    session_is_authenticated = False

    # Check if the session key is set in the session state
    if st.session_state['session_key']:
        user_id = sec.validate_session(st.session_state['session_key'], _get_database())
        if user_id:
            # If the session key is valid, set the authenticated state to True and update the role
            session_is_authenticated = True
            st.session_state['user_id'] = user_id
            st.session_state['user_role'] = sec.get_user_role(user_id, _get_database())

    # Show login page if not authenticated
    if not session_is_authenticated:
        if page.login(database=_get_database()):
            # Reload the page to apply authentication
            st.rerun()
        else:
            # Stop execution to prevent the rest of the app from loading
            st.stop()

    # Once authenticated, continue with the rest of the app
    #with st.spinner(text="Initializing..."):  # TODO: Fix loading spinner not being formatted correctly
    # Fetch the mails to store them in the cache
    #workflow_get_emails()
    # TODO: Implement a cache or something to avoid having to fetch all the emails (with their attachments
    #  every time the app is loaded). A DB table could be used.

    # Render the navbar and store the selected page in the session state
    st.session_state['page'] = navbar()

    # Render the page based on the selected option
    match st.session_state.page:
        case 0:
            log.debug('Home page selected')
            page.home(mailclient=_get_mailclient(), database=_get_database())
        case 1:
            log.debug('Active cases page selected')
            page.active_cases(database=_get_database())
        case 2:
            log.debug('Settings page selected')
            page.settings(database=_get_database())
        case 3:
            log.debug('About page selected')
            page.about()
        case _:
            log.warning(f'Invalid page selected: {st.session_state.page}, defaulting to home page.')
            page.home(mailclient=_get_mailclient(), database=_get_database())
            st.session_state['page'] = 0

    # Log end of script execution to track streamlit reruns
    st.session_state.rerun_counter += 1
    log.debug(f'script executed {st.session_state.rerun_counter} times')
    if st.session_state.rerun_counter % 5 == 0:
        log.info(f'script executed {st.session_state.rerun_counter} times')


if __name__ == '__main__':
    main()

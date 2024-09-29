"""
This module holds the sidebar ui page for the application.
"""
import os
import streamlit
# Custom imports
from cfg.custom_logger import configure_custom_logger


def _setup_logger():
    log = configure_custom_logger(
        module_name=__name__,
        console_level=int(os.getenv('LOG_LEVEL_CONSOLE', 20)),
        file_level=int(os.getenv('LOG_LEVEL_FILE', 0)),
        logging_directory=os.getenv('LOG_PATH', None))
    log.debug('Logger initialized')
    return log

def navbar() -> int:
    """
    This is the sidebar ui page for the application.

    :return: The selected page number.
    """
    log = _setup_logger()
    log.debug('Initializing navbar')

    # Initialize the page number
    page = 0

    # Set the sidebar to st for easier access and to make sure everything happens
    # inside the sidebar unless explicitly stated
    st = streamlit.sidebar

    # Description
    st.title('Navigation')
    st.write('Please select an option from the list below.')

    # Buttons
    if st.button('Home'):
        log.debug('Fetch Documents button clicked')
        page = 0

    if st.button('Settings'):
        log.debug('Settings button clicked')
        page = 1

    if st.button('About'):
        log.debug('About button clicked')
        page = 2  # TODO: Change to 3 when the about page is implemented

    if st.button('Exit'):
        log.debug('Exit button clicked')

        # Close the browser window and stop the script
        st.markdown('<script>window.close();</script>', unsafe_allow_html=True)
        streamlit.stop()
        # TODO: This does not work as expected. Needs to be fixed

    return page

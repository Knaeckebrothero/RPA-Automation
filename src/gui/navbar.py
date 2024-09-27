"""
This module holds the sidebar ui page for the application.
"""
import logging
import streamlit


def navbar(logger: logging.Logger) -> int:
    """
    This is the sidebar ui page for the application.

    :param logger: The logger object to log messages to.
    :return: The selected page number.
    """
    logger.debug('Rendering sidebar page')
    page = 0

    # Set the sidebar to st for easier access and to make sure everything happens
    # inside the sidebar unless explicitly stated
    st = streamlit.sidebar

    # Description
    st.title('Navigation')
    st.write('Please select an option from the list below.')

    # Buttons
    if st.button('Home'):
        logger.debug('Fetch Documents button clicked')
        page = 0

    if st.button('Settings'):
        logger.debug('Settings button clicked')
        page = 1

    if st.button('About'):
        logger.debug('About button clicked')
        page = 2  # TODO: Change to 3 when the about page is implemented

    if st.button('Exit'):
        logger.debug('Exit button clicked')

        # Close the browser window and stop the script
        st.markdown('<script>window.close();</script>', unsafe_allow_html=True)
        streamlit.stop()
        # TODO: This does not work as expected. Needs to be fixed

    return page

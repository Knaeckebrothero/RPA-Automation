"""
This module holds the sidebar ui page for the application.
"""
import streamlit
import logging as log
# Custom imports


def navbar() -> int:
    """
    This is the sidebar ui page for the application.

    :return: The selected page number.
    """
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

    if st.button('Active Cases'):
        log.debug('Active cases button clicked')
        page = 1

    if st.button('Settings'):
        log.debug('Settings button clicked')
        page = 2

    if st.button('About'):
        log.debug('About button clicked')
        page = 3

    return page

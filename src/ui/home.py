"""
This module holds the main ui page for the application.
"""
import logging
import streamlit as st
import pandas as pd


def home(logger: logging.Logger, mails: pd.DataFrame):
    """
    This is the main ui page for the application.
    It serves as a landing page and provides the user with options to navigate the application.

    :param logger: The logger object to log messages to.
    :param mails: The mails to display on the page.
    """
    logger.debug('Rendering home page')

    # Page title and description
    logger.debug('Rendering page title and description')
    st.title('Document Fetcher')
    st.write('Welcome to the Document Fetcher application!')

    # Sidebar description
    logger.debug('Rendering sidebar')
    st.sidebar.title('Options')
    st.sidebar.write('Please select an option from the list below.')

    # Buttons
    logger.debug('Rendering buttons')
    st.sidebar.button('Fetch Documents')
    st.sidebar.button('Settings')
    st.sidebar.button('About')
    st.sidebar.button('Exit')

    # Display the mails
    st.dataframe(mails)

    # TODO: Store the selected documents in the session state so that we don't have to fetch them every time

    # Display a multiselect box to select documents to process
    st.multiselect('Select documents to process', mails['Subject'])

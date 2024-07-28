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
    st.header('Document Fetcher')
    st.write('Welcome to the Document Fetcher application!')

    # Display the mails
    st.dataframe(mails)

    # Display a multiselect box to select documents to process
    docs_to_process = st.multiselect('Select documents to process', mails['ID'])

    # Process the selected documents
    if st.button('Process selected documents'):
        logger.debug('Processing selected documents...')

        # TODO: Implement the processing logic
        st.write(f'Processing documents: {docs_to_process}')
        st.balloons()


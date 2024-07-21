"""
This module holds the main ui page for the application.
"""
import logging
import streamlit as st
import pandas as pd

# Custom imports
from src.email.client import Client


def home(logger: logging.Logger, mailclient: Client):
    """
    This is the main ui page for the application.
    It serves as a landing page and provides the user with options to navigate the application.

    :param logger: The logger object to log messages to.
    :param mailclient: The mail client object to interact with the mail server.
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

    # Get the mails
    mails = mailclient.list_mails()

    # TEST STUFF REMOVE LATER!!!
    import pandas as pd
    my_dataframe = pd.DataFrame({
        'first column': [1, 2, 3, 4],
        'second column': [10, 20, 30, 40]
    })

    data = {'col1': [1, 2, 3, 4], 'col2': [10, 20, 30, 40]}

    st.dataframe(my_dataframe)
    st.table(data)
    st.json({"foo": "bar", "fu": "ba"})
    st.metric("My metric", 42, 2)

"""
This module holds the settings ui page for the application.
"""
import logging
import streamlit as st


def settings(logger: logging.Logger):
    """
    This is the settings ui page for the application.

    :param logger: The logger object to log messages to.
    """
    logger.debug('Rendering settings page')

    # Page title and description
    st.header('Settings')
    st.write('Configure the application settings below.')

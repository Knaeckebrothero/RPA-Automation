"""
This module contains a set of functions that are used to cache resources.

This allows the resources to be fetched only once during a session,
which can help improve the performance of the application.
For more information on caching in Streamlit, see the documentation:
https://docs.streamlit.io/develop/concepts/architecture/caching
"""
import os
import streamlit as st

# Custom imports
import cls


@st.cache_resource
def get_mailclient(
        imap_server: str = None,
        imap_port: int = None,
        username: str = None,
        password: str = None,
        inbox: str = None
):
    """
    Get the mail client instance.

    Parameters are optional and will be fetched from the environment variables if not specified.

    :param imap_server: The IMAP server.
    :param imap_port: The IMAP port.
    :param username: The username.
    :param password: The password.
    :param inbox: The inbox.

    :return: The mail client instance.
    """
    return cls.Mailclient.get_instance(
        imap_server=imap_server if imap_server else os.getenv('IMAP_HOST'),
        imap_port=imap_port if imap_port else int(os.getenv('IMAP_PORT')),
        username=username if username else os.getenv('IMAP_USER'),
        password=password if password else os.getenv('IMAP_PASSWORD'),
        inbox=inbox if inbox else os.getenv('INBOX')
    )


@st.cache_data
def get_emails():
    """
    Fetch the emails from the mail client.

    :return: The emails fetched from the mail client.
    """
    return get_mailclient().get_mails()


@st.cache_resource
def get_database():
    """
    Get the database instance.

    :return: The database instance.
    """
    return cls.Database().get_instance()

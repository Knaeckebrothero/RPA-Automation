"""
This module holds the main ui page for the application.
"""
import logging
import streamlit as st
import pandas as pd
from custommail import Client
from storage.filehandler import Filehandler
from storage.document import Document


def home(logger: logging.Logger, mails: pd.DataFrame, mailclient: Client, filehandler: Filehandler):
    """
    This is the main ui page for the application.
    It serves as a landing page and provides the user with options to navigate the application.

    :param logger: The logger object to log messages to.
    :param mails: The mails to display on the page.
    :param mailclient: The mailclient object to interact with the mail server.
    :param filehandler: The filehandler object to interact with the file system.
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

        # Iterate over the selected documents
        for mail_id in docs_to_process:
            logger.debug(f'Processing mail with ID {mail_id}')
            attachments = mailclient.get_attachment(mail_id)

            # Check if attachments are present
            if not attachments:
                logger.warning(f'No attachments found for mail with ID {mail_id}')
                st.error(f'No attachments found for mail with ID {mail_id}')
                continue
            elif len(attachments) > 1:
                logger.warning(f'Mail with ID {mail_id} has {len(attachments)} attachments, processing all of them.')
                st.warning(f'Mail with ID {mail_id} has {len(attachments)} attachments, processing all of them.')

                for attachment in attachments:
                    if attachment['filename'].split('.')[-1] == 'pdf':
                        logger.info(f'Processing pdf attachment {attachment["filename"]}')

                        doc = Document(
                            file=attachment['data'],
                            filetype='pdf',
                            name=attachment['filename'].split('.')[0]
                        )
                        logger.info(f'Created document object from mail: {mail_id}')

                        # Extract text from the document
                        doc.extract_table_attributes()
                    else:
                        logger.info(f'Skipping non-pdf attachment {attachment["filename"]}')

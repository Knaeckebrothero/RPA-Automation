"""
This module holds the main ui page for the application.
"""
import logging
import streamlit as st
# Custom imports
from cfg.cache import get_emails
from cfg.cache import get_mailclient
from cls.document import Document  # TODO: Change this to the appropriate class (e.g. Email for emails)


def home(logger: logging.Logger):
    """
    This is the main ui page for the application.
    It serves as a landing page and provides the user with options to navigate the application.

    :param logger: The logger object to log messages to.
    """
    logger.debug('Rendering home page')

    # Page title and description
    st.header('Document Fetcher')
    st.write('Welcome to the Document Fetcher application!')

    # Fetch the emails and client
    emails = get_emails()
    mailclient = get_mailclient()

    # Display the mails
    st.dataframe(emails)

    # Display a multiselect box to select documents to process
    docs_to_process = st.multiselect('Select documents to process',emails['ID'])

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

def settings(logger: logging.Logger):
    """
    This is the settings ui page for the application.

    :param logger: The logger object to log messages to.
    """
    logger.debug('Rendering settings page')

    # Page title and description
    st.header('Settings')
    st.write('Configure the application settings below.')

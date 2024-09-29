"""
This module holds the main ui page for the application.
"""
import os
import streamlit as st
# Custom imports
from cfg.custom_logger import configure_custom_logger
from cfg.cache import get_emails
from cfg.cache import get_mailclient
from cls.document import Document  # TODO: Change this to the appropriate class (e.g. Email for emails)


def _setup_logger():
    log = configure_custom_logger(
        module_name=__name__,
        console_level=int(os.getenv('LOG_LEVEL_CONSOLE', 20)),
        file_level=int(os.getenv('LOG_LEVEL_FILE', 0)),
        logging_directory=os.getenv('LOG_PATH', None))
    log.debug('Logger initialized')
    return log

def home():
    """
    This is the main ui page for the application.
    It serves as a landing page and provides the user with options to navigate the application.
    """
    log = _setup_logger()
    log.debug('Rendering home page')

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
        log.debug('Processing selected documents...')

        # Iterate over the selected documents
        for mail_id in docs_to_process:
            log.debug(f'Processing mail with ID {mail_id}')
            attachments = mailclient.get_attachment(mail_id)

            # Check if attachments are present
            if not attachments:
                log.warning(f'No attachments found for mail with ID {mail_id}')
                st.error(f'No attachments found for mail with ID {mail_id}')
                continue
            elif len(attachments) > 1:
                log.warning(f'Mail with ID {mail_id} has {len(attachments)} attachments, processing all of them.')
                st.warning(f'Mail with ID {mail_id} has {len(attachments)} attachments, processing all of them.')

                for attachment in attachments:
                    if attachment['filename'].split('.')[-1] == 'pdf':
                        log.info(f'Processing pdf attachment {attachment["filename"]}')

                        doc = Document(
                            file=attachment['data'],
                            filetype='pdf',
                            name=attachment['filename'].split('.')[0]
                        )
                        log.info(f'Created document object from mail: {mail_id}')

                        # Extract text from the document
                        doc.extract_table_attributes()
                    else:
                        log.info(f'Skipping non-pdf attachment {attachment["filename"]}')

def settings():
    """
    This is the settings ui page for the application.
    """
    log = _setup_logger()
    log.debug('Rendering settings page')

    # Page title and description
    st.header('Settings')
    st.write('Configure the application settings below.')

def about():
    """
    This is the about ui page for the application.
    """
    # Display the contents of the log file in a code block (as a placeholder)
    with open(os.path.join(os.getenv('LOG_PATH', ''), 'log.log'), 'r') as file:
        st.code(file.read())

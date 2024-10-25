"""
This module holds the main ui page for the application.
"""
import os
import streamlit as st
import logging as log

# Custom imports
import ui.visuals as visuals
import cfg.cache as cache
import processing.data as process


def home():
    """
    This is the main ui page for the application.
    It serves as a landing page and provides the user with options to navigate the application.
    """
    log.debug('Rendering home page')

    # Page title and description
    st.header('Document Fetcher')
    st.write('Welcome to the Document Fetcher application!')

    # Fetch the emails and client
    emails = cache.get_emails()
    mailclient = cache.get_mailclient()

    # Configure layout
    column_left, column_right = st.columns(2)

    # Display a plot on the right
    with column_left:
        # Pie chart showing the submission ratio
        st.pyplot(visuals.pie_submission_ratio())
        # TODO: Fix issue with labels overlapping

    # Display a table on the left
    with column_right:
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
            attachments = mailclient.get_attachments(mail_id)

            # Check if attachments are present
            if not attachments:
                log.warning(f'No attachments found for mail with ID {mail_id}')
                st.error(f'No attachments found for mail with ID {mail_id}')
                continue
            elif len(attachments) > 1:
                log.warning(f'Mail with ID {mail_id} has {len(attachments)} attachments, processing all of them.')
                st.warning(f'Mail with ID {mail_id} has {len(attachments)} attachments, processing all of them.')

                for attachment in attachments:
                    if attachment.get_attributes('content_type') == 'application/pdf':
                        log.info(f'Processing pdf attachment {attachment.get_attributes("filename")}')

                        # Extract text from the document
                        attachment.extract_table_data()

                        # Check if all values match the database
                        print(process.compare_company_values(attachment))
                        #if process.compare_company_values(attachment):
                            #db = cache.get_database()

                            # TODO: Create a status column once the documents are getting processed (and simply update
                            #  it later on)

                            #db.query(
                            #    f"INSERT INTO submissions (document_id, company_id, status) VALUES ({mail_id},
                            #    {attachment.get_attributes('BaFin-ID')}, 'submitted')")

                            #log.info(f"Document with ID {mail_id} successfully processed")
                            # TODO: Let the insert statement be executed by the database class

                    else:
                        log.info(f'Skipping non-pdf attachment {attachment.get_attributes("content_type")}')

def settings():
    """
    This is the settings ui page for the application.
    """
    log.debug('Rendering settings page')

    # Page title and description
    st.header('Settings')
    st.write('Configure the application settings below.')


def about():
    """
    This is the about ui page for the application.
    """
    # Display the contents of the log file in a code block (as a placeholder)
    with open(os.path.join(os.getenv('LOG_PATH', ''), 'application.log'), 'r') as file:
        st.code(file.read())

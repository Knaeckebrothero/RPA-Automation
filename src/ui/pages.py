"""
This module holds the main ui page for the application.
"""
import os
import pandas as pd
import streamlit as st
import logging as log

# Custom imports
import ui.visuals as visuals
import cfg.cache as cache
import processing.data as process


def _process_documents(docs_to_process: pd.DataFrame, mailclient, database):
    log.info(f'Processing: {len(docs_to_process)} selected mails...')

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

                    # TODO: Move this to a separate function
                    # Ensure the filesystem's download folder path exists
                    filesystem = os.getenv('FILESYSTEM_PATH')
                    if not os.path.exists(filesystem + "/downloads/"):
                        os.makedirs(filesystem + "/downloads/")

                    # Save the attachment to the filesystem's downloads folder
                    attachment.save_to_file(
                        filesystem +
                        "/downloads/" +
                        attachment.get_attributes("filename") +
                        '.pdf'
                    )
                    # TODO: Why is it saving as NAME.pdf.pdf?

                    # Extract text from the document
                    attachment.extract_table_data()

                    # Get the company id based on the BaFin-ID
                    company_id = database.query(f"""
                                SELECT id 
                                FROM companies 
                                WHERE bafin_id ={attachment.get_attributes('BaFin-ID')}
                                """)

                    # Check if all values match the database
                    if process.compare_company_values(attachment):
                        # TODO: Create a status column once the documents are getting processed (and simply update
                        #  it later on)

                        database.insert(f"""
                                INSERT INTO status (company_id, email_id, status)
                                VALUES ({company_id[0][0]}, {mail_id}, 'processed')
                                """)

                        log.info(f"Company with BaFin ID {attachment.get_attributes('BaFin-ID')} successfully processed")
                    else:
                        if len(company_id[0][0]) == 0:
                            database.insert(f"""
                                    INSERT INTO status (company_id, email_id, status)
                                    VALUES ({company_id[0][0]}, {mail_id}, 'processing')
                                    """)
                        else:
                            log.info(f"Couldn't detect BaFin-ID for document with mail id: {mail_id}")
                else:
                    log.info(f'Skipping non-pdf attachment {attachment.get_attributes("content_type")}')

        # Finally, rerun the app to update the display
        st.rerun()

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

    # Configure visuals layout
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
    docs_to_process = st.multiselect('Select documents to process', emails['ID'])

    # Process only the selected documents
    if st.button('Process selected documents'):
        _process_documents(docs_to_process, cache.get_mailclient(), cache.get_database())

    # Process all the documents
    if st.button('Process all documents'):
        db = cache.get_database()
        mailclient = cache.get_mailclient()

        # Get all mails that are already in the database
        already_processed_mails = [x[0] for x in db.query('SELECT email_id FROM status')]

        # If no mails are in the database, fetch all mails
        if len(already_processed_mails) > 0:
            _process_documents(mailclient.get_mails(already_processed_mails)['ID'], mailclient, db)
        else:
            _process_documents(emails['ID'], mailclient, db)

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

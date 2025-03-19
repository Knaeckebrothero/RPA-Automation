import os
import streamlit as st
import pandas as pd
import logging as log

# Custom imports
import cfg.cache as cache
from cls.document import Document
from process.data import compare_company_values


def asses_mails(docs_to_process: pd.DataFrame):
    """
    F

    """
    database = cache.get_database()

    log.info(f'Processing: {len(docs_to_process)} selected documents...')

    # Iterate over the selected documents
    for mail_id in docs_to_process:
        log.debug(f'Processing mail with ID {mail_id}')
        attachments = cache.get_mailclient().get_attachments(mail_id)

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

                    # TODO: Continue HERE!!!

                    if attachment.get_attributes('BaFin-ID'):
                        print('BaFin-ID: ' + attachment.get_attributes('BaFin-ID') +
                              "########################################################################")
                    else:
                        print('No BaFin-ID found '
                              ' ######################################################################')

                    # TODO: Move this to a separate function
                    # Ensure the filesystem's download folder path exists
                    filesystem = os.getenv('FILESYSTEM_PATH')
                    if not os.path.exists(filesystem + "/downloads/"):
                        os.makedirs(filesystem + "/downloads/")

                    # Save the attachment to the filesystem's downloads folder
                    attachment.save_to_file(
                        filesystem +
                        "/downloads/" +
                        attachment.get_attributes("filename")
                    )

                    # Initialize the audit case and check the values
                    initialize_audit_case(attachment)

                else:
                    log.info(f'Skipping non-pdf attachment {attachment.get_attributes("content_type")}')

        # Finally, rerun the app to update the display
        st.rerun()

# TODO: Rename to initialize and check or something like that
def initialize_audit_case(document: Document):
    """
    Function to initialize an audit case.

    :param document: The document which should be the basis of this audit case.
    """
    database = cache.get_database()

    # Get the client id
    client_id = database.query(
        f"""
        SELECT id
        FROM client
        WHERE bafin_id ={int(document.get_attributes('BaFin-ID'))} 
        """)
    print(client_id)

    # Get the mail id
    mail_id = document.get_attributes('email_id')

    # Check if all values match the database
    if compare_company_values(document):
        # TODO: Check if a audit_case already exists for that client & year combination!
        database.insert(
            f"""
            INSERT INTO audit_case (client_id, email_id, status)
            VALUES ({client_id[0][0]}, {mail_id}, 2)
            """)
        log.info(f"Company with BaFin ID {document.get_attributes('BaFin-ID')} successfully processed")
    else:
        # TODO: Continue here!!!
        if client_id[0][0] == 0: # if len(client_id[0][0]) == 0:
            database.insert(
                f"""
                INSERT INTO audit_case (client_id, email_id, status)
                VALUES ({client_id[0][0]}, {mail_id}, 1)
                """)
        else:
            log.info(f"Couldn't detect BaFin-ID for document with mail id: {mail_id}")

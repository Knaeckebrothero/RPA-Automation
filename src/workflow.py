import os
import streamlit as st
import pandas as pd
import logging as log

# Custom imports
from cls.document import PDF
from cache import get_database as db
from cache import get_mailclient


def assess_emails(emails: pd.DataFrame):
    """
    Function to assess a set of mails and process them accordingly.

    :param emails: The set of mails to process.
    """
    log.info(f'Processing: {len(emails)} selected documents...')

    # Iterate over the selected documents
    for mail_id in emails:
        log.debug(f'Processing mail with ID {mail_id}')
        attachments = get_mailclient().get_attachments(mail_id)

        # Check if attachments are present
        if not attachments:
            log.warning(f'No attachments found for mail with ID {mail_id}')
            st.error(f'No attachments found for mail with ID {mail_id}')
            continue
        elif len(attachments) >= 1:
            log.warning(f'Processing mail with ID {mail_id}')
            st.warning(f'Processing mail with ID {mail_id}')

            for attachment in attachments:
                if attachment.get_attributes('content_type') == 'application/pdf':
                    log.info(f'Processing pdf attachment {attachment.get_attributes("filename")}')

                    # Extract text from the document
                    attachment.extract_table_data()
                    # TODO: Perhaps the 'client_id' attribute should already be set in the 'extract_table_data' method
                    # Check if there are any active cases for this client
                    client_id = attachment.verify_bafin_id()
                    if client_id:
                        email_id = attachment.get_attributes("email_id")
                        log.info(f'Document {email_id} belongs to client {client_id}')

                        # Check if the document is already in the database
                        status = attachment.get_audit_status()

                        # Check the status of the document
                        match status:
                            case 1:  # Documents received
                                log.info(f'Document found in mail with email_id: {email_id} for'
                                         f' client_id: {client_id}.')
                                # Update the audit case
                                update_audit_case_one(attachment)
                            case 2:  # Data verified
                                log.info(f'Document with email_id: {email_id} and'
                                         f' client_id: {client_id} is already in the database.')
                                # Update the audit case
                                update_audit_case_two(attachment)

                                # TODO: CONTINUE HERE !!!

                            case 3:  # Certificate issued
                                pass
                            case 4: # Process completed
                                pass
                            case _:  # Default case
                                log.info(f'Adding document with email_id: {attachment.get_attributes("email_id")} and'
                                         f' client_id: {client_id} to the database.')

                                # Insert the document into the database
                                db.insert(f"""
                                    INSERT INTO audit_case (email_id, client_id, status)
                                    VALUES ({attachment.get_attributes("email_id")}, {client_id}, 1)
                                """)
                                log.info(f'Added document with email_id: {attachment.get_attributes("email_id")} and'
                                         f' client_id: {client_id} to the database.')






                    # Save the attachment to the filesystem's downloads folder
                    attachment.save_to_file(
                        os.path.join(
                            os.getenv('FILESYSTEM_PATH'),
                            "/downloads/",
                            attachment.get_attributes("filename")
                        )
                    )

                    # Initialize the audit case and check the values
                    attachment.validate_and_initialize_audit_case()
                else:
                    log.info(f'Skipping non-pdf attachment {attachment.get_attributes("content_type")}')

        # Finally, rerun the app to update the display
        st.rerun()


def update_audit_case_one(document: PDF):
    """
    Function to update an audit case which has not yet received a document.

    :param document: The document to update the audit case for.
    """


def update_audit_case_two(document: PDF):
    """
    Function to update an audit case which has already received a document.

    :param document: The document to update the audit case for.
    """
    # TODO: Move attributes like 'client_id' and 'email_id' to the 'document' object!
    client_id = document.get_attributes("client_id")
    email_id = document.get_attributes("email_id")

    # Check if the email_id is the same as the one in the database
    email_id_db = db.query(f"""
                            SELECT email_id
                            FROM audit_case
                            WHERE client_id = {client_id}
                            """)
    if email_id != email_id_db[0][0]:
        log.info(f'Email id for case with client id: {client_id} is different from the one in the database.')

        # Check if the new document matches the values in the database
        if document.compare_values():
            # TODO: We should use the audit_case id instead of the client_id to update the status
            # Update the status of the audit case to 2
            db.insert(
                f"""
                UPDATE audit_case
                SET email_id = {email_id}, status = 2
                WHERE client_id = {client_id}
                """)
            log.info(f"Client with BaFin ID {document.get_attributes('BaFin-ID')} successfully "
                     f" validated")
        else:
            log.info(f'Document with email_id: {email_id} does also not match the values in the database.')
            # Update only the email_id in the database
            db.insert(
                f"""
                UPDATE audit_case
                SET email_id = {email_id}
                WHERE client_id = {client_id}
                """)
    else:
        log.info(f'Email id for case with client id: {client_id} is the same as the one in the database.')


def update_audit_case_three(document: PDF):
    pass # TODO: Implement this function


def update_audit_case_four(document: PDF):
    pass # TODO: Implement this function

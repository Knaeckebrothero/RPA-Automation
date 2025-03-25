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
                keep_attachment = False
                if attachment.get_attributes('content_type') == 'application/pdf':
                    log.info(f'Processing pdf attachment {attachment.get_attributes("filename")}')

                    # Extract text from the document
                    attachment.extract_table_data()

                    # Check if the document contains a BaFin ID
                    client_id = attachment.verify_bafin_id()
                    # TODO: Perhaps the 'client_id' attribute should already be set in the 'extract_table_data' method

                    # Check if the document contains a valid BaFin ID
                    if client_id:
                        email_id = attachment.get_attributes("email_id")
                        log.info(f'Document {email_id} belongs to client {client_id}')

                        # Get the status of the audit case
                        status = attachment.get_audit_status()
                        # TODO: Add a check if a audit_case already exists for that client & year combination!?

                        # Check the status of the audit case
                        match status:
                            case 1:  # Waiting for documents
                                log.info(f'Document found in mail with email_id: {email_id} for'
                                         f' client_id: {client_id}.')
                                update_audit_case(attachment)
                                keep_attachment = True

                            case 2:  # Data verification
                                log.info(f'Document with email_id: {email_id} and'
                                         f' client_id: {client_id} is already in the database.')
                                update_audit_case(attachment)
                                keep_attachment = True
                            case 3:  # Issuing certificate
                                log.warning(f"Client with id: {client_id} has already passed the value check ("
                                         f"is currently in phase 3), but submitted a new document with email_id:"
                                         f"  {email_id}.")
                                # keep_attachment = False no need since it's redundant
                            case 4: # Completing process
                                log.warning(f"Client with id: {client_id} has already been certified"
                                         f" (is currently in phase 4), but submitted a new document with email_id: {email_id}.")
                                # keep_attachment = False no need since it's redundant
                            case _:  # Default case
                                log.warning(f'No case found for client_id: {client_id}, adding case for document '
                                            f'with email_id: {email_id}.')

                                # Initialize and update the audit case
                                attachment.initialize_audit_case()
                                update_audit_case(attachment)
                                keep_attachment = True

                        # Save the attachment to the filesystem's downloads folder if it should be kept
                        if keep_attachment:
                            attachment.save_to_file(
                                os.path.join(
                                    os.getenv('FILESYSTEM_PATH'),
                                    "/downloads/",
                                    attachment.get_attributes("filename")
                                )
                            )
                            log.info(f'Saved attachment {attachment.get_attributes("filename")} to filesystem.')
                    else:
                        log.warning(f'No BaFin ID found in document {attachment.get_attributes("filename")}, '
                                    f'email_id: {attachment.get_attributes("email_id")}')
                else:
                    log.info(f'Skipping non-pdf attachment {attachment.get_attributes("content_type")}')

    # Finally, rerun the app to update the display
    # st.rerun()
    # TODO: Could this be an issue? Perhaps this causes the app to only process one mail instead and should be
    #  replaced with a spinner or something similar!


def validate_audit_case(document: PDF):
    """
    Function to initialize an audit case for a document.
    Unlike initialize_audit_case() this function also attempts to validate the client's values against the database,
    if a valid bafin id is found in the document.

    :param document: The document to initialize the audit case for.
    """
    bafin_id = document.get_attributes("BaFin-ID")
    email_id = document.get_attributes("email_id")
    client_id = document.get_attributes("client_id")

    if document.compare_values():
        # Update the status of the audit case to 3
        db.insert(
            f"""
            UPDATE audit_case
            SET status = 3
            WHERE client_id = {client_id} AND email_id = {email_id}
            """)
        log.info(f"Client with BaFin ID {bafin_id} submitted a valid document with email_id: {email_id}")
    else:
        db.insert(
            f"""
            UPDATE audit_case
            SET status = 2
            WHERE client_id = {client_id}
            """)
        log.warning(f"Document with email_id: {email_id}, client_id: {client_id} is not valid!")
        # TODO: Add display logic to show what values are not matching! (Also the page where the auditor can alter
        #  the values can be added/referenced here!)


def update_audit_case(document: PDF):
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

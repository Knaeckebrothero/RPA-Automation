import os
import streamlit as st
import pandas as pd
import logging

# Custom imports
from cls.document import PDF
from cls.database import Database
from cls.mailclient import Mailclient


# Set up logging
log  = logging.getLogger(__name__)

@st.cache_data
def get_emails():
    """
    Fetch the emails from the mail client.

    :return: The emails fetched from the mail client.
    """
    return Mailclient.get_instance().get_mails()


def assess_emails(emails: pd.DataFrame):
    """
    Function to assess a set of mails and process them accordingly.

    :param emails: The set of mails to process.
    """
    log.info(f'Processing: {len(emails)} selected documents...')
    mailclient = Mailclient.get_instance()

    # Iterate over the selected documents
    for email_list_email_id in emails:
        log.debug(f'Processing mail with ID {email_list_email_id}')
        attachments = mailclient.get_attachments(email_list_email_id)

        # Check if attachments are present
        if not attachments:
            log.warning(f'No attachments found for mail with ID {email_list_email_id}')
            # st.error(f'No attachments found for mail with ID {email_id}')
            continue
        elif len(attachments) >= 1:
            log.warning(f'Processing mail with ID {email_list_email_id}')
            # TODO: Remove the warning message in favor of a progress bar or spinner (anything that doesn't bloat the UI)
            st.warning(f'Processing mail with ID {email_list_email_id}')

            for attachment in attachments:
                keep_attachment = False
                if attachment.get_attributes('content_type') == 'application/pdf':
                    log.info(f'Processing pdf attachment {attachment.get_attributes("filename")}')

                    # Extract text from the document (this also sets various attributes if detected)
                    attachment.extract_table_data()

                    # Check if the document contains a valid BaFin ID by checking if the client_id has been set
                    # during the extraction process (this is done by the extract_table_data() method)
                    if attachment.client_id:
                        log.info(f'Document {attachment.email_id} belongs to client {attachment.client_id}')

                        # Get the stage of the audit case
                        stage = attachment.get_audit_stage()
                        # TODO: Add a check if a audit_case already exists for that client & year combination!?

                        # Check the stage of the audit case
                        match stage:
                            case 1:  # Waiting for documents
                                log.info(f'Document found in mail with email_id: {email_list_email_id} for'
                                         f' client_id: {attachment.client_id}.')

                                # Start the validation process
                                process_audit_case(attachment)
                                keep_attachment = True
                            case 2:  # Data verification
                                log.info(f'Document with email_id: {email_list_email_id} and'
                                         f' client_id: {attachment.client_id} is already in the database.')

                                # TODO: Add a check if the document already has a mail id attached to it (so we
                                #  don't process the same document every time the mail is fetched)

                                # Start the validation process
                                process_audit_case(attachment)
                                keep_attachment = True
                            case 3:  # Issuing certificate
                                log.warning(f"Client with id: {attachment.client_id} has already passed the value check ("
                                         f"is currently in phase 3), but submitted a new document with email_id:"
                                         f" {email_list_email_id}.")
                                # keep_attachment = False
                            case 4: # Completing process
                                log.warning(f"Client with id: {attachment.client_id} has already been certified"
                                         f" (is currently in phase 4), but submitted a new document with email_id: {email_list_email_id}.")
                                # keep_attachment = False # No need since it's redundant
                            case _:  # Default case
                                log.info(f'No case found for client_id: {attachment.client_id}, adding case for'
                                         f' document with email_id: {email_list_email_id}.')

                                # Initialize the audit case
                                attachment.initialize_audit_case(stage=2)

                                # Start the validation process
                                process_audit_case(attachment)
                                keep_attachment = True

                        # TODO: Add a proper method to save the attachment to the filesystem (aka. implement folder
                        #  paths and stuff)
                        # Save the attachment to the filesystem's downloads folder if it should be kept
                        if keep_attachment:
                            attachment.save_to_file(os.path.join(
                                os.getenv('FILESYSTEM_PATH'),
                                "downloads",
                                str(email_list_email_id) + "_" + attachment.get_attributes("filename")
                            ))
                            log.info(f'Saved attachment {attachment.get_attributes("filename")} to filesystem.')
                    else:
                        log.warning(f'No BaFin ID found in document {attachment.get_attributes("filename")}, '
                                    f'email_id: {attachment.email_id}')
                        # TODO: Add a db table or something to store the documents that didn't have a BaFin ID
                else:
                    log.info(f'Skipping non-pdf attachment {attachment.get_attributes("content_type")}')
                    # TODO: Add a db table or something to store the mail ids / attachments that were skipped


def process_audit_case(document: PDF):
    """
    Function to initialize and validate a new audit case for a document.

    :param document: The document to initialize the audit case for.
    """
    db = Database().get_instance()

    if document.compare_values():
        # If the values match, set the stage of the audit case to 3
        db.insert(
            f"""
            UPDATE audit_case
            SET stage = 3
            WHERE client_id = ? AND email_id = ?
            """, (document.client_id, document.email_id))
        log.info(f"Client with BaFin ID {document.bafin_id} submitted a VALID document with email_id:"
                 f" {document.email_id}")
    else:
        # If the values do not match, set the stage of the audit case to 2
        db.insert(
            f"""
            UPDATE audit_case
            SET stage = 2
            WHERE client_id = ?
            """, (document.client_id,))
        log.info(f"Client with BaFin ID {document.bafin_id} submitted a INVALID document with email_id:"
                 f" {document.email_id}")
        # TODO: Add display logic to show what values are not matching! (Also the page where the auditor can alter
        #  the values can be added/referenced there!)


def update_audit_case(document: PDF):  # TODO: Remove this method since the update_audit_case() method already covers this functionality
    """
    Function to update an audit case which has already received a document.

    :param document: The document to update the audit case for.
    """
    db = Database().get_instance()

    # Check if the email_id is the same as the one in the database
    email_id_db = db.query("SELECT email_id FROM audit_case WHERE client_id = ?", (document.client_id,))[0][0]
    if document.email_id != email_id_db:
        log.info(f'Email id: {document.email_id} for case with client id: {document.client_id} is different from '
                 f' email id: {email_id_db} already in the one in the database.')

        # Check if the new document matches the values in the database
        #if document.compare_values():
        #else:
    else:
        log.info(f'Skipping document since email id: {document.email_id} for case with client id:'
                 f' {document.client_id} is the same as the one in the database.')

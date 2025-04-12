import streamlit as st
import pandas as pd
import logging

# Custom imports
from cls.document import PDF
from cls.database import Database
from cls.mailclient import Mailclient
from processing.ocr import create_ocr_reader


# Set up logging
log = logging.getLogger(__name__)


@st.cache_data
def get_emails(excluded_ids: list[int] = None):
    """
    Fetch the emails from the mail client.

    :return: The emails fetched from the mail client.
    """
    if excluded_ids:
        return Mailclient.get_instance().get_mails(excluded_ids)
    else:
        return Mailclient.get_instance().get_mails()


def check_for_documents():
    """
    Function to check if there are any documents already stored on the filesystem.
    """
    pass
    # TODO: Implement this function to check if there are any documents already stored on the filesystem.


def assess_emails(emails: pd.DataFrame):
    """
    Function to assess a set of mails and process them accordingly.

    :param emails: The set of mails to process.
    """
    log.info(f'Processing: {len(emails)} selected documents...')
    mailclient = Mailclient.get_instance()
    ocr_reader = create_ocr_reader(language='de')

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
            # st.warning(f'Processing mail with ID {email_list_email_id}')

            for attachment in attachments:
                attachment_case_id = None
                if attachment.get_attributes('content_type') == 'application/pdf':
                    log.info(f'Processing pdf attachment {attachment.get_attributes("filename")}')

                    # Extract text from the document (this also sets various attributes if detected)
                    attachment.extract_table_data(ocr_reader=ocr_reader)

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

                            case 2:  # Data verification
                                log.info(f'Document with email_id: {email_list_email_id} and'
                                         f' client_id: {attachment.client_id} is already in the database.')

                                # TODO: Add a check if the document already has a mail id attached to it (so we
                                #  don't process the same document every time the mail is fetched)

                                # Start the validation process
                                process_audit_case(attachment)

                            case 3:  # Issuing certificate
                                log.warning(
                                    f"Client with id: {attachment.client_id} has already passed the value check ("
                                    f"is currently in phase 3), but submitted a new document with email_id:"
                                    f" {email_list_email_id}.")

                            case 4:  # Completing process
                                log.warning(f"Client with id: {attachment.client_id} has already been certified"
                                            f" (is currently in phase 4), but submitted a new document with email_id: {email_list_email_id}.")

                            case _:  # Default case
                                log.info(f'No case found for client_id: {attachment.client_id}, adding case for'
                                         f' document with email_id: {email_list_email_id}.')

                                # Initialize the audit case
                                attachment.initialize_audit_case(stage=2)
                                # Start the validation process
                                process_audit_case(attachment)
                                # Get the audit case ID if it exists
                                attachment_case_id = attachment.get_audit_case_id()

                        # Store the document if we have an audit case ID
                        if attachment_case_id:
                            if attachment.store_document(attachment_case_id):
                                log.info(f'Document {attachment.get_attributes("filename")} stored successfully for audit case {attachment_case_id}')
                            else:
                                log.error(f'Failed to store document {attachment.get_attributes("filename")} for audit case {attachment_case_id}')
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


# TODO: Remove this method since the update_audit_case() method already covers this functionality
def update_audit_case(document: PDF):
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


def fetch_new_emails(database: Database = None) -> pd.DataFrame:
    """
    Function to fetch new emails from the mail client.

    :param database: The database instance to use (optional).
    :return: The new emails fetched from the mail client.
    """
    if database:
        db = database
    else:
        db = Database.get_instance()

    # TODO: Make sure that a email is not marked as processed unless the process finished successfully 
    #  (e.g. if the app crashes but the mail has already been marked "processed",
    #   then we might run into an issue with emails slipping through without processing!)

    # Check what emails have already been processed
    processed_mails = db.query("SELECT DISTINCT email_id FROM document")

    # Fetch the emails from the mail client
    if not processed_mails:
        log.debug('No mails found in the database, fetching all mails.')
        new_mails = get_emails()
    else:
        new_mails = get_emails(processed_mails)
        log.debug(f'Found a total of {len(processed_mails)} mails already in the database.')

    return new_mails

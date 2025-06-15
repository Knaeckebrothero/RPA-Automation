"""
This module contains the workflow for processing audit cases.
"""
import streamlit as st
import pandas as pd
import logging
import os
import hashlib

# Custom imports
from cls.document import PDF
from cls.database import Database
from cls.mailclient import Mailclient
from processing.ocr import create_ocr_reader
from processing import files


# Set up logging
log = logging.getLogger(__name__)


@st.cache_data
def get_emails(excluded_ids: list[int] = None):
    """
    Fetches emails using the Mailclient instance, optionally excluding specified IDs.

    This function retrieves emails from the Mailclient instance. If a list of email
    IDs to exclude is provided, these emails will be omitted from the result.
    The function leverages Streamlit's caching mechanism to cache the results for
    better performance during repetitive calls.

    :param excluded_ids: A list of email IDs to be excluded from the results. If
        not provided, no emails will be excluded.
    :type excluded_ids: list[int] or None
    :return: A list of emails retrieved from the Mailclient instance.
    :rtype: list
    """
    if excluded_ids:
        return Mailclient.get_instance().get_mails(excluded_ids)
    else:
        return Mailclient.get_instance().get_mails()


def assess_emails(emails: pd.DataFrame):
    """
    Assesses emails and processes their attachments according to specific criteria.
    The function iterates through provided emails, extracts attachments, identifies
    their type, and processes them based on their content and attributes. It interacts
    with various components such as mail clients, OCR readers, and databases to extract
    relevant data, validate attachments, and manage client audit cases. This function
    also takes actions such as sending confirmation emails and initializing audit stages,
    depending on the state of the processed attachments.

    :param emails: A dataframe containing a list of emails to process.
    :type emails: pd.DataFrame
    """
    log.info(f'Processing: {len(emails)} selected documents...')
    mailclient = Mailclient.get_instance()
    ocr_reader = create_ocr_reader(language='de')
    db = Database.get_instance()

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

                                # Send confirmation email to client
                                email_sent = send_document_confirmation_email(attachment, db)
                                if not email_sent:
                                    log.warning("Failed to send confirmation email, but continuing with document processing")

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

                                # Send confirmation email to client
                                email_sent = send_document_confirmation_email(attachment, db)
                                if not email_sent:
                                    log.warning("Failed to send confirmation email, but continuing with document processing")

                                # Start the validation process
                                process_audit_case(attachment)

                    else:
                        log.warning(f'No BaFin ID found in document {attachment.get_attributes("filename")}, '
                                    f'email_id: {attachment.email_id}')
                        # TODO: Add a db table or something to store the documents that didn't have a BaFin ID
                else:
                    log.info(f'Skipping non-pdf attachment {attachment.get_attributes("content_type")}')
                    # TODO: Add a db table or something to store the mail ids / attachments that were skipped


def process_audit_case(document: PDF):
    """
    Processes an audit case based on the provided document's validity and completeness. This function interacts
    with a database to update the state of the audit case depending on the results of the document verification.
    Additionally, it logs important information to the audit and application logs, handles document storage, and
    optionally triggers certificate generation. The document comparison process also computes match percentages
    for detailed auditing insights.

    :param document: The PDF document used for the audit case processing. It is expected to provide methods
        for retrieving audit case identifiers, comparing values, checking completeness, and handling the storage
        of the document. It is also used to generate value comparison tables for verification purposes.
    :type document: PDF
    """
    db = Database().get_instance()
    case_id = document.get_audit_case_id()

    if document.compare_values():
        # Check if the document has a date and is signed
        document.check_document_completeness()

        # If the values match, set the stage of the audit case to 3
        db.insert(
            f"""
            UPDATE audit_case
            SET stage = 3
            WHERE client_id = ? AND email_id = ?
            """, (document.client_id, document.email_id))

        # Log to application log and audit log
        log.info(
            f"Client with BaFin ID {document.bafin_id} submitted a VALID document with email_id: {document.email_id}",
            audit_log=True, case_id=case_id)

        # Save the document to the filesystem
        document.store_document(case_id)

        # Get match percentage for audit log
        comparison_df = document.get_value_comparison_table()
        if not comparison_df.empty:
            matches = comparison_df['Match status'].value_counts().get('✅', 0)
            total = len(comparison_df)
            match_percentage = (matches / total) * 100 if total > 0 else 0
            log.info(f"Document verification completed with {match_percentage:.1f}% match ({matches}/{total} fields)",
                     audit_log=True, case_id=case_id)

        # TODO: Do we want to do the following parts fully automatic?
        # Proceed to generate the certificate
        if generate_certificate(case_id, db):

            # TODO: Add a indication that the certificate was generated successfully
            # Update the audit case stage if the certificate was generated successfully
            #db.insert(
            #    f"""
            #    UPDATE audit_case
            #    SET stage = 4
            #    WHERE client_id = ? AND email_id = ?
            #    """, (document.client_id, document.email_id))

            # Log to application log and audit log
            log.info(
                f"Certificate generated for client with BaFin ID {document.bafin_id} and email_id: {document.email_id}",
                audit_log=True, case_id=case_id)
        else:
            # Log to application log and audit log
            log.error(f"Failed to generate certificate for client with BaFin ID {document.bafin_id}",
                      audit_log=True, case_id=case_id)
    else:
        # If the values do not match, set the stage of the audit case to 2
        db.insert(
            f"""
            UPDATE audit_case
            SET stage = 2
            WHERE client_id = ?
            """, (document.client_id,))

        # Log to application log and audit log
        log.info(
            f"Client with BaFin ID {document.bafin_id} submitted an INVALID document with email_id: {document.email_id}",
            audit_log=True, case_id=case_id)

        # Save the document to the filesystem
        document.store_document(case_id)

        # Get match percentage for audit log
        comparison_df = document.get_value_comparison_table()
        if not comparison_df.empty:
            matches = comparison_df['Match status'].value_counts().get('✅', 0)
            total = len(comparison_df)
            match_percentage = (matches / total) * 100 if total > 0 else 0
            log.info(f"Document verification failed with only {match_percentage:.1f}% match ({matches}/{total} fields)",
                     audit_log=True, case_id=case_id)

    # Process any pending log initializations
    from custom_logger import process_pending_log_initializations
    process_pending_log_initializations(db)


def fetch_new_emails(database: Database = Database.get_instance()) -> pd.DataFrame:
    """
    Fetches new emails from the mail client, excluding those that have already been marked
    as processed in the database. This function ensures that only unprocessed emails are retrieved.

    :param database: An instance of the Database class used to query processed emails
        and store retrieved emails. Defaults to the singleton instance of the Database.
    :type database: Database
    :return: A DataFrame containing the new, unprocessed emails fetched from the mail client.
    :rtype: pd.DataFrame
    """
    # TODO: Make sure that a email is not marked as processed unless the process finished successfully
    #  (e.g. if the app crashes but the mail has already been marked "processed",
    #   then we might run into an issue with emails slipping through without processing!)

    # Check what emails have already been processed
    processed_mails = database.query("SELECT DISTINCT email_id FROM document")

    # Fetch the emails from the mail client
    if not processed_mails:
        log.debug('No mails found in the database, fetching all mails.')
        new_mails = get_emails()
    else:
        new_mails = get_emails(processed_mails)
        log.debug(f'Found a total of {len(processed_mails)} mails already in the database.')

    return new_mails


def generate_certificate(audit_case_id: int, database: Database = Database.get_instance()) -> bool:
    """
    Generates a certificate document and combines it with additional documents to create a
    final PDF for a given audit case. This function fetches relevant information from the
    database, creates a certificate based on a template, extracts necessary pages from other
    documents, and merges them into a single combined PDF. The process includes fetching
    configuration details, handling file operations, and recording updates in the audit database.

    :param audit_case_id: ID of the audit case for which the certificate is to be generated
    :type audit_case_id: int
    :param database: Database instance to interact with the audit case data. Defaults to
        the singleton instance of the Database class
    :type database: Database
    :return: True if the certificate generation process completes successfully, otherwise False
    :rtype: bool
    """
    try:
        # Import the config handler
        from cls.config import ConfigHandler

        # Get config instance
        config = ConfigHandler.get_instance()

        # Step 1: Get client and audit case information
        client_info = get_client_info(audit_case_id, database)
        if not client_info:
            log.error(f"Failed to get client information for audit case {audit_case_id}")
            return False

        # Get document information
        document_info = get_document_info(audit_case_id, database)
        if not document_info:
            log.error(f"No document found for audit case {audit_case_id}")
            return False

        document_path = document_info['document_path']

        # Step 2: Create certificate from template
        certificate_docx_path = files.create_certificate_from_template(client_info, audit_case_id)
        if not certificate_docx_path:
            log.error(f"Failed to create certificate for audit case {audit_case_id}")
            return False

        # Step 3: Convert certificate to PDF
        certificate_pdf_path = files.convert_docx_to_pdf(certificate_docx_path)
        if not certificate_pdf_path:
            log.error(f"Failed to convert certificate to PDF for audit case {audit_case_id}")
            return False

        # Step 4: Extract first page from audit document
        first_page_path = files.extract_first_page(document_path, audit_case_id)
        if not first_page_path:
            log.error(f"Failed to extract first page from document for audit case {audit_case_id}")
            return False

        # Step 5: Combine PDFs
        # Get terms and conditions path from config or use default
        default_terms_path = os.path.join(os.getenv('FILESYSTEM_PATH', './.filesystem'), "terms_conditions.pdf")
        terms_conditions_path = config.get("APP_SETTINGS", "terms_conditions_path", default_terms_path)

        if not os.path.exists(terms_conditions_path):
            log.error(f"Terms and conditions file not found at {terms_conditions_path}")
            return False

        combined_pdf_path = files.combine_pdfs(certificate_pdf_path, first_page_path, terms_conditions_path, audit_case_id)
        if not combined_pdf_path:
            log.error(f"Failed to combine PDFs for audit case {audit_case_id}")
            return False

        # Step 6: Update the database to record that the certificate was generated
        #success = update_audit_case(audit_case_id, combined_pdf_path, database)
        #if not success:
        #    log.error(f"Failed to update audit case record for {audit_case_id}")
        #    return False
        # TODO: Again add a indicator that the certificate was generated but do not move the case to stage 4 yet

        log.info(f"Successfully generated certificate for audit case {audit_case_id}")
        return True

    except Exception as e:
        log.error(f"Error generating certificate for audit case {audit_case_id}: {str(e)}")
        return False


def get_client_info(audit_case_id: int, database: Database) -> dict | None:
    """
    Retrieves client information for a given audit case ID from the database.

    This function queries the 'audit_case' and 'client' tables in the provided database
    to fetch client details associated with a specific audit case. If no client information
    is found, it logs a warning message and returns None. In case of an exception during
    execution, it logs the error and also returns None.

    :param audit_case_id: The unique identifier of the audit case for which
                          client information is required.
    :type audit_case_id: int
    :param database: An instance of the database object used to execute the
                     SQL query and retrieve data.
    :type database: Database
    :return: A dictionary containing client information including keys
             such as 'client_id', 'institute', 'bafin_id', 'address',
             'city', 'created_at', and 'validation_date'. Returns None
             if no information is found or if an error occurs.
    :rtype: dict | None
    """
    try:
        # Query to get client information
        result = database.query("""
                                SELECT
                                    c.id as client_id,
                                    c.institute,
                                    c.bafin_id,
                                    c.address,
                                    c.city,
                                    a.created_at,
                                    a.last_updated_at
                                FROM
                                    audit_case a
                                        JOIN
                                    client c ON a.client_id = c.id
                                WHERE
                                    a.id = ?
                                """, (audit_case_id,))

        if not result or not result[0]:
            log.warning(f"No client information found for audit case {audit_case_id}")
            return None

        # Create a dictionary with client information
        client_info = {
            'client_id': result[0][0],
            'institute': result[0][1],
            'bafin_id': result[0][2],
            'address': result[0][3],
            'city': result[0][4],
            'created_at': result[0][5],
            'validation_date': result[0][6]
        }

        return client_info

    except Exception as e:
        log.error(f"Error getting client information: {str(e)}")
        return None


def get_document_info(audit_case_id: int, database: Database) -> dict | None:
    """
    Retrieves the most recent document information for the given audit case ID from the database.
    The document information includes its path and filename. The function tries to query the database
    for a record matching the provided audit case ID, ordering the results by processing date in
    descending order, and limiting to the most recent one. If a document is found, it returns a dictionary
    containing the document path and filename. If no document is found or an error occurs during the
    operation, it logs the issue and returns `None`.

    :param audit_case_id: The unique identifier for the audit case used to query the document information.
    :type audit_case_id: int
    :param database: A Database instance that is used to query for document information.
    :type database: Database
    :return: A dictionary containing the document path and filename if found, otherwise `None`.
    :rtype: dict | None
    """
    try:
        # Query to get document information
        result = database.query("""
                                SELECT
                                    document_path,
                                    document_filename
                                FROM
                                    document
                                WHERE
                                    audit_case_id = ?
                                ORDER BY
                                    processing_date DESC
                                LIMIT 1
                                """, (audit_case_id,))

        if not result or not result[0]:
            log.warning(f"No document found for audit case {audit_case_id}")
            return None

        # Create a dictionary with document information
        document_info = {
            'document_path': result[0][0][:-4] + "pdf",  # TODO: This is a workaround and should be fixed!
            'document_filename': result[0][1]
        }

        return document_info

    except Exception as e:
        log.error(f"Error getting document information: {str(e)}")
        return None


def update_audit_case(audit_case_id: int, certificate_path: str, database: Database) -> bool:
    """
    Updates the details of a specific audit case in the database based on the provided
    audit_case_id and certificate file. This function is responsible for updating the
    stage of the audit case to indicate process completion and modifying comments to
    log the certificate generation. Additionally, it generates a hash for the certificate
    content, which is prepared for potential insertion into a document table (currently
    commented out).

    :param audit_case_id: Identifier of the audit case to update in the database.
    :type audit_case_id: int
    :param certificate_path: Path to the certificate file associated with the audit
                             case.
    :type certificate_path: str
    :param database: Database instance to execute the queries on.
    :type database: Database
    :return: True if the update operation is successful; False otherwise.
    :rtype: bool
    """
    try:
        # Read the certificate file
        with open(certificate_path, 'rb') as file:
            certificate_content = file.read()

        # Generate a hash for the certificate
        certificate_hash = hashlib.md5(certificate_content).hexdigest()

        # Update the audit case to set stage to 4 (process completion)
        database.query("""
                       UPDATE audit_case
                       SET
                           stage = 4,
                           comments = CASE
                                          WHEN comments IS NULL THEN 'Certificate generated'
                                          ELSE comments || ' | Certificate generated'
                               END
                       WHERE id = ?
                       """, (audit_case_id,))

        # TODO: Fix the display logic first before uncommenting this
        # Insert record in document table for the certificate
        #database.insert("""
        #    INSERT INTO document (
        #        document_hash,
        #        audit_case_id,
        #        document_filename,
        #        document_path,
        #        processed,
        #        processing_date
        #    ) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        #""", (
        #    certificate_hash,
        #    audit_case_id,
        #    os.path.basename(certificate_path),
        #    certificate_path,
        #    True
        #))

        log.info(f"Database updated for audit case {audit_case_id}")
        return True

    except Exception as e:
        log.error(f"Error updating database: {str(e)}")
        return False


def send_document_confirmation_email(document: PDF, db: Database) -> bool:
    """
    Sends a confirmation email to the sender of a document and logs the operation.

    This function extracts the sender's email address from the provided document,
    retrieves client information from the database, and uses a mail client to send
    a confirmation email. It logs the results of the operation, including any
    errors encountered during the process.

    :param document: The PDF document instance containing attributes such as the sender's email
                     and related metadata.
    :type document: PDF
    :param db: The database instance to query for client information required for the
               confirmation email content.
    :type db: Database
    :return: Boolean value indicating whether the confirmation email was sent successfully.
    :rtype: bool
    """
    try:
        # Get the sender's email from the document attributes (captured from the original email)
        sender_email = document.get_attributes('sender')

        if not sender_email:
            log.error(f"No sender email found in document attributes for document {document.email_id}")
            return False

        # Extract just the email address from the sender field (format might be "Name <email@domain.com>")
        import re
        email_match = re.search(r'[\w\.-]+@[\w\.-]+', sender_email)
        if email_match:
            reply_to_email = email_match.group(0)
        else:
            log.error(f"Could not extract valid email address from sender: {sender_email}")
            return False

        # Get client information from database for the email content
        client_info = db.query("""
                               SELECT
                                   c.institute,
                                   c.bafin_id,
                                   ac.id as case_id
                               FROM
                                   client c
                                       JOIN
                                   audit_case ac ON ac.client_id = c.id
                               WHERE
                                   c.id = ?
                               """, (document.client_id,))

        if not client_info or not client_info[0]:
            log.error(f"Could not find client information for client_id: {document.client_id}")
            return False

        institute, bafin_id, case_id = client_info[0]

        # Get mail client instance
        mailclient = Mailclient.get_instance()

        # Send confirmation email to the original sender
        success = mailclient.send_confirmation_email(
            to_email=reply_to_email,
            client_name=institute,
            bafin_id=str(bafin_id),
            case_id=case_id
        )

        if success:
            log.info(f"Confirmation email sent to {reply_to_email} (original sender) for case {case_id}")

            # Log to audit log
            log.info(
                f"Confirmation email sent to {reply_to_email} for client {institute}",
                audit_log=True,
                case_id=case_id
            )

            # TODO: Consider marking the original email as answered
            # if document.email_id:
            #     mailclient.mark_email_as_answered(str(document.email_id))

        else:
            log.error(f"Failed to send confirmation email to {reply_to_email} for case {case_id}")

        return success

    except Exception as e:
        log.error(f"Error sending confirmation email: {str(e)}")
        return False

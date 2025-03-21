import os
import streamlit as st
import pandas as pd
import logging as log

# Custom imports
from cls.document import Document
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
                        log.info(f'Document {attachment.get_attributes("email_id")} belongs to client {client_id}')



                        # TODO: Continue here!!!
                        get_audit_case_status()




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


def get_audit_case_status(submissions, companies):
    """
    This function checks whether a company has already submitted the required documents or not.
    It does so by comparing the submissions with a list of companies from the database.
    """
    pass # TODO: Implement the check_company_submission function

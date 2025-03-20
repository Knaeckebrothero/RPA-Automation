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
            log.warning(f'Mail with ID {mail_id} has {len(attachments)} attachments, processing all of them.')
            st.warning(f'Mail with ID {mail_id} has {len(attachments)} attachments, processing all of them.')

            for attachment in attachments:
                if attachment.get_attributes('content_type') == 'application/pdf':
                    log.info(f'Processing pdf attachment {attachment.get_attributes("filename")}')

                    # Extract text from the document
                    attachment.extract_table_data()

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


def check_company_submission(submissions, companies):
    """
    This function checks whether a company has already submitted the required documents or not.
    It does so by comparing the submissions with a list of companies from the database.
    """
    pass  # TODO: Implement the check_company_submission function

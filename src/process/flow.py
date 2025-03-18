import os
import streamlit as st
import pandas as pd
import logging as log

# Custom imports
import cfg.cache as cache
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
                        # + '.pdf'
                    )
                    # TODO: Why is it saving as NAME.pdf.pdf?

                    # Extract text from the document
                    attachment.extract_table_data()

                    # TODO: Continue HERE!!!

                    # Get the company id based on the BaFin-ID
                    company_id = database.query(f"""
                                SELECT id 
                                FROM clients 
                                WHERE bafin_id ={attachment.get_attributes('BaFin-ID')}
                                """)

                    # Check if all values match the database
                    if compare_company_values(attachment):
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

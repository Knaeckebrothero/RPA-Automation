"""
This module holds the contents for each expander used by the active_cases page.
"""
import os
import pandas as pd
import streamlit as st
import logging

# Custom imports
from cls.database import Database
from cls.document import PDF


# Set up logging
log = logging.getLogger(__name__)


def _icon(icon: bool = False) -> str:
    """
    This function returns the icon for the expander.
    Icons can be found here: https://streamlit-emoji-shortcodes-streamlit-app-gwckff.streamlit.app/

    :param icon: A boolean indicating if the icon should be displayed.
    :return: The icon in a string.
    """
    if icon:
        return "✅"
    else:
        return "❌"


# Stage 1: Waiting for documents
def stage_1(case_id: int, current_stage: int, db: Database = Database.get_instance()):
    """
    This is the first/default stage an audit case can be in.
    Cases in this stage are part of this year's audit and are waiting for the documents to be received.
    Once a document is received, meaning the application has received an email that contains a document with the
    client's baFin ID, the case will move to the next stage.

    :param case_id: The ID of the case.
    :param current_stage: The current stage of the case.
    :param db: The database instance to use. Optional and will be fetched from the class if not provided.
    """
    with st.expander(
            "Documents Received",
            expanded=(current_stage == 1),
            icon=_icon((current_stage > 1))):
        if current_stage == 1:
            st.write("Waiting to receive documents.")

            # Add the option to manually upload a document
            uploaded_file = st.file_uploader("Upload document", type=["pdf"])

            # Add the option to manually enter an email id
            email_id = st.text_input("Enter email ID")

            # TODO: Implement the functionality
        elif current_stage > 1:
            # Load information about the received document from the db
            document_info = db.query(
                """
                SELECT 
                    email_id, 
                    document_filename, 
                    document_path, 
                    processing_date
                FROM document 
                WHERE audit_case_id = ?
                """, (case_id,)
            )  # TODO: Add a date when the documents were received

            # Display information about the received documents
            if document_info:
                # Define column names for better display
                columns = ["Email ID", "Filename", "Path", "Processing Date"]

                # Convert to dataframe
                df = pd.DataFrame(document_info, columns=columns)

                # Format the 'Processed' column to show Yes/No instead of True/False
                #df["Processed"] = df["Processed"].apply(lambda x: "Yes" if x else "No")

                # If there's only one document, just show it
                if len(df) == 1:
                    st.write("Document received and ready for verification.")
                    st.dataframe(df, use_container_width=True, hide_index=True)
                else:
                    st.write(f"{len(df)} documents received and ready for verification:")
                    st.dataframe(df, use_container_width=True, hide_index=True)

                # TODO: How can processed be no but processing_date be set?

                # Create download buttons for each document
                for i, (email_id, filename, path, proc_date) in enumerate(document_info):
                    try:
                        if os.path.exists(path):
                            with open(path[:-4] + "pdf",
                                      "rb") as file:  # TODO: This is a workaround and should be fixed
                                st.download_button(
                                    # Add the filename to the button in case multiple documents have been received
                                    label="Download Document" if len(df) == 1 else f"Download {filename}",
                                    data=file,
                                    file_name=filename + ".pdf",
                                    #mime="application/pdf",
                                    key=f"download-pdf-{i}"
                                )
                                log.info(f"Document {filename} has been downloaded.")
                        else:
                            st.error(f"Document file not found: {path}")
                            log.error(f"Document file not found: {path}")
                    except Exception as e:
                        st.error(f"Error accessing document: {str(e)}")
                        log.error(f"Error accessing document: {str(e)}")
            else:
                st.warning("No documents found for this case, even though it's in stage 2 or higher.")
                log.warning("No documents found for this case, even though it's in stage 2 or higher.")

        # Button to manually update the case
        if current_stage == 1 and st.button("Update Case"):
            if uploaded_file and not email_id:
                # TODO: Create a document from the uploaded file and add it to the case (docs need to be saved in the db)!
                db.query("UPDATE audit_case SET stage = 2 WHERE id = ?", (case_id,))
                st.success("Case updated successfully!")
            elif email_id and not uploaded_file:
                # TODO: Check if the email id is valid and exists on the mailserver
                db.query("UPDATE audit_case SET stage = 2 WHERE id = ?", (case_id,))
                st.success("Case updated successfully!")
            else:
                st.error("Please provide either an email ID OR upload a document!")

            # Clear cache and refresh
            st.cache_data.clear()
            st.rerun()


# Stage 2: Data verification
def stage_2(case_id: int, current_stage: int, db: Database = Database.get_instance()):
    """
    The second stage of the audit process.
    Cases in this stage have had their documents received and are now waiting for the data to be verified.
    Once the data verification process has been successful, the case will move to the next stage.
    Should the data verification process fail, the case will remain in this stage, waiting for manual intervention.

    :param case_id: The ID of the case.
    :param current_stage: The current stage of the case.
    :param db: The database instance to use. Optional and will be fetched from the class if not provided.
    """
    with st.expander(
            "Data verification",
            expanded=(current_stage == 2),
            icon=_icon((current_stage > 2))):
        if current_stage < 2:
            st.write("Waiting for stage one to complete.")
            #log.debug(f"Waiting for stage one to be completed for case: {case_id}")
        else:
            if current_stage > 2:
                st.write("Client data has been verified against our records.")
                #log.debug(f"Client data has been verified against our records for case: {case_id}")
            elif current_stage == 2:
                st.write("Client data needs to be verified against our records.")
                #log.debug(f"Client data needs to be verified against our records for case: {case_id}")

            # TODO: Why am I getting two documents here????
            # Get documents for this audit case
            documents = db.query("""
                SELECT 
                    document_hash, 
                    document_filename, 
                    document_path, 
                    processed, 
                    processing_date
                FROM document 
                WHERE audit_case_id = ?
                ORDER BY processing_date DESC
            """, (case_id,))

            # Put the display logic into a function to avoid duplication
            def _display_comparison_table_helper_function(doc, counter: int = 0):
                # Load document from JSON (use the third index to get the path)
                document_pdf = PDF.from_json(doc[counter][2])

                # Get comparison table
                comparison_df = document_pdf.get_value_comparison_table()

                # Display in UI
                st.dataframe(comparison_df, use_container_width=True, hide_index=True)

                # Calculate match percentage
                if not comparison_df.empty:
                    matches = comparison_df['Match status'].value_counts().get('✅', 0)
                    total = len(comparison_df)
                    match_percentage = (matches / total) * 100 if total > 0 else 0
                    st.metric("Match Percentage", f"{match_percentage:.1f}%",
                              help=f"{matches} of {total} fields match")

            if documents:
                # Create tabs for each document
                if len(documents) > 1:
                    st.write(f"Found {len(documents)} documents for this case:")
                    doc_tabs = st.tabs([f"Document {i + 1}: {doc[1]}" for i, doc in enumerate(documents)])

                    # Display each document in its own tab
                    for i, document in enumerate(documents):
                        with doc_tabs[i]:
                            _display_comparison_table_helper_function(document, i)
                else:
                    # Display the one document
                    _display_comparison_table_helper_function(documents)
            else:
                # TODO: This case shouldn't exist since the case can't entr stage 2 without a document!
                #  Thouhgh a fallback option might be implemented here (something like set back to stage 1)
                #   Or the error should be logged since a doc might went missing.
                #    The code can still be used if put in expander stage_1()!
                st.warning("No documents found for this case. Please upload or process a document first.")
                log.error(f"No documents found for case: {case_id}, who is in stage 2.")


# Stage 3: Certification
def stage_3(case_id: int, current_stage: int, db: Database = Database.get_instance()):
    """
    The third stage of the audit process.
    Cases in this stage have had their data verified and are now waiting for the certificate to be issued.
    Once the certificate has been signed and submitted to the BaFin, the case will move to the next stage.

    :param case_id: The ID of the case.
    :param current_stage: The current stage of the case.
    :param db: The database instance to use. Optional and will be fetched from the class if not provided.
    """
    with st.expander(
            "Certificate issued",
            expanded=(current_stage == 3),
            icon=_icon((current_stage > 3))):
        st.write("Certificate logic goes here!")

        if current_stage == 3 and st.button("Complete Process"):
            db.query("UPDATE audit_case SET stage = 4 WHERE id = ?", (case_id,))
            st.success("Process Completed!")
            # Clear cache and refresh
            st.cache_data.clear()
            st.rerun()


# Stage 4: Process completion
def stage_4(case_id: int, current_stage: int, db: Database = Database.get_instance()):
    """
    The fourth and final stage of the audit process.
    Cases in this stage have successfully completed the audit process and are now waiting to be archived.
    Once the case has been archived, it will no longer be part of the current year's audit.

    :param case_id: The ID of the case.
    :param current_stage: The current stage of the case.
    :param db: The database instance to use. Optional and will be fetched from the class if not provided.
    """
    with st.expander(
            "Process completed",
            expanded=(current_stage == 4),
            icon=_icon((current_stage > 4))):
        st.write("Archiving logic goes here!")

        if current_stage == 4 and st.button("Archive Case"):
            db.query("UPDATE audit_case SET stage = 5 WHERE id = ?", (case_id,))
            st.success("Case Archived!")
            # Clear cache and refresh
            st.cache_data.clear()
            st.rerun()

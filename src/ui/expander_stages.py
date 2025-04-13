"""
This module holds the contents for each expander used by the active_cases page.
"""
import os
import streamlit as st
import logging

# Custom imports
from cls.database import Database
from cls.document import PDF
from ui.visuals import client_db_value_comparison


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


def _display_document_verification(case_id, doc_hash, filename, path, processed, proc_date, db):
    """
    Display document verification information and controls.

    :param case_id: The audit case ID
    :param doc_hash: The document hash
    :param filename: The document filename
    :param path: The document path
    :param processed: Whether the document has been processed
    :param proc_date: The document processing date
    :param db: The database instance
    """
    col1, col2 = st.columns([1, 2])

    with col1:
        st.write(f"**Filename:** {filename}")
        st.write(f"**Processed:** {'Yes' if processed else 'No'}")
        st.write(f"**Date:** {proc_date}")

        # Show document
        try:
            if os.path.exists(path):
                with open(path, "rb") as file:
                    st.download_button(
                        label="Download Document",
                        data=file,
                        file_name=filename,
                        mime="application/pdf"
                    )

                # Option to display the PDF
                if st.button("View PDF", key=f"view_{doc_hash[:8]}"):
                    with open(path, "rb") as file:
                        pdf_bytes = file.read()
                    st.write("**Document Preview:**")
                    st.pdf(pdf_bytes, width=300)
            else:
                st.error(f"Document file not found at: {path}")
        except Exception as e:
            st.error(f"Error accessing document: {str(e)}")

    with col2:
        st.write("**Document Verification**")
        pdf_doc = None
        try:
            if os.path.exists(path):
                with open(path, "rb") as file:
                    content = file.read()

                # Get the client_id for this case
                client_id = db.query("SELECT client_id FROM audit_case WHERE id = ?", (case_id,))[0][0]

                # Create a PDF instance
                pdf_doc = PDF(content=content, client_id=client_id)

                # Load JSON metadata if available
                json_path = f"{os.path.splitext(path)[0]}.json"
                if os.path.exists(json_path):
                    with open(json_path, 'r') as f:
                        import json
                        metadata = json.load(f)
                        if 'attributes' in metadata:
                            pdf_doc.add_attributes(metadata['attributes'])

                # Get BaFin ID from the client
                bafin_id = db.query("SELECT bafin_id FROM client WHERE id = ?", (client_id,))[0][0]
                pdf_doc.bafin_id = bafin_id

                # Generate comparison table
                comparison_df = client_db_value_comparison(pdf_doc, database=db)

                # Display the comparison table
                st.dataframe(comparison_df, use_container_width=True)

                # Calculate match percentage
                if not comparison_df.empty:
                    matches = comparison_df['Match status'].value_counts().get('✅', 0)
                    total = len(comparison_df)
                    match_percentage = (matches / total) * 100 if total > 0 else 0

                    # Display match information
                    st.metric(
                        "Match Percentage",
                        f"{match_percentage:.1f}%",
                        help=f"{matches} of {total} fields match"
                    )
            else:
                st.error("Document file not found")
        except Exception as e:
            st.error(f"Error analyzing document: {str(e)}")
            import traceback
            st.error(traceback.format_exc())

        # Add verification controls
        if not processed:
            if st.button("Verify Document as Correct", key=f"verify_{doc_hash[:8]}"):
                # Update the document as processed
                db.query("""
                    UPDATE document 
                    SET processed = TRUE 
                    WHERE document_hash = ? AND audit_case_id = ?
                """, (doc_hash, case_id))

                # Move the case to the next stage
                db.query("""
                    UPDATE audit_case 
                    SET stage = 3
                    WHERE id = ?
                """, (case_id,))

                st.success("Document verified and case moved to certification stage!")
                st.rerun()
        else:
            st.info("This document has already been verified.")


# Stage 1: Waiting for documents
def stage_1(case_id: int, current_stage: int, database: Database = None):
    """
    This is the first/default stage an audit case can be in.
    Cases in this stage are part of this year's audit and are waiting for the documents to be received.
    Once a document is received, meaning the application has received an email that contains a document with the
    client's baFin ID, the case will move to the next stage.

    :param case_id: The ID of the case.
    :param current_stage: The current stage of the case.
    :param database: The database instance to use. If None, the default instance will be used.
    """
    if not database:
        db = Database.get_instance()
    else:
        db = database

    with st.expander("Documents Received", expanded=(current_stage == 1), icon=_icon((current_stage > 1))):
        if current_stage == 1:
            st.write("Waiting to receive documents.")

            # Add the option to manually upload a document
            uploaded_file = st.file_uploader("Upload document", type=["pdf"])

            # Add the option to manually enter an email id
            email_id = st.text_input("Enter email ID")
        elif current_stage > 1:
            st.write(f"Documents received (info will be displayed here).")
            # TODO: Add date and infos about when the documents were received

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
def stage_2(case_id: int, current_stage: int, database: Database = None):
    """
    The second stage of the audit process.
    Cases in this stage have had their documents received and are now waiting for the data to be verified.
    Once the data verification process has been successful, the case will move to the next stage.
    Should the data verification process fail, the case will remain in this stage, waiting for manual intervention.

    :param case_id: The ID of the case.
    :param current_stage: The current stage of the case.
    :param database: The database instance to use.
    """
    if not database:
        db = Database.get_instance()
    else:
        db = database
    # TODO: Move this logic into a function

    with st.expander("Data verification", expanded=(current_stage == 2), icon=_icon((current_stage > 2))):
        if current_stage <= 2:
            st.write("Client data needs to be verified against our records.")

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

            if documents:
                # Create tabs for each document
                if len(documents) > 1:
                    st.write(f"Found {len(documents)} documents for this case:")
                    doc_tabs = st.tabs([f"Document {i+1}: {doc[1]}" for i, doc in enumerate(documents)])

                    for i, (doc_hash, filename, path, processed, proc_date) in enumerate(documents):
                        with doc_tabs[i]:
                            _display_document_verification(case_id, doc_hash, filename, path, processed, proc_date, db)
                else:
                    # Only one document, no need for tabs
                    doc_hash, filename, path, processed, proc_date = documents[0]
                    _display_document_verification(case_id, doc_hash, filename, path, processed, proc_date, db)
            else:

                # TODO: This case shouldn't exist since the case can't entr stage 2 without a document!
                #  Thouhgh a fallback option might be implemented here (something like set back to stage 1)
                #   Or the error should be logged since a doc might went missing.
                #    The code can still be used if put in expander stage_1()!
                st.warning("No documents found for this case. Please upload or process a document first.")

                # Option to manually upload a document
                uploaded_file = st.file_uploader("Upload document", type=["pdf"])
                if uploaded_file and st.button("Process Document"):
                    # Create a Document instance and process it
                    from cls.document import PDF

                    try:
                        # Get the client_id for this case
                        client_id = db.query("SELECT client_id FROM audit_case WHERE id = ?", (case_id,))[0][0]

                        # Create a PDF instance
                        pdf_document = PDF(
                            content=uploaded_file.read(),
                            audit_case_id=case_id,
                            client_id=client_id,
                            attributes={"filename": uploaded_file.name}
                        )

                        # Extract text from the document
                        from processing.ocr import create_ocr_reader
                        ocr_reader = create_ocr_reader(language='de')
                        pdf_document.extract_table_data(ocr_reader=ocr_reader)

                        # Store the document
                        if pdf_document.store_document(case_id):
                            st.success(f"Document {uploaded_file.name} processed and stored successfully!")
                            st.rerun()
                        else:
                            st.error("Failed to process and store the document.")
                    except Exception as e:
                        st.error(f"Error processing document: {str(e)}")

        elif current_stage > 2:
            st.write("Client data has been verified against our records.")

            # Option to view verification history
            if st.checkbox("Show verification history"):
                documents = db.query("""
                    SELECT 
                        document_hash, 
                        document_filename, 
                        processed, 
                        processing_date
                    FROM document 
                    WHERE audit_case_id = ? AND processed = TRUE
                    ORDER BY processing_date DESC
                """, (case_id,))

                if documents:
                    for doc_hash, filename, processed, proc_date in documents:
                        st.write(f"✅ {filename} - Verified on {proc_date}")
                else:
                    st.info("No verified documents found in history.")


# Stage 3: Certification
def stage_3():
    """
    The third stage of the audit process.
    Cases in this stage have had their data verified and are now waiting for the certificate to be issued.
    Once the certificate has been signed and submitted to the BaFin, the case will move to the next stage.
    """
    with st.expander("Certificate issued", icon=_icon()):
        st.write("Inside the expander.")


# Stage 4: Process completion
def stage_4():
    """
    The fourth and final stage of the audit process.
    Cases in this stage have successfully completed the audit process and are now waiting to be archived.
    Once the case has been archived, it will no longer be part of the current year's audit.
    """
    with st.expander("Process completed", icon=_icon()):
        st.write("Inside the expander.")

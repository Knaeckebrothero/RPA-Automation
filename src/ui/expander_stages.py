"""
This module holds the contents for each expander used by the active_cases page.
"""
import streamlit as st
import logging

# Custom imports
from cls.database import Database


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
    """
    if not database:
        db = Database.get_instance()
    else:
        db = database

    with st.expander("Data verification", expanded=(current_stage == 2), icon=_icon((current_stage > 2))):
        if current_stage <= 2:
            st.write("Client data needs to be verified against our records.")
        elif current_stage > 2:
            st.write("Client data has been verified against our records.")

        # Button to manually update the case
        if current_stage == 2 and st.button("Process document"):
            db.query("UPDATE audit_case SET stage = 3 WHERE id = ?", (case_id,))
            st.success("Certificate Issued!")
            # Clear cache and refresh
            st.cache_data.clear()
            st.rerun()
        # TODO: Continue here!!! Implement the new document from db stuff


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

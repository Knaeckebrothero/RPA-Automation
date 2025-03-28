"""
This module holds the contents for each expander used by the active_cases page.
"""
import streamlit as st


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
def stage_1():
    """
    This is the first/default stage an audit case can be in.
    Cases in this stage are part of this year's audit and are waiting for the documents to be received.
    Once a document is received, meaning the application has received an email that contains a document with the
    client's baFin ID, the case will move to the next stage.
    """
    with st.expander("Documents received", icon=_icon()):
        st.write("Inside the expander.")


# Stage 2: Data verification
def stage_2():
    """
    The second stage of the audit process.
    Cases in this stage have had their documents received and are now waiting for the data to be verified.
    Once the data verification process has been successful, the case will move to the next stage.
    Should the data verification process fail, the case will remain in this stage, waiting for manual intervention.
    """
    with st.expander("Data verified", icon=_icon()):
        st.write("Inside the expander.")


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

"""
This module holds the main ui page for the application.
"""
import os
import pandas as pd
import streamlit as st
import logging as log

# Custom imports
import ui.visuals as visuals
import cache as cache
from workflow import assess_emails


def home():
    """
    This is the main ui page for the application.
    It serves as a landing page and provides the user with options to navigate the application.
    """
    log.debug('Rendering home page')

    # Page title and description
    st.header('Document Fetcher')
    st.write('Welcome to the Document Fetcher application!')

    # Fetch the emails and client
    emails = cache.get_emails()

    # Configure visuals layout
    column_left, column_right = st.columns(2)

    # Display a plot on the right
    with column_left:
        # Pie chart showing the submission ratio
        st.pyplot(visuals.pie_submission_ratio())
        # TODO: Fix issue with labels overlapping

    # Display a table on the left
    with column_right:
        # Display the mails
        st.dataframe(emails)

    # TODO: Remove old processing logic in favor of the "Active Cases" page
    # Display a multiselect box to select documents to process
    docs_to_process = st.multiselect('Select documents to process', emails['ID'])

    # Process only the selected documents
    if st.button('Process selected documents'):

        # TODO: Finish integration of the assess_emails function

        # Iterate over the selected documents
        for mail_id in docs_to_process:
            assess_emails(docs_to_process)

    # Process all the documents
    if st.button('Process all documents'):
        db = cache.get_database()
        mailclient = cache.get_mailclient()

        # Get all mails that are already in the database
        already_processed_mails = [x[0] for x in db.query('SELECT email_id FROM audit_case')]

        # If no mails are in the database, fetch all mails
        if len(already_processed_mails) > 0:
            assess_emails(mailclient.get_mails(already_processed_mails)['ID'])
        else:
            assess_emails(emails['ID'])


def active_cases():
    """
    UI page for viewing and managing active audit cases.
    """
    log.debug('Rendering active cases page')

    # Fetch the active cases and clients
    active_cases_df = cache.get_database().get_active_client_cases()

    # Page title and description
    st.header('Active Cases')

    if active_cases_df.empty:
        st.info("No active audit cases found. All cases have been completed and archived.")
        return

    # Create tabs for different views
    tab1, tab2 = st.tabs(["Case List", "Case Details"])

    with tab1:
        # Display a table of all active cases
        st.subheader("All Active Cases")

        # Create a more user-friendly display table
        display_df = active_cases_df[['case_id', 'institute', 'bafin_id', 'status', 'created_at', 'last_updated_at']].copy()
        display_df.columns = ['Case ID', 'Institute', 'BaFin ID', 'Status', 'Created', 'Last Updated']

        # Format dates
        display_df['Created'] = display_df['Created'].dt.strftime('%Y-%m-%d')
        display_df['Last Updated'] = display_df['Last Updated'].dt.strftime('%Y-%m-%d %H:%M')

        # Add status badges
        display_df['Status'] = active_cases_df['status'].apply(
            lambda x: visuals.status_badge(x)
        )

        # Display the table with HTML rendering enabled
        st.write(display_df.to_html(escape=False, index=False), unsafe_allow_html=True)

        # Add a button to refresh the data
        if st.button("Refresh Cases"):
            st.cache_data.clear()
            st.rerun()

    with tab2:
        # Setup session state for selected case if not already initialized
        if 'selected_case_id' not in st.session_state:
            st.session_state['selected_case_id'] = None

        # Create options for the selectbox with client names and case IDs
        case_options = [f"{row['institute']} (Case #{row['case_id']})" for _, row in active_cases_df.iterrows()]

        # Display a selectbox to select a case
        selected_option = st.selectbox(
            'Select a case to view details',
            case_options,
            key='case_selector'
        )

        if selected_option:
            # Extract case ID from the selection
            case_id = int(selected_option.split("Case #")[1].strip(")"))
            st.session_state['selected_case_id'] = case_id

            # Find the selected case
            selected_case = active_cases_df[active_cases_df['case_id'] == case_id].iloc[0]

            # Display case information
            st.markdown(f"### Case #{selected_case['case_id']}")
            st.markdown(f"**Status:** {visuals.status_badge(selected_case['status'])}", unsafe_allow_html=True)

            # Create columns for layout
            col1, col2 = st.columns(2)

            # Case details column
            with col1:
                st.subheader("Case Details")
                st.markdown(f"**Created:** {selected_case['created_at'].strftime('%Y-%m-%d')}")
                st.markdown(f"**Last Updated:** {selected_case['last_updated_at'].strftime('%Y-%m-%d %H:%M')}")

                # Comments section with editing capability
                st.subheader("Comments")
                current_comments = selected_case['comments'] if pd.notna(selected_case['comments']) else ""

                new_comments = st.text_area("Edit Comments", value=current_comments, height=100)

                if new_comments != current_comments:
                    if st.button("Save Comments"):
                        # Update comments in database
                        db = cache.get_database()
                        db.query(f"""
                            UPDATE audit_case 
                            SET comments = ? 
                            WHERE id = ?
                        """, (new_comments, case_id))
                        st.success("Comments updated successfully!")
                        # Clear cache and refresh
                        st.cache_data.clear()
                        st.rerun()

            # Client details column
            with col2:
                st.subheader("Client Information")
                st.markdown(f"**Institute:** {selected_case['institute']}")
                st.markdown(f"**BaFin ID:** {selected_case['bafin_id']}")
                st.markdown(f"**Address:** {selected_case['address']}")
                st.markdown(f"**City:** {selected_case['city']}")
                st.markdown(f"**Contact Person:** {selected_case['contact_person']}")
                st.markdown(f"**Phone:** {selected_case['phone']}")
                st.markdown(f"**Fax:** {selected_case['fax']}")
                st.markdown(f"**Email:** {selected_case['email']}")

            # Divider
            st.divider()

            # Process steps
            st.subheader("Process Steps")

            # Define steps based on status
            current_status = selected_case['status']

            # Display expandable sections for each step of the process
            with st.expander("Step 1: Documents Received", expanded=(current_status == 1)):
                st.write("Documents have been received from the client.")
                if current_status == 1 and st.button("Mark as Verified"):
                    db = cache.get_database()
                    db.query("UPDATE audit_case SET status = 2 WHERE id = ?", (case_id,))
                    st.success("Case marked as Verified!")
                    # Clear cache and refresh
                    st.cache_data.clear()
                    st.rerun()

            with st.expander("Step 2: Data Verified", expanded=(current_status == 2)):
                st.write("Client data has been verified against our records.")
                if current_status == 2 and st.button("Issue Certificate"):
                    db = cache.get_database()
                    db.query("UPDATE audit_case SET status = 3 WHERE id = ?", (case_id,))
                    st.success("Certificate Issued!")
                    # Clear cache and refresh
                    st.cache_data.clear()
                    st.rerun()

            with st.expander("Step 3: Certificate Issued", expanded=(current_status == 3)):
                st.write("Certificate has been issued to BaFin.")
                if current_status == 3 and st.button("Complete Process"):
                    db = cache.get_database()
                    db.query("UPDATE audit_case SET status = 4 WHERE id = ?", (case_id,))
                    st.success("Process Completed!")
                    # Clear cache and refresh
                    st.cache_data.clear()
                    st.rerun()

            with st.expander("Step 4: Process Completed", expanded=(current_status == 4)):
                st.write("The audit process has been completed.")
                if current_status == 4 and st.button("Archive Case"):
                    db = cache.get_database()
                    db.query("UPDATE audit_case SET status = 5 WHERE id = ?", (case_id,))
                    st.success("Case Archived!")
                    # Clear cache and refresh
                    st.cache_data.clear()
                    st.rerun()




def settings():
    """
    This is the settings ui page for the application.
    """
    log.debug('Rendering settings page')

    # Page title and description
    st.header('Settings')
    st.write('Configure the application settings below.')


def about():
    """
    This is the about ui page for the application.
    """
    # Display the contents of the log file in a code block (as a placeholder)
    with open(os.path.join(os.getenv('LOG_PATH', ''), 'application.log'), 'r') as file:
        st.code(file.read())

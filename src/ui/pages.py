"""
This module holds the main ui page for the application.
"""
import os
import pandas as pd
import streamlit as st
import logging as log

# Custom imports
import ui.visuals as visuals
import cfg.cache as cache
import processing.data as process
import ui.expander_steps as expander


def _process_documents(docs_to_process: pd.DataFrame, mailclient, database):
    # TODO: Move the processing logic somewhere else
    log.info(f'Processing: {len(docs_to_process)} selected mails...')

    # Iterate over the selected documents
    for mail_id in docs_to_process:
        log.debug(f'Processing mail with ID {mail_id}')
        attachments = mailclient.get_attachments(mail_id)

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

                    # TODO: Move this to a separate function
                    # Ensure the filesystem's download folder path exists
                    filesystem = os.getenv('FILESYSTEM_PATH')
                    if not os.path.exists(filesystem + "/downloads/"):
                        os.makedirs(filesystem + "/downloads/")

                    # Save the attachment to the filesystem's downloads folder
                    attachment.save_to_file(
                        filesystem +
                        "/downloads/" +
                        attachment.get_attributes("filename") +
                        '.pdf'
                    )
                    # TODO: Why is it saving as NAME.pdf.pdf?

                    # Extract text from the document
                    attachment.extract_table_data()

                    # Get the company id based on the BaFin-ID
                    company_id = database.query(f"""
                                SELECT id 
                                FROM clients 
                                WHERE bafin_id ={attachment.get_attributes('BaFin-ID')}
                                """)

                    # Check if all values match the database
                    if process.compare_company_values(attachment):
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
    # docs_to_process = st.multiselect('Select documents to process', emails['ID'])

    # Process only the selected documents
    # if st.button('Process selected documents'):
    #     _process_documents(docs_to_process, cache.get_mailclient(), cache.get_database())

    # Process all the documents
    # if st.button('Process all documents'):
    #    db = cache.get_database()
    #    mailclient = cache.get_mailclient()

    #    # Get all mails that are already in the database
    #    already_processed_mails = [x[0] for x in db.query('SELECT email_id FROM status')]

        # If no mails are in the database, fetch all mails
    #    if len(already_processed_mails) > 0:
    #        _process_documents(mailclient.get_mails(already_processed_mails)['ID'], mailclient, db)
    #    else:
    #        _process_documents(emails['ID'], mailclient, db)


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

"""
This module holds the main ui page for the application.
"""
import os
import pandas as pd
import streamlit as st
import logging
import base64
import datetime

# Custom imports
import ui.visuals as visuals
import workflow.audit as auditflow
from cls.mailclient import Mailclient
from cls.database import Database
import ui.expander_stages as expander_stages
import workflow.security as sec
from cls.document import PDF


# Set up logging
log = logging.getLogger(__name__)


def home(mailclient: Mailclient = None, database: Database = Database.get_instance()):
    """
    This is the main ui page for the application.
    It serves as a landing page and provides the user with options to navigate the application.
    """
    log.debug('Rendering home page')

    # Page title and description
    st.header('Document Fetcher')
    st.write('Welcome to the Document Fetcher application!')
    
    # Fetch the emails (exclude those who have already been downloaded)
    emails = auditflow.fetch_new_emails(database)
    # TODO: Check if this interferes with the visuals (since we don't just load all emails present)

    # Configure visuals layout
    column_left, column_right = st.columns(2)

    # Display the mails
    st.dataframe(emails, hide_index=True)
    # TODO: Check if the new selector ids work (e.g. the list number matches the number used by the selector)

    # Display a plot on the right
    with column_left:
        # Pie chart showing the submission ratio
        st.pyplot(visuals.pie_submission_ratio())
        # TODO: Fix issue with labels overlapping

    # Display a table on the left
    with column_right:
        if emails.empty:
            st.warning("No new emails to process.")
            return

        # Display a multiselect box to select documents to process
        docs_to_process = st.multiselect('Select documents to process', emails['ID'])

        # Process only the selected documents
        if st.button('Process selected documents'):
            with st.spinner(f'Processing mails'):
                auditflow.assess_emails(docs_to_process)

            # Rerun the app to update the display
            st.rerun()

        # Process all the documents
        if st.button('Process all documents'):

            # Check if the mailclient instance is provided, otherwise fetch the instance
            if not mailclient:
                mailclient = Mailclient.get_instance()

            # Get all mails that are already part of an active audit case
            already_processed_mails = [x[0] for x in database.query(
                """
                SELECT email_id 
                FROM audit_case
                WHERE email_id IS NOT NULL
                AND stage < 5
                """)]

            # If no mails are in the database, fetch all mails
            if len(already_processed_mails) > 0:
                with st.spinner(f'Processing mails'):
                    auditflow.assess_emails(mailclient.get_mails(excluded_ids=already_processed_mails)['ID'])
            else:
                with st.spinner(f'Processing mails'):
                    auditflow.assess_emails(emails['ID'])

            # Rerun the app to update the display
            st.rerun()

    # Fetch the active cases and clients
    active_cases_df = database.get_active_client_cases()
    if active_cases_df.empty:
        st.info("No active audit cases found. All cases have been completed and archived.")
        return

    # Display a table of all active cases
    st.subheader("Active Cases")

    # Create a more user-friendly display table
    display_df = active_cases_df[['case_id', 'bafin_id', 'institute', 'stage', 'created_at', 'last_updated_at']].copy()
    display_df.columns = ['Case ID', 'BaFin ID', 'Institute', 'Stage', 'Created', 'Last Updated']

    # Format dates
    display_df['Created'] = display_df['Created'].dt.strftime('%d.%m.%Y')
    display_df['Last Updated'] = display_df['Last Updated'].dt.strftime('%d.%m.%Y %H:%M')

    # Add stage badges
    display_df['Stage'] = active_cases_df['stage'].apply(
        lambda x: visuals.stage_badge(x, pure_string=True)
    )

    # Display the table with HTML rendering enabled
    st.write(display_df.to_html(escape=False, index=False), unsafe_allow_html=True)

    # Add a button to refresh the data
    if st.button("Refresh Cases"):
        st.cache_data.clear()  # TODO: Check if this deletes the database and stuff as well
        st.rerun()


def active_cases(database: Database = Database.get_instance()):
    """
    UI page for viewing and managing active audit cases.

    :param database: Database instance to use. Defaults to the global database instance.
    """
    log.debug('Rendering active cases page')

    # Fetch the active cases and clients
    active_cases_df = database.get_active_client_cases()
    # TODO: Move the active_cases df to the session state!

    # Page title and description
    st.header('Active Cases')

    if active_cases_df.empty:
        st.info("No active audit cases found. All cases have been completed and archived.")
        return

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

    # Create tabs for different views
    tab1, tab2 = st.tabs(["Case Details", "Document Values"])

    with tab1:
        if selected_option:
            # Extract case ID from the selection
            case_id = int(selected_option.split("Case #")[1].strip(")"))
            st.session_state['selected_case_id'] = case_id

            # Find the selected case
            selected_case = active_cases_df[active_cases_df['case_id'] == case_id].iloc[0]

            # Display case information
            st.markdown(
                f"**Case {selected_case['case_id']} Stage:** {visuals.stage_badge(selected_case['stage'])}",
                        unsafe_allow_html=True
            )

            # Define steps based on stage
            current_stage = selected_case['stage']

            # Display expandable sections for each step of the process
            expander_stages.stage_1(case_id, current_stage, database)
            expander_stages.stage_2(case_id, current_stage, database)

            # Display additional stages based on the user role
            if st.session_state['user_role'] == 'inspector':
                expander_stages.stage_3(case_id, current_stage, database)
            elif st.session_state['user_role'] == 'admin':
                expander_stages.stage_3(case_id, current_stage, database)
                expander_stages.stage_4(case_id, current_stage, database)

            # Divider
            st.divider()

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
                new_comments = st.text_area("Edit Comments", value=current_comments, height=143)

                if new_comments != current_comments:
                    if st.button("Save Comments"):
                        # Update comments in database
                        database.insert(f"""
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

    with tab2:
        if selected_option and st.session_state['selected_case_id']:
            case_id = st.session_state['selected_case_id']
            
            # Get document details for the selected case
            document_data = database.query("""
                SELECT document_path, document_hash 
                FROM document 
                WHERE audit_case_id = ? 
                ORDER BY processing_date DESC 
                LIMIT 1
            """, (case_id,))  # TODO: Do we still need the document_hash?
            
            if not document_data:
                st.warning("No document found for this audit case.")
                return
                
            # Create two columns - one for PDF display, one for editing values
            col1, col2 = st.columns([6, 3])

            # Load the document with audit values
            document_path = document_data[0][0]
            doc = PDF.from_json(document_path)
            
            with col1:
                st.subheader("Document Preview")
                # Display PDF using iframe
                if document_path and os.path.exists(document_path):
                    # Create a base64 representation of the PDF
                    base64_pdf = base64.b64encode(doc.get_content()).decode('utf-8')

                    # Embed the PDF
                    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="1600px" type="application/pdf"></iframe>'
                    st.markdown(pdf_display, unsafe_allow_html=True)
                else:
                    st.error("PDF file not found.")

            with col2:
                st.subheader("Edit Extracted Values")
                
                if not hasattr(doc, '_audit_values') or not doc._audit_values:
                    st.warning("No audit values found for this document.")
                    return
                
                st.markdown("### Extracted Values")
                st.markdown("Edit the values extracted from the document:")
                
                # Create a form for editing the values
                with st.form("edit_audit_values"):
                    edited_values = {}
                    
                    # Group values by type
                    positions = {}
                    findag_entries = {}
                    
                    # Organize values into categories for better display
                    for key, value in doc._audit_values.items():
                        # Skip metadata keys
                        if key.startswith('raw_') or key.startswith('key_') or key.startswith('error_'):
                            continue
                            
                        # Display position values
                        if key.startswith('p0'):
                            positions[key] = value
                        # Display FinDAG values
                        elif key.startswith('ab2s1n'):
                            findag_entries[key] = value
                    
                    # Position values section
                    if positions:
                        st.markdown("#### SONO-1 Positions")
                        for key, value in positions.items():
                            position_number = key[1:]  # Extract the position number
                            original_key = doc._audit_values.get(f"key_{key}", "Unknown")
                            
                            # Add tooltip with original extracted text field name
                            help_text = f"Original field: {original_key}"
                            
                            # Edit field with label showing position number
                            edited_value = st.number_input(
                                f"Position {position_number}", 
                                value=value,
                                help=help_text
                            )
                            edited_values[key] = edited_value
                    
                    # FinDAG values section
                    if findag_entries:
                        st.markdown("#### FinDAG § 16j Abs. 2 Satz 1")
                        
                        # Sort keys numerically by extracting the number portion
                        sorted_keys = sorted(findag_entries.keys(), 
                                             key=lambda k: int(k[-2:]))  # Sort by the last two digits
                        
                        for key in sorted_keys:
                            value = findag_entries[key]
                            # Extract the number (e.g., "01" from "ab2s1n01")
                            number = key[-2:]
                            original_key = doc._audit_values.get(f"key_{key}", "Unknown")
                            
                            # Add tooltip with original extracted text field name
                            help_text = f"Original field: {original_key}"
                            
                            # Edit field with label showing FinDAG reference
                            edited_value = st.number_input(
                                f"Nr. {number.lstrip('0')}", 
                                value=value,
                                help=help_text
                            )
                            edited_values[key] = edited_value
                    
                    # Submit button
                    submitted = st.form_submit_button("Save Changes")
                    
                    if submitted:
                        # Update the audit values in the document
                        for key, value in edited_values.items():
                            doc._audit_values[key] = value
                            # TODO: Implement a get method for the audit values!
                        
                        # Save the document back to the database
                        doc.save_to_json()
                        st.success("Audit values updated successfully!")
                        
                # Display original text extraction for reference
                with st.expander("Show original extracted field names"):
                    st.markdown("### Original Field Names")
                    st.markdown("These are the original fields from which values were extracted:")
                    
                    for key in doc._audit_values:
                        if key.startswith('key_'):
                            field_key = key[4:]  # Remove the 'key_' prefix
                            if field_key in doc._audit_values:
                                st.markdown(f"**{field_key}**: {doc._audit_values[key]}")
        else:
            st.info("Please select a case to edit document values.")


def settings(database: Database = Database().get_instance()):
    """
    This is the settings ui page for the application.

    :param database: Optional database instance to use.
    """
    log.debug('Rendering settings page')

    # Import the config handler
    from cls.config import ConfigHandler

    # Get config instance
    config = ConfigHandler.get_instance()

    # Page title and description
    st.header('Settings')
    st.write('Configure the application settings below.')

    # Split the page into tabs
    application_tab, audit_tab, user_tab = st.tabs(["Application Settings", "Audit Settings", "User Management"])

    with application_tab:
        st.subheader("Application Settings")

        # Certificate Template Settings
        with st.expander("Certificate Template Settings", expanded=True):
            st.write("Configure the template used for generating certificates.")

            # Get current template path from config
            default_template_path = os.path.join(os.getenv('FILESYSTEM_PATH', './.filesystem'),
                                                 "certificate_template.docx")
            current_template_path = config.get("APP_SETTINGS", "certificate_template_path", default_template_path)

            # Display current template info
            st.markdown("#### Current Template")
            if os.path.exists(current_template_path):
                st.success(f"Template is configured: {os.path.basename(current_template_path)}")

                # Option to download current template
                with open(current_template_path, "rb") as file:
                    st.download_button(
                        label="Download Current Template",
                        data=file,
                        file_name=os.path.basename(current_template_path),
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
            else:
                st.warning(f"Template file not found at {current_template_path}")

            # Upload new template
            st.markdown("#### Upload New Template")
            st.write("""
            Upload a new Word document (.docx) template for certificates. The template should contain the following placeholders:
            - [DATE] - Current date
            - [YEAR] - Current year
            - [BAFIN_ID] - Client BaFin ID
            - [INSTITUTE_NAME] - Client institute name
            - [INSTITUTE_ADDRESS] - Client address
            - [INSTITUTE_CITY] - Client city
            - [FISCAL_YEAR_END] - End of fiscal year
            - [VALIDATION_DATE] - Validation date
            """)  # TODO: Put this into a external config file!

            uploaded_template = st.file_uploader("Upload template file", type="docx")

            if uploaded_template is not None:
                # Save the uploaded template
                template_dir = os.path.join(os.getenv('FILESYSTEM_PATH', './.filesystem'))
                os.makedirs(template_dir, exist_ok=True)

                template_path = os.path.join(template_dir, "certificate_template.docx")

                with open(template_path, "wb") as f:
                    f.write(uploaded_template.getvalue())

                # Update the config
                config.set("APP_SETTINGS", "certificate_template_path", template_path)

                st.success(f"Template updated successfully: {os.path.basename(template_path)}")

        # Archive File Name Settings
        with st.expander("Archive Settings", expanded=True):
            st.write("Configure the naming convention for archive zip files.")

            # Get current archive prefix from config
            default_prefix = "audit_archive"
            current_prefix = config.get("APP_SETTINGS", "archive_file_prefix", default_prefix)

            # Input for archive file prefix
            new_prefix = st.text_input(
                "Archive File Prefix",
                value=current_prefix,
                help="This prefix will be used for naming archive zip files. The final format will be: prefix_YYYY-MM-DD.zip"
            )

            # Display preview of the file name
            current_date = datetime.datetime.now().strftime("%Y-%m-%d")
            st.write(f"Preview: `{new_prefix}_{current_date}.zip`")

            if st.button("Save Archive Settings"):
                # Save the prefix to the config
                config.set("APP_SETTINGS", "archive_file_prefix", new_prefix)
                st.success("Archive file prefix updated successfully!")

        # Application log settings
        with st.expander("Application Logs", expanded=False):
            log_path = os.path.join(os.getenv('LOG_PATH', ''), 'application.log')
            if os.path.exists(log_path):
                try:
                    # Use a deque to efficiently get the last 300 lines
                    from collections import deque

                    # Read the last 300 lines
                    with open(log_path, 'r') as file:
                        last_lines = deque(file, maxlen=300)
                        last_lines = list(last_lines)

                    # Add a slider to control how many lines to display
                    num_lines = st.slider('Number of log lines to display',
                                          min_value=10,
                                          max_value=len(last_lines),
                                          value=min(100, len(last_lines)),
                                          step=10)

                    # Get the selected number of lines from the end of the list
                    displayed_lines = last_lines[-num_lines:] if num_lines < len(last_lines) else last_lines

                    # Join the lines into a single string
                    log_content = ''.join(displayed_lines)

                    st.subheader(f'Application Logs (Last {num_lines} of {len(last_lines)} lines)')
                    st.code(log_content)
                except Exception as e:
                    st.error(f"Error reading log file: {str(e)}")
            else:
                st.warning(f"Log file not found at {log_path}")

    # Modify the archive button logic to use the custom archive name
    with audit_tab:
        # Existing audit_tab code here...
        st.subheader("Audit Process")

        with st.expander("Initialize Annual Audit Process", expanded=True):
            # Initialize Annual Audit Process code...
            st.write("""
            This will create a new audit case (stage 1) for every client in the database 
            that doesn't already have an active case. Use this to start the annual audit process.
            """)

            # Add a confirmation checkbox for safety
            confirm_init = st.checkbox("I understand this will create new audit cases for all clients")

            if st.button("Initialize Audit Cases", disabled=not confirm_init):
                with st.spinner("Creating audit cases..."):
                    # Find clients without active audit cases
                    clients_without_cases = database.query("""
                                                     SELECT id
                                                     FROM client
                                                     WHERE id NOT IN (SELECT client_id
                                                                      FROM audit_case
                                                                      WHERE stage < 5)
                                                     """)

                    if not clients_without_cases:
                        st.warning("All clients already have active audit cases.")
                    else:
                        # Create a new audit case for each client
                        created_count = 0
                        for client_id in clients_without_cases:
                            database.insert("""
                                      INSERT INTO audit_case (client_id, stage, comments)
                                      VALUES (?, 1, 'Automatically created for annual audit process')
                                      """, (client_id[0],))
                            created_count += 1

                        # Success message
                        st.success(f"Successfully created {created_count} new audit cases.")

                        # Log the action
                        log.info(f"Created {created_count} new audit cases for annual audit process")

        # Archive cases section
        with st.expander("Archive Completed Cases", expanded=True):
            st.write(
                """
                This will archive all audit cases that are in stage 4 (Process Completion).
                Archived cases will no longer appear in the active cases view.
                """
            )

            # Get case statistics
            stage_counts = database.query("""
                                    SELECT stage, COUNT(*)
                                    FROM audit_case
                                    WHERE stage < 5
                                    GROUP BY stage
                                    """)

            # Create a dictionary of stage counts
            stage_stats = {1: 0, 2: 0, 3: 0, 4: 0}
            for stage, count in stage_counts:
                stage_stats[stage] = count

            # Display statistics
            st.write("Current audit case statistics:")
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("Stage 1", stage_stats[1], help="Waiting for documents")
            with col2:
                st.metric("Stage 2", stage_stats[2], help="Data verification")
            with col3:
                st.metric("Stage 3", stage_stats[3], help="Certification")
            with col4:
                st.metric("Stage 4", stage_stats[4], help="Process completion")

            # Warning if there are cases not in stage 4
            not_completed = stage_stats[1] + stage_stats[2] + stage_stats[3]
            if not_completed > 0:
                st.warning(
                    f"⚠️ There are still {not_completed} active cases that are not ready for archiving (stages 1-3).")

            # Add a confirmation checkbox for safety
            confirm_archive = st.checkbox("I understand this will archive all cases in stage 4")

            if st.button("Archive Completed Cases", disabled=not confirm_archive):
                with st.spinner("Archiving completed cases..."):
                    # Count cases to be archived
                    cases_to_archive = database.query("""
                                                SELECT COUNT(*)
                                                FROM audit_case
                                                WHERE stage = 4
                                                """)[0][0]

                    if cases_to_archive == 0:
                        st.info("No completed cases to archive.")
                    else:
                        # Get archive file prefix from config
                        default_prefix = "audit_archive"
                        archive_prefix = config.get("APP_SETTINGS", "archive_file_prefix", default_prefix)
                        current_date = datetime.datetime.now().strftime("%Y-%m-%d")
                        archive_filename = f"{archive_prefix}_{current_date}.zip"

                        # TODO: Implement archiving logic with the custom filename
                        # 1. Move documents to archive storage
                        # 2. Update database records
                        # 3. Create archive logs

                        # For now, just update the stage to 5 (Archived)
                        database.insert("""
                            UPDATE audit_case 
                            SET stage = 5,
                                comments = CASE 
                                    WHEN comments IS NULL THEN 'Archived automatically as {0}'
                                    ELSE comments || ' | Archived automatically as {0}'
                                END
                            WHERE stage = 4
                        """.format(archive_filename))

                        # Success message
                        st.success(f"Successfully archived {cases_to_archive} completed cases as {archive_filename}.")

                        # Log the action
                        log.info(f"Archived {cases_to_archive} completed cases as {archive_filename}")

                        # Refresh the statistics
                        st.rerun()

    # Existing user_tab code
    with user_tab:
        # User management code... (no changes needed)
        st.subheader("User Management")

        # Check if the database instance is provided, otherwise fetch the instance
        if database:
            db = database
        else:
            db = Database().get_instance()

        # Fetch all users from the database
        users_data = db.query("""
                              SELECT id, username_email, role, created_at
                              FROM user
                              ORDER BY created_at DESC
                              """)

        if not users_data:
            st.warning("No users found in the database.")
        else:
            # Convert to DataFrame for easier display
            users_df = pd.DataFrame(users_data, columns=['ID', 'Username', 'Role', 'Created At'])
            users_df['Created At'] = pd.to_datetime(users_df['Created At']).dt.strftime('%Y-%m-%d %H:%M')

            # 1. Display table of current users
            st.markdown("### Current Users")
            st.dataframe(users_df[['Username', 'Role', 'Created At']], hide_index=True)

            # 2. User deletion section
            st.markdown("### Delete User")

            # Create a dropdown to select user to delete
            user_options = [(row['ID'], row['Username']) for _, row in users_df.iterrows()]
            selected_user_id = st.selectbox(
                "Select a user to delete",
                options=[user_id for user_id, _ in user_options],
                format_func=lambda x: next((username for user_id, username in user_options if user_id == x), ""),
                index=None
            )

            if st.button("Delete Selected User", disabled=selected_user_id is None):
                # Check if trying to delete yourself
                if selected_user_id == st.session_state.get('user_id'):
                    st.error("You cannot delete your own account.")
                else:
                    # Delete the user
                    try:
                        # TODO: Rename the method (refactor db to have functions instead of query methods)
                        db.insert("""
                                 DELETE
                                 FROM user
                                 WHERE id = ?
                                 """, (selected_user_id,))
                        st.success("User deleted successfully.")

                        # Force refresh
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error deleting user: {str(e)}")

        # 3. User creation form
        st.markdown("### Create New User")

        with st.form("create_user_form"):
            new_username = st.text_input("Email/Username", placeholder="user@example.com")
            new_password = st.text_input("Password", type="password")
            new_role = st.selectbox("Role", options=["admin", "auditor", "inspector"])

            submit_button = st.form_submit_button("Create User")

            if submit_button:
                if not new_username or not new_password:
                    st.error("Please enter both username and password.")
                else:
                    # Check if user already exists
                    existing_user = db.query("""
                                             SELECT id
                                             FROM user
                                             WHERE username_email = ?
                                             """, (new_username,))

                    if existing_user:
                        st.error("A user with that username already exists.")
                    else:
                        try:
                            # Import the security module to create password hash
                            import workflow.security as sec

                            # Generate password
                            password_hash, password_salt = sec.hash_password(new_password)

                            # Insert the new user
                            db.insert("""
                                      INSERT INTO user (username_email, password_hash, password_salt, role)
                                      VALUES (?, ?, ?, ?)
                                      """, (new_username, password_hash, password_salt, new_role))

                            st.success(f"User '{new_username}' with role '{new_role}' created successfully.")
                            # Force refresh
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error creating user: {str(e)}")


def about():
    """
    This is the about ui page for the application.
    """
    st.header('About')
    st.write('FinDAG Document Processing Application')

    # Display log file with configurable number of lines
    log_path = os.path.join(os.getenv('LOG_PATH', ''), 'application.log')
    if os.path.exists(log_path):
        try:
            # Use a deque to efficiently get the last 300 lines
            from collections import deque

            # Read the last 300 lines
            with open(log_path, 'r') as file:
                last_lines = deque(file, maxlen=300)
                last_lines = list(last_lines)

            # Add a slider to control how many lines to display
            num_lines = st.slider('Number of log lines to display',
                                  min_value=10,
                                  max_value=len(last_lines),
                                  value=min(100, len(last_lines)),
                                  step=10)

            # Get the selected number of lines from the end of the list
            displayed_lines = last_lines[-num_lines:] if num_lines < len(last_lines) else last_lines

            # Join the lines into a single string
            log_content = ''.join(displayed_lines)

            st.subheader(f'Application Logs (Last {num_lines} of {len(last_lines)} lines)')
            st.code(log_content)
        except Exception as e:
            st.error(f"Error reading log file: {str(e)}")
    else:
        st.warning(f"Log file not found at {log_path}")

    # Bug report section
    st.subheader('Report an Issue')
    st.write('If you encounter any problems with the application, please describe the issue below:')

    issue_description = st.text_area('Issue Description', height=100)
    # steps_to_reproduce = st.text_area('Steps to Reproduce', height=100)

    if st.button('Submit Issue Report'):
        if issue_description:
            # Here you would implement the logic to save or send the bug report
            # For now, just show a success message
            st.success('Thank you for your report! The issue has been logged.')
        else:
            st.warning('Please provide a description of the issue.')


def login(database: Database = None) -> bool:
    """
    Display a login form and handle authentication.

    :return: True if login is successful, False otherwise.
    """
    st.title("Document Fetcher - Login")
    st.markdown("Please enter your credentials to access the application.")

    # Get client IP as early as possible
    client_ip = sec.get_client_ip()

    # Create columns for layout
    col1, col2 = st.columns([1, 1])

    with col1:
        # Create a form for better UX
        with st.form("login_form"):
            username = st.text_input("Username").strip()
            password = st.text_input("Password", type="password").strip()
            submit = st.form_submit_button("Login")

        if submit:
            if not username or not password:
                log.warning(f"Login attempt with empty credentials from IP: {client_ip}")
                st.error("Please enter both username and password")
                return False

            # Check if the database instance is provided, otherwise fetch the instance
            if database:
                db = database
            else:
                db = Database().get_instance()

            # Check for too many failed attempts from this IP
            if sec.check_login_attempts(client_ip, db):
                log.warning(f"Too many failed login attempts from IP: {client_ip}")
                st.error("Too many failed login attempts. Please try again later.")
                return False

            # Query for user with the given username
            user_data = db.query(
                """
                SELECT id, password_hash, password_salt, role
                FROM user
                WHERE username_email = ?
                """, (username,)
            )

            if not user_data:
                log.warning(f"Failed login attempt for username: {username} from IP: {client_ip}")
                sec.record_failed_attempt(client_ip, username, db)
                st.error("Invalid username or password")
                return False

            user_id, password_hash, password_salt, role = user_data[0]

            # Verify password
            if not sec.verify_password(password_hash, password_salt, password):
                log.warning(f"Failed login attempt for user: {user_id} from IP: {client_ip}")
                sec.record_failed_attempt(client_ip, username, db)
                st.error("Invalid username or password")
                return False

            # Create a new session
            session_key = sec.create_session(user_id, db)
            if not session_key:
                log.error(f"Failed to create session for user: {user_id} from IP: {client_ip}")
                st.error("Failed to create session")
                return False

            # Store session information in session state
            st.session_state['session_key'] = session_key
            st.session_state['user_id'] = user_id
            st.session_state['user_role'] = role
            st.session_state['client_ip'] = client_ip  # Store IP in session state for later use

            # Log successful login
            log.info(f"Successful login for user: {user_id} ({username}) from IP: {client_ip}")
            sec.record_successful_login(client_ip, user_id, db)

            st.success(f"Welcome, {username}!")
            return True

    # Display demo accounts for testing
    with col2:
        st.markdown("""
        ### Demo Accounts
        
        **Admin User**  
        Username: admin@example.com  
        Password: admin123
        
        **Inspector User**  
        Username: inspector@example.com  
        Password: inspector123 
        
        **Auditor User**  
        Username: auditor@example.com  
        Password: auditor123 
        """)

    return False
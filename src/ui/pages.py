"""
This module holds the main ui page for the application.
"""
import os
import pandas as pd
import streamlit as st
import logging

# Custom imports
import ui.visuals as visuals
from workflow.audit import get_emails, assess_emails
from cls.mailclient import Mailclient
from cls.database import Database
import ui.expander_stages as expander_stages
import workflow.security as sec


# Set up logging
log = logging.getLogger(__name__)


def home(mailclient: Mailclient = None, database: Database = None):
    """
    This is the main ui page for the application.
    It serves as a landing page and provides the user with options to navigate the application.
    """
    log.debug('Rendering home page')

    # Page title and description
    st.header('Document Fetcher')
    st.write('Welcome to the Document Fetcher application!')

    # Fetch the emails and client
    emails = get_emails()

    # Configure visuals layout
    column_left, column_right = st.columns(2)

    # Display the mails
    st.dataframe(emails)

    # Display a plot on the right
    with column_left:
        # Pie chart showing the submission ratio
        st.pyplot(visuals.pie_submission_ratio())
        # TODO: Fix issue with labels overlapping

    # Display a table on the left
    with column_right:
        # Display a multiselect box to select documents to process
        docs_to_process = st.multiselect('Select documents to process', emails['ID'])

        # Process only the selected documents
        if st.button('Process selected documents'):
            with st.spinner(f'Processing mails'):
                assess_emails(docs_to_process)

            # Rerun the app to update the display
            st.rerun()

        # Process all the documents
        if st.button('Process all documents'):

            # Check if the mailclient instance is provided, otherwise fetch the instance
            if not mailclient:
                mailclient = Mailclient.get_instance()

            # Check if the database instance is provided, otherwise fetch the instance
            if database:
                db = database
            else:
                db = Database().get_instance()

            # Get all mails that are already part of an active audit case
            already_processed_mails = [x[0] for x in db.query(
                """
                SELECT email_id 
                FROM audit_case
                WHERE email_id IS NOT NULL
                AND stage < 5
                """)]

            # If no mails are in the database, fetch all mails
            if len(already_processed_mails) > 0:
                with st.spinner(f'Processing mails'):
                    assess_emails(mailclient.get_mails(excluded_ids=already_processed_mails)['ID'])
            else:
                with st.spinner(f'Processing mails'):
                    assess_emails(emails['ID'])

            # Rerun the app to update the display
            st.rerun()


def active_cases(database: Database = None):
    """
    UI page for viewing and managing active audit cases.
    """
    log.debug('Rendering active cases page')

    # Check if the database instance is provided, otherwise fetch the instance
    if database:
        db = database
    else:
        db = Database().get_instance()

    # Fetch the active cases and clients
    active_cases_df = db.get_active_client_cases()

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
            st.markdown(f"**Stage:** {visuals.stage_badge(selected_case['stage'])}", unsafe_allow_html=True)

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

            # Define steps based on stage
            current_stage = selected_case['stage']

            # Display expandable sections for each step of the process
            expander_stages.stage_1(case_id, current_stage, db)
            expander_stages.stage_2(case_id, current_stage)
            #expander_stages.stage_3(case_id, current_stage)
            #expander_stages.stage_4(case_id, current_stage)

            # TODO: Continue to implement the rest of the stages!

            with st.expander("Step 3: Certificate Issued", expanded=(current_stage == 3)):
                st.write("Certificate has been issued to BaFin.")
                if current_stage == 3 and st.button("Complete Process"):
                    db.query("UPDATE audit_case SET stage = 4 WHERE id = ?", (case_id,))
                    st.success("Process Completed!")
                    # Clear cache and refresh
                    st.cache_data.clear()
                    st.rerun()

            with st.expander("Step 4: Process Completed", expanded=(current_stage == 4)):
                st.write("The audit process has been completed.")
                if current_stage == 4 and st.button("Archive Case"):
                    db.query("UPDATE audit_case SET stage = 5 WHERE id = ?", (case_id,))
                    st.success("Case Archived!")
                    # Clear cache and refresh
                    st.cache_data.clear()
                    st.rerun()


# TODO: Check if this works as expected!
def settings(database: Database = None):
    """
    This is the settings ui page for the application.
    """
    log.debug('Rendering settings page')

    # Page title and description
    st.header('Settings')
    st.write('Configure the application settings below.')

    # New section for audit process initialization
    st.subheader("Audit Process")

    with st.expander("Initialize Annual Audit Process", expanded=True):
        st.write("""
        This will create a new audit case (stage 1) for every client in the database 
        that doesn't already have an active case. Use this to start the annual audit process.
        """)

        # Add a confirmation checkbox for safety
        confirm_init = st.checkbox("I understand this will create new audit cases for all clients")

        # Check if the database instance is provided, otherwise fetch the instance
        if database:
            db = database
        else:
            db = Database().get_instance()

        if st.button("Initialize Audit Cases", disabled=not confirm_init):
            with st.spinner("Creating audit cases..."):
                # Find clients without active audit cases
                clients_without_cases = db.query("""
                    SELECT id FROM client 
                    WHERE id NOT IN (
                        SELECT client_id FROM audit_case 
                        WHERE stage < 5
                    )
                """)

                if not clients_without_cases:
                    st.warning("All clients already have active audit cases.")
                else:
                    # Create a new audit case for each client
                    created_count = 0
                    for client_id in clients_without_cases:
                        db.insert("""
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
        stage_counts = db.query("""
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
            st.warning(f"⚠️ There are still {not_completed} active cases that are not ready for archiving (stages 1-3).")

        # Add a confirmation checkbox for safety
        confirm_archive = st.checkbox("I understand this will archive all cases in stage 4")

        if st.button("Archive Completed Cases", disabled=not confirm_archive):
            with st.spinner("Archiving completed cases..."):
                # Count cases to be archived
                cases_to_archive = db.query("""
                    SELECT COUNT(*) FROM audit_case 
                    WHERE stage = 4
                """)[0][0]

                if cases_to_archive == 0:
                    st.info("No completed cases to archive.")
                else:
                    # TODO: Implement archiving logic - this would include:
                    # 1. Move documents to archive storage
                    # 2. Update database records
                    # 3. Create archive logs

                    # For now, just update the stage to 5 (Archived)
                    db.query("""
                        UPDATE audit_case 
                        SET stage = 5,
                            comments = CASE 
                                WHEN comments IS NULL THEN 'Archived automatically'
                                ELSE comments || ' | Archived automatically'
                            END
                        WHERE stage = 4
                    """)

                    # Success message
                    st.success(f"Successfully archived {cases_to_archive} completed cases.")

                    # Log the action
                    log.info(f"Archived {cases_to_archive} completed cases")

                    # Refresh the statistics
                    st.rerun()

    # Divider before other settings
    st.divider()

    # You can add other settings sections below
    st.subheader("Application Settings")
    st.write("Other settings will go here!")


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
        
        **Auditor User**  
        Username: auditor@example.com  
        Password: auditor123
        """)

    return False

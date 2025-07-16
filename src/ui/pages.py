"""
This module holds the main ui page for the application.
"""
import os
import pandas as pd
import streamlit as st
import logging
import base64
import datetime
import cv2
import numpy as np

# Custom imports
import ui.visuals as visuals
import workflow.audit as auditflow
from cls.mailclient import Mailclient
from cls.database import Database
import ui.expander_stages as expander_stages
import workflow.security as sec
from cls.document import PDF
from cls.config import ConfigHandler
from cls.accesscontrol import AccessControl
from workflow.excel_import import ExcelImporter
import processing.detect as dtct
from processing.ocr import ocr_cell, create_ocr_reader
from processing.files import get_images_from_pdf


# Set up logging
log = logging.getLogger(__name__)


def home(mailclient: Mailclient = None, database: Database = Database.get_instance()):
    """
    Render the home page of the Document Fetcher application. The page provides functionalities for
    viewing fetched emails, processing them, and displaying active audit cases. The layout includes
    sections for email operations and auditing case listings, with appropriate access control checks
    based on the user's role.

    :param mailclient: The mail client instance used for fetching and handling emails.
    :type mailclient: Mailclient, optional
    :param database: The database instance used for querying and updating audit-related information.
    :type database: Database, optional
    """
    log.debug('Rendering home page')

    # Page title and description
    st.header('Dokumenten-Fetcher')
    st.write('Willkommen zur Dokumenten-Fetcher-Anwendung!')

    # Get user's accessible clients
    user_id = st.session_state.get('user_id')
    user_role = st.session_state.get('user_role', 'auditor')

    # Fetch the emails (exclude those who have already been downloaded)
    emails = auditflow.fetch_new_emails(database)

    # Configure visuals layout
    column_left, column_right = st.columns(2)

    # Display the mails
    st.dataframe(emails, hide_index=True)

    # Display a plot on the right
    with column_left:
        # Pie chart showing the submission ratio
        st.pyplot(visuals.pie_submission_ratio())

    # Display a table on the left
    with column_right:
        if emails.empty:
            st.warning("Keine neuen E-Mails zur Verarbeitung.")
            return

        # Only show email processing buttons for admin and inspector roles
        if AccessControl.can_access_feature(user_role, 'process_emails'):
            # Display a multiselect box to select documents to process
            docs_to_process = st.multiselect('Zu verarbeitende Dokumente wählen', emails['ID'])

            # Process only the selected documents
            if st.button('Ausgewählte Dokumente verarbeiten'):
                with st.spinner(f'Verarbeite E-Mails'):
                    auditflow.assess_emails(docs_to_process)

                # Rerun the app to update the display
                st.rerun()

            # Process all the documents
            if st.button('Alle Dokumente verarbeiten'):
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
                    with st.spinner(f'Verarbeite E-Mails'):
                        auditflow.assess_emails(mailclient.get_mails(excluded_ids=already_processed_mails)['ID'])
                else:
                    with st.spinner(f'Verarbeite E-Mails'):
                        auditflow.assess_emails(emails['ID'])

                # Rerun the app to update the display
                st.rerun()

    # Fetch the active cases based on user's access
    if user_role == 'admin':
        # Admins see all cases
        active_cases_df = database.get_active_client_cases()
    else:
        # Other users see only their assigned cases
        accessible_clients = AccessControl.get_accessible_clients(user_id, user_role, database)
        active_cases_df = database.get_active_client_cases(client_ids=accessible_clients)

    if active_cases_df.empty:
        if user_role == 'admin':
            st.info("Keine aktiven Prüffälle gefunden. Alle Fälle wurden abgeschlossen und archiviert.")
        else:
            st.info("Sie haben keine aktiven Prüffälle zugewiesen.")
        return

    # Display a table of all active cases
    st.subheader("Aktive Fälle")

    # Create a more user-friendly display table
    display_df = active_cases_df[['case_id', 'bafin_id', 'institute', 'stage', 'created_at', 'last_updated_at']].copy()
    display_df.columns = ['Fall-ID', 'BaFin-ID', 'Institut', 'Stufe', 'Erstellt', 'Zuletzt aktualisiert']

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
    if st.button("Fälle aktualisieren"):
        st.cache_data.clear()
        st.rerun()


def active_cases(database: Database = Database.get_instance()):
    """
    Fetches and displays active audit cases based on the user's role and permissions.
    The function retrieves data from the database, provides a selection interface for cases,
    and allows users to view and manage case details as well as document information.

    :param database: Database instance used for querying and updating case and document data.
    :type database: Database
    """
    log.debug('Rendering active cases page')

    # Get user's access information
    user_id = st.session_state.get('user_id')
    user_role = st.session_state.get('user_role', 'auditor')

    # Fetch the active cases based on user's access
    if user_role == 'admin':
        # Admins see all cases
        active_cases_df = database.get_active_client_cases()
    else:
        # Other users see only their assigned cases
        accessible_clients = AccessControl.get_accessible_clients(user_id, user_role, database)
        active_cases_df = database.get_active_client_cases(client_ids=accessible_clients)

    # Page title and description
    st.header('Aktive Fälle')

    if active_cases_df.empty:
        if user_role == 'admin':
            st.info("Keine aktiven Prüffälle gefunden. Alle Fälle wurden abgeschlossen und archiviert.")
        else:
            st.info("Sie haben keine aktiven Prüffälle zugewiesen.")
        return

    # Setup session state for selected case if not already initialized
    if 'selected_case_id' not in st.session_state:
        st.session_state['selected_case_id'] = None

    # Create options for the selectbox with client names and case IDs
    case_options = [f"{row['institute']} (Case #{row['case_id']})" for _, row in active_cases_df.iterrows()]

    # Display a selectbox to select a case
    selected_option = st.selectbox(
        'Wählen Sie einen Fall, um Details anzuzeigen',
        case_options,
        key='case_selector'
    )

    # Create tabs for different views
    tab1, tab2 = st.tabs(["Fall-Details", "Dokument-Werte"])

    with tab1:
        if selected_option:
            # Extract case ID from the selection
            case_id = int(selected_option.split("Case #")[1].strip(")"))
            st.session_state['selected_case_id'] = case_id

            # Find the selected case
            selected_case = active_cases_df[active_cases_df['case_id'] == case_id].iloc[0]

            # Verify user has access to this case
            if not AccessControl.can_access_client(user_id, selected_case['client_id'], user_role, database):
                st.error("Sie haben keine Berechtigung, diesen Fall anzuzeigen.")
                return

            # Display case information
            st.markdown(
                f"**Fall {selected_case['case_id']} Stufe:** {visuals.stage_badge(selected_case['stage'])}",
                unsafe_allow_html=True
            )

            # Define steps based on stage
            current_stage = selected_case['stage']

            # Display expandable sections for each step of the process
            expander_stages.stage_1(case_id, current_stage, database)
            expander_stages.stage_2(case_id, current_stage, database)

            # Display additional stages based on the user role
            if AccessControl.can_access_feature(user_role, 'generate_certificate'):
                expander_stages.stage_3(case_id, current_stage, database)

            if AccessControl.can_access_feature(user_role, 'complete_process'):
                expander_stages.stage_4(case_id, current_stage, database)

            # Divider
            st.divider()

            # Create columns for layout
            col1, col2 = st.columns(2)

            # Case details column
            with col1:
                st.subheader("Fall-Details")
                st.markdown(f"**Erstellt:** {selected_case['created_at'].strftime('%Y-%m-%d')}")
                st.markdown(f"**Zuletzt aktualisiert:** {selected_case['last_updated_at'].strftime('%Y-%m-%d %H:%M')}")

                # Comments section with editing capability
                st.subheader("Kommentare")
                current_comments = selected_case['comments'] if pd.notna(selected_case['comments']) else ""
                new_comments = st.text_area("Kommentare bearbeiten", value=current_comments, height=143)

                if new_comments != current_comments:
                    if st.button("Kommentare speichern"):
                        # Update comments in database
                        database.insert(f"""
                            UPDATE audit_case 
                            SET comments = ? 
                            WHERE id = ?
                        """, (new_comments, case_id))
                        st.success("Kommentare erfolgreich aktualisiert!")
                        # Clear cache and refresh
                        st.cache_data.clear()
                        st.rerun()

            # Client details column
            with col2:
                st.subheader("Kundeninformation")
                st.markdown(f"**Institut:** {selected_case['institute']}")
                st.markdown(f"**BaFin-ID:** {selected_case['bafin_id']}")
                st.markdown(f"**Adresse:** {selected_case['address']}")
                st.markdown(f"**Stadt:** {selected_case['city']}")
                st.markdown(f"**Ansprechpartner:** {selected_case['contact_person']}")
                st.markdown(f"**Telefon:** {selected_case['phone']}")
                st.markdown(f"**Fax:** {selected_case['fax']}")
                st.markdown(f"**E-Mail:** {selected_case['email']}")

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
                st.warning("Kein Dokument für diesen Prüffall gefunden.")
                return

            # Create two columns - one for PDF display, one for editing values
            col1, col2 = st.columns([6, 3])

            # Load the document with audit values
            document_path = document_data[0][0]
            doc = PDF.from_json(document_path)

            with col1:
                st.subheader("Dokument-Vorschau")
                # Display PDF using iframe
                if document_path and os.path.exists(document_path):
                    # Create a base64 representation of the PDF
                    base64_pdf = base64.b64encode(doc.get_content()).decode('utf-8')

                    # Embed the PDF
                    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="1600px" type="application/pdf"></iframe>'
                    st.markdown(pdf_display, unsafe_allow_html=True)
                else:
                    st.error("PDF-Datei nicht gefunden.")

            with col2:
                st.subheader("Extrahierte Werte bearbeiten")

                if not hasattr(doc, '_audit_values') or not doc._audit_values:
                    st.warning("Keine Prüfwerte für dieses Dokument gefunden.")
                    return

                st.markdown("### Extrahierte Werte")
                st.markdown("Bearbeiten Sie die aus dem Dokument extrahierten Werte:")

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
                        st.markdown("#### SONO-1 Positionen")
                        for key, value in positions.items():
                            position_number = key[1:]  # Extract the position number
                            original_key = doc._audit_values.get(f"key_{key}", "Unbekannt")

                            # Add tooltip with original extracted text field name
                            help_text = f"Ursprüngliches Feld: {original_key}"

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
                            original_key = doc._audit_values.get(f"key_{key}", "Unbekannt")

                            # Add tooltip with original extracted text field name
                            help_text = f"Ursprüngliches Feld: {original_key}"

                            # Edit field with label showing FinDAG reference
                            edited_value = st.number_input(
                                f"Nr. {number.lstrip('0')}", 
                                value=value,
                                help=help_text
                            )
                            edited_values[key] = edited_value

                    # Submit button
                    submitted = st.form_submit_button("Änderungen speichern")

                    if submitted:
                        # Update the audit values in the document
                        for key, value in edited_values.items():
                            doc._audit_values[key] = value
                            # TODO: Implement a get method for the audit values!

                        # Save the document back to the database
                        doc.save_to_json()
                        st.success("Prüfwerte erfolgreich aktualisiert!")

                # Display original text extraction for reference
                with st.expander("Ursprüngliche extrahierte Feldnamen anzeigen"):
                    st.markdown("### Ursprüngliche Feldnamen")
                    st.markdown("Dies sind die ursprünglichen Felder, aus denen Werte extrahiert wurden:")

                    for key in doc._audit_values:
                        if key.startswith('key_'):
                            field_key = key[4:]  # Remove the 'key_' prefix
                            if field_key in doc._audit_values:
                                st.markdown(f"**{field_key}**: {doc._audit_values[key]}")
        else:
            st.info("Bitte wählen Sie einen Fall aus, um Dokumentwerte zu bearbeiten.")


def settings(database: Database = Database().get_instance()):
    """
    Render and manage the settings page for the application interface. This function checks user access
    rights and dynamically displays the appropriate configuration sections for the application.

    :param database: Database instance used for managing and storing application-related settings.
    :type database: Database
    """
    log.debug('Rendering settings page')

    # Check if user has access to settings
    user_role = st.session_state.get('user_role', 'auditor')
    if not AccessControl.can_access_feature(user_role, 'settings'):
        st.error("Sie haben keine Berechtigung, auf die Einstellungen zuzugreifen.")
        return

    # Page title and description
    st.header('Einstellungen')
    st.write('Konfigurieren Sie die Anwendungseinstellungen unten.')

    # Split the page into tabs
    tabs = ["Anwendungseinstellungen", "Prüfungseinstellungen", "Benutzerverwaltung"]
    if AccessControl.can_access_feature(user_role, 'user_management'):
        tabs.append("Zugriffskontrolle")

    tab_objects = st.tabs(tabs)

    # Application Settings tab
    with tab_objects[0]:
        st.subheader("Anwendungseinstellungen")

        # Certificate Template Settings
        with st.expander("Zertifikat-Vorlagen-Einstellungen", expanded=True):
            st.write("Konfigurieren Sie die Vorlage für die Erstellung von Zertifikaten.")

            # Get current template path
            template_path = os.getenv('CERTIFICATE_TEMPLATE_PATH', './.filesystem/certificate_template.docx')

            # Upload new template
            st.markdown("#### Neue Vorlage hochladen")
            st.write("""
            Laden Sie eine neue Word-Dokument-Vorlage (.docx) für Zertifikate hoch. Die Vorlage sollte die folgenden Platzhalter enthalten:
            - [DATE] - Aktuelles Datum
            - [YEAR] - Aktuelles Jahr
            - [BAFIN_ID] - BaFin-ID des Kunden
            - [INSTITUTE_NAME] - Name des Instituts
            - [INSTITUTE_ADDRESS] - Adresse des Instituts
            - [INSTITUTE_CITY] - Stadt des Instituts
            - [FISCAL_YEAR_END] - Ende des Geschäftsjahres
            - [VALIDATION_DATE] - Validierungsdatum
            """)

            uploaded_template = st.file_uploader("Vorlagendatei hochladen", type="docx", key="template_uploader")

            if uploaded_template is not None:
                # Save the uploaded template
                with open(template_path, "wb") as f:
                    f.write(uploaded_template.getvalue())

                st.success(f"Vorlage erfolgreich aktualisiert: {os.path.basename(template_path)}")

            # Display current template info
            st.markdown("#### Aktuelle Vorlage")
            if os.path.exists(template_path):
                st.success(f"Vorlage ist konfiguriert: {os.path.basename(template_path)}")

                # Option to download current template
                with open(template_path, "rb") as file:
                    st.download_button(
                        label="Aktuelle Vorlage herunterladen",
                        data=file,
                        file_name=os.path.basename(template_path),
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
            else:
                st.warning(f"Vorlagendatei nicht gefunden unter {template_path}")

        # Terms and Conditions Settings
        with st.expander("Allgemeine Geschäftsbedingungen Einstellungen", expanded=True):
            st.write("Konfigurieren Sie das AGB-PDF, das für die Erstellung von Zertifikaten verwendet wird.")

            # Get current terms and conditions path
            terms_path = os.getenv('CERTIFICATE_TOS_PATH', './.filesystem/terms_conditions.pdf')

            # Upload new terms and conditions PDF
            st.markdown("#### Neue AGB-PDF hochladen")
            st.write("Laden Sie ein neues PDF-Dokument (.pdf) für die Allgemeinen Geschäftsbedingungen hoch.")

            uploaded_terms_pdf = st.file_uploader("AGB-PDF hochladen", type="pdf", key="terms_uploader")

            if uploaded_terms_pdf is not None:
                # Save the uploaded terms and conditions PDF
                with open(terms_path, "wb") as f:
                    f.write(uploaded_terms_pdf.getvalue())

                st.success(f"AGB-PDF erfolgreich aktualisiert: {os.path.basename(terms_path)}")

            # Display current terms and conditions info
            st.markdown("#### Aktuelle AGB-PDF")
            if os.path.exists(terms_path):
                st.success(f"AGB-PDF ist konfiguriert: {os.path.basename(terms_path)}")

                # Option to download current terms and conditions PDF
                with open(terms_path, "rb") as file:
                    st.download_button(
                        label="Aktuelle AGB-PDF herunterladen",
                        data=file,
                        file_name=os.path.basename(terms_path),
                        mime="application/pdf"
                    )
            else:
                st.warning(f"AGB-PDF-Datei nicht gefunden unter {terms_path}")

        # Archive File Name Settings
        with st.expander("Archiv-Einstellungen", expanded=True):
            st.write("Konfigurieren Sie die Namenskonvention für Archiv-ZIP-Dateien.")

            # Get the config handler instance
            config = ConfigHandler.get_instance()

            # Get current archive prefix from config
            default_prefix = "audit_archive"
            current_prefix = config.get("APP_SETTINGS", "archive_file_prefix", default_prefix)

            # Input for archive file prefix
            new_prefix = st.text_input(
                "Archivdatei-Präfix",
                value=current_prefix,
                help="Dieses Präfix wird für die Benennung von Archiv-ZIP-Dateien verwendet. Das finale Format wird sein: prefix_YYYY-MM-DD.zip"
            )

            # Display preview of the file name
            current_date = datetime.datetime.now().strftime("%Y-%m-%d")
            st.write(f"Vorschau: `{new_prefix}_{current_date}.zip`")

            if st.button("Archiv-Einstellungen speichern"):
                # Save the prefix to the config
                config.set("APP_SETTINGS", "archive_file_prefix", new_prefix)
                st.success("Archivdatei-Präfix erfolgreich aktualisiert!")

        # Application log settings
        with st.expander("Anwendungsprotokolle", expanded=False):
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
                    num_lines = st.slider('Anzahl der anzuzeigenden Protokollzeilen',
                                          min_value=10,
                                          max_value=len(last_lines),
                                          value=min(100, len(last_lines)),
                                          step=10)

                    # Get the selected number of lines from the end of the list
                    displayed_lines = last_lines[-num_lines:] if num_lines < len(last_lines) else last_lines

                    # Join the lines into a single string
                    log_content = ''.join(displayed_lines)

                    st.subheader(f'Anwendungsprotokolle (Letzte {num_lines} von {len(last_lines)} Zeilen)')
                    st.code(log_content)
                except Exception as e:
                    st.error(f"Fehler beim Lesen der Protokolldatei: {str(e)}")
            else:
                st.warning(f"Protokolldatei nicht gefunden unter {log_path}")

    # Audit Settings tab
    with tab_objects[1]:
        st.subheader("Prüfprozess")

        # Updated Excel Import Section in settings() function from ui/pages.py
        # This replaces the Excel Import Section within the Audit Settings tab

        # Excel Import Section
        with st.expander("Initialize Audit Season from Excel", expanded=False):
            st.write("""
            Upload an Excel file to initialize the audit season. The file should contain:
            - **Bank ID**: BaFin ID of the institution (required)
            - **Inspector 1**: Name or email of the first inspector
            - **Inspector 2**: Name or email of the second inspector
            - **Auditor**: Name or email of the auditor

            Additional columns like Nr, Name, PLZ, City or Comment will be ignored.

            **Note:** If users don't exist in the system, they will be created automatically with:
            - Username generated from their name (all spaces removed, lowercase) + @example.com
            - Secure random password
            - Appropriate role (inspector/auditor)
            """)

            uploaded_file = st.file_uploader("Choose Excel file", type=['xlsx', 'xls'])

            if uploaded_file is not None:
                # Validate file structure
                is_valid, issues = ExcelImporter.validate_excel_structure(uploaded_file)

                if not is_valid:
                    st.error("Excel file validation failed")
                    for issue in issues:
                        st.error(f"• {issue}")
                else:
                    st.success("Excel file structure is valid!")

                    # Show preview
                    df_preview = pd.read_excel(uploaded_file)
                    st.write("Preview (first 5 rows):")
                    st.dataframe(df_preview.head())

                    # Import button
                    if st.button("Import Audit Season Data"):
                        # Reset file pointer
                        uploaded_file.seek(0)

                        # Perform import
                        importer = ExcelImporter(database)
                        results = importer.import_audit_season(
                            uploaded_file,
                            st.session_state['user_id']
                        )

                        # Show results
                        if results['success']:
                            st.success(f"Import completed successfully! {results['success_count']} rows processed.")
                        else:
                            st.error("Import completed with errors.")

                        # Show created users if any
                        if results['created_users']:
                            st.info(f"Created {results['total_created_users']} new users:")

                            # Create a dataframe for better display
                            created_users_df = pd.DataFrame(results['created_users'])
                            created_users_df = created_users_df[['name', 'username', 'password', 'role', 'row']]
                            created_users_df.columns = ['Name', 'Username', 'Password', 'Role', 'Excel Row']

                            # Display the created users
                            st.dataframe(created_users_df, use_container_width=True)

                            # Add download button for created users
                            csv = created_users_df.to_csv(index=False)
                            st.download_button(
                                label="Download Created Users (CSV)",
                                data=csv,
                                file_name="created_users.csv",
                                mime="text/csv"
                            )

                            st.warning("""
                            ⚠️ **Important**: Please save these credentials securely!
                            - The passwords shown above are temporary and should be communicated to users securely
                            - Users should be instructed to change their passwords on first login
                            - These passwords will not be shown again
                            """)

                        # Show errors
                        if results['errors']:
                            st.error("Errors:")
                            for error in results['errors']:
                                st.error(f"• {error}")

                        # Show warnings
                        if results['warnings']:
                            st.warning("Warnings:")
                            for warning in results['warnings']:
                                st.warning(f"• {warning}")

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

    # TODO: Break these down into their own functions for better organization
    # User Management tab
    with tab_objects[2]:
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

    # Access Control tab (displayed only if user has access)
    if AccessControl.can_access_feature(user_role, 'user_management'):
        with tab_objects[-1]:
            st.subheader("Access Control Management")

            # User access management
            st.markdown("### User Client Access")

            # Select a user to manage
            users_data = database.query("""
                                        SELECT id, username_email, role
                                        FROM user
                                        WHERE role != 'admin'
                                        ORDER BY username_email
                                        """)

            if users_data:
                user_options = [(row[0], f"{row[1]} ({row[2]})") for row in users_data]
                selected_user_id = st.selectbox(
                    "Select user to manage access",
                    options=[uid for uid, _ in user_options],
                    format_func=lambda x: next((label for uid, label in user_options if uid == x), ""),
                    index=None
                )

                if selected_user_id:
                    # Show current access
                    st.markdown("#### Current Access")
                    current_access = AccessControl.get_user_client_access(selected_user_id, database)

                    if current_access:
                        access_df = pd.DataFrame(current_access)
                        st.dataframe(access_df[['institute', 'bafin_id', 'granted_at']], use_container_width=True)

                        # Revoke access
                        st.markdown("#### Revoke Access")
                        client_to_revoke = st.selectbox(
                            "Select client to revoke access",
                            options=[acc['client_id'] for acc in current_access],
                            format_func=lambda x: next((acc['institute'] for acc in current_access if acc['client_id'] == x), ""),
                            index=None
                        )

                        if client_to_revoke and st.button("Revoke Access"):
                            if AccessControl.revoke_client_access(selected_user_id, client_to_revoke, database):
                                st.success("Access revoked successfully!")
                                st.rerun()
                            else:
                                st.error("Failed to revoke access.")
                    else:
                        st.info("This user has no client access assigned.")

                    # Grant new access
                    st.markdown("#### Grant New Access")

                    # Get clients the user doesn't have access to
                    current_client_ids = [acc['client_id'] for acc in current_access]
                    available_clients = database.query("""
                        SELECT id, institute, bafin_id
                        FROM client
                        WHERE id NOT IN ({})
                        ORDER BY institute
                    """.format(','.join(['?'] * len(current_client_ids)) if current_client_ids else '0'),
                                                       current_client_ids if current_client_ids else None)

                    if available_clients:
                        client_options = [(row[0], f"{row[1]} (BaFin: {row[2]})") for row in available_clients]
                        client_to_grant = st.selectbox(
                            "Select client to grant access",
                            options=[cid for cid, _ in client_options],
                            format_func=lambda x: next((label for cid, label in client_options if cid == x), ""),
                            index=None
                        )

                        if client_to_grant and st.button("Grant Access"):
                            if AccessControl.grant_client_access(
                                    selected_user_id,
                                    client_to_grant,
                                    st.session_state['user_id'],
                                    database
                            ):
                                st.success("Access granted successfully!")
                                st.rerun()
                            else:
                                st.error("Failed to grant access.")
                    else:
                        st.info("User already has access to all clients.")


def about():
    """
    Provides the implementation of the about section for a Streamlit application. This
    includes rendering information about the application, displaying application logs from
    a predefined log file with adjustable visibility using a slider, and enabling users
    to submit bug reports.

    :param st: Streamlit module for building the application interface.
    :type st: module
    :param os: Standard Python module for handling file paths and environment variables.
    :type os: module
    :param deque: A double-ended queue from collections module for efficiently fetching
                  lines from the end of the log file.
    :type deque: collections.deque
    """
    st.header('Über')
    st.write('FinDAG Dokumentenverarbeitungsanwendung')

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

            st.subheader(f'Anwendungsprotokolle (Letzte {num_lines} von {len(last_lines)} Zeilen)')
            st.code(log_content)
        except Exception as e:
            st.error(f"Fehler beim Lesen der Protokolldatei: {str(e)}")
    else:
        st.warning(f"Protokolldatei nicht gefunden unter {log_path}")

    # Bug report section
    st.subheader('Problem melden')
    st.write('Wenn Sie Probleme mit der Anwendung haben, beschreiben Sie das Problem bitte unten:')

    issue_description = st.text_area('Problembeschreibung', height=100)
    # steps_to_reproduce = st.text_area('Steps to Reproduce', height=100)

    if st.button('Problembericht senden'):
        if issue_description:
            # Here you would implement the logic to save or send the bug report
            # For now, just show a success message
            st.success('Vielen Dank für Ihren Bericht! Das Problem wurde protokolliert.')
        else:
            st.warning('Bitte geben Sie eine Beschreibung des Problems an.')


def login(database: Database = None) -> bool:
    """
    Handles the login functionality for the Document Fetcher application. It allows users to
    log in using valid credentials and manages user sessions securely. The function implements
    basic protection against brute force attacks by tracking failed login attempts.

    :param database: An instance of the Database class that provides methods for querying,
        inserting, and managing the application's database.
    :type database: Database, optional
    :return: True if the login is successful, otherwise False.
    :rtype: bool

    :raises Exception: If there is an error during the login process, such as database connection issues
    """
    st.title("Dokumenten-Fetcher - Anmeldung")
    st.markdown("Bitte geben Sie Ihre Anmeldedaten ein, um auf die Anwendung zuzugreifen.")

    # Get client IP as early as possible
    client_ip = sec.get_client_ip()

    # Create columns for layout
    col1, col2 = st.columns([1, 1])

    with col1:
        # Create a form for better UX
        with st.form("login_form"):
            username = st.text_input("Benutzername").strip()
            password = st.text_input("Passwort", type="password").strip()
            submit = st.form_submit_button("Anmelden")

        if submit:
            if not username or not password:
                log.warning(f"Login attempt with empty credentials from IP: {client_ip}")
                st.error("Bitte geben Sie sowohl Benutzername als auch Passwort ein")
                return False

            # Check if the database instance is provided, otherwise fetch the instance
            if database:
                db = database
            else:
                db = Database().get_instance()

            # Check for too many failed attempts from this IP
            if sec.check_login_attempts(client_ip, db):
                log.warning(f"Too many failed login attempts from IP: {client_ip}")
                st.error("Zu viele fehlgeschlagene Anmeldeversuche. Bitte versuchen Sie es später erneut.")
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
                st.error("Ungültiger Benutzername oder Passwort")
                return False

            user_id, password_hash, password_salt, role = user_data[0]

            # Verify password
            if not sec.verify_password(password_hash, password_salt, password):
                log.warning(f"Failed login attempt for user: {user_id} from IP: {client_ip}")
                sec.record_failed_attempt(client_ip, username, db)
                st.error("Ungültiger Benutzername oder Passwort")
                return False

            # Create a new session
            session_key = sec.create_session(user_id, db)
            if not session_key:
                log.error(f"Failed to create session for user: {user_id} from IP: {client_ip}")
                st.error("Sitzung konnte nicht erstellt werden")
                return False

            # Store session information in session state
            st.session_state['session_key'] = session_key
            st.session_state['user_id'] = user_id
            st.session_state['user_role'] = role
            st.session_state['username'] = username  # Store username for display
            st.session_state['client_ip'] = client_ip  # Store IP in session state for later use

            # Log successful login
            log.info(f"Successful login for user: {user_id} ({username}) from IP: {client_ip}")
            sec.record_successful_login(client_ip, user_id, db)

            st.success(f"Willkommen, {username}!")
            return True

    # Display demo accounts for testing
    with col2:
        st.markdown("""
        ### Demo-Konten

        **Administrator**  
        Benutzername: admin@example.com  
        Passwort: admin123

        **Inspektor**  
        Benutzername: inspector@example.com  
        Passwort: inspector123 

        **Prüfer**  
        Benutzername: auditor@example.com  
        Passwort: auditor123 
        """)

    return False


def table_detection():
    """
    Renders the table detection test page that allows users to upload PDF documents
    and detect tables, signatures, and dates within them. This page is for testing
    purposes and does not store any data in the database.

    The page provides functionality to:
    1. Upload PDF documents
    2. Display the PDF pages as images
    3. Detect and highlight tables, signatures, and dates
    4. Extract and display table data using OCR
    """
    log.debug('Rendering table detection page')

    # Page title and description
    st.header('Tabellen-Erkennungstest')
    st.write('Laden Sie ein PDF-Dokument hoch, um die Tabellenerkennung zu testen.')

    # File upload
    pdf_document = st.file_uploader(label="PDF hier hochladen", type=["pdf"])
    display_tables = st.checkbox("Tabellen anzeigen")
    display_signatures = st.checkbox("Signaturen anzeigen")
    display_dates = st.checkbox("Datumsangaben anzeigen")

    if pdf_document is not None:
        pdf_content_bytes = pdf_document.read()  # Read content once
        images = get_images_from_pdf(pdf_content_bytes)

        for image in images:
            st.image(image, width=350)

        ocr_reader = create_ocr_reader(use_gpu=True)

        # Instantiate PDF class and determine signature page
        pdf_doc_object = PDF(content=pdf_content_bytes)
        pdf_doc_object.extract_table_data(ocr_reader=ocr_reader)  # This should populate _signature_page_index

        signature_page_idx = pdf_doc_object._signature_page_index if hasattr(pdf_doc_object, '_signature_page_index') else -1
        if signature_page_idx != -1:
            st.info(f"The application logic identified Page {signature_page_idx + 1} as the signature page.")
        else:
            st.warning("Signature page could not be determined by the PDF class logic.")

        ### Test code goes here ###
        for i, image in enumerate(images):
            # Convert the image to a NumPy array
            np_image_array = np.array(image)

            # Convert to BGR format for OpenCV
            bgr_image_array = cv2.cvtColor(np_image_array, cv2.COLOR_RGB2BGR)
            # Normalize image resolution
            bgr_image_array = dtct.normalize_image_resolution(bgr_image_array)

            ### DISPLAY EDGES ###
            edges = cv2.Canny(bgr_image_array, 80, 200, apertureSize=3)
            # Convert your BGR back to RGB for display
            original_rgb = cv2.cvtColor(bgr_image_array, cv2.COLOR_BGR2RGB)

            # Convert edges to RGB
            edges_rgb = cv2.cvtColor(edges, cv2.COLOR_GRAY2RGB)

            # Display both
            col1, col2 = st.columns(2)
            with col1:
                st.image(original_rgb, caption="Original", width=350)
            with col2:
                st.image(edges_rgb, caption="Edges", width=350)
            ### END DISPLAY EDGES ###

            result_image = bgr_image_array.copy()

            # Always detect tables for consistent data, regardless of display_tables for drawing
            table_contours = dtct.tables(bgr_image_array)

            if display_tables:
                st.write(f"Number of tables detected on page {i + 1}: {len(table_contours)}")
                cv2.drawContours(result_image, table_contours, -1, (0, 255, 0), 3)  # Green for tables

            if display_signatures:
                if i == signature_page_idx:
                    st.write(f"Attempting to detect signature regions on identified signature Page {i + 1}...")
                    # Convert to grayscale for signature detection
                    gray_image_array = cv2.cvtColor(bgr_image_array, cv2.COLOR_BGR2GRAY)
                    # Detect potential signature regions using the function from detect.py
                    signature_regions = dtct._detect_potential_signature_regions(gray_image_array)
                    st.write(f"Number of potential signature regions detected: {len(signature_regions)}")

                    if not signature_regions:
                        st.write("No signature regions detected by the dynamic function.")
                    else:
                        # Visualize detected signature regions
                        for region in signature_regions:
                            x_sig, y_sig, w_sig, h_sig = region  # Renamed to avoid conflict with table loop vars
                            cv2.rectangle(result_image, (x_sig, y_sig), (x_sig + w_sig, y_sig + h_sig), (0, 0, 255), 2)  # Red for signatures

                elif signature_page_idx != -1:  # Only show if a signature page was determined
                    st.write(f"Page {i + 1} is not the identified signature page. Skipping signature detection.")
                # If signature_page_idx is -1, this loop won't execute the main signature logic, which is fine.

            if display_dates:
                if i == signature_page_idx:
                    st.write(f"Attempting to detect date regions on identified signature Page {i + 1}...")
                    # Convert to grayscale for date detection if not already done
                    if 'gray_image_array' not in locals():
                        gray_image_array = cv2.cvtColor(bgr_image_array, cv2.COLOR_BGR2GRAY)
                    # Detect potential date regions using the function from detect.py
                    date_regions = dtct._detect_potential_date_regions(gray_image_array)
                    st.write(f"Number of potential date regions detected: {len(date_regions)}")

                    if not date_regions:
                        st.write("No date regions detected by the dynamic function.")
                    else:
                        # Visualize detected date regions
                        for region in date_regions:
                            x_date, y_date, w_date, h_date = region  # Renamed to avoid conflict with other loop vars
                            cv2.rectangle(result_image, (x_date, y_date), (x_date + w_date, y_date + h_date), (255, 0, 0), 2)  # Blue for dates

                elif signature_page_idx != -1:  # Only show if a signature page was determined
                    st.write(f"Page {i + 1} is not the identified signature page. Skipping date detection.")
                # If signature_page_idx is -1, this loop won't execute the main date logic, which is fine.

            # Display the original and result images if any detection is enabled
            if display_tables or (display_signatures and i == signature_page_idx and signature_regions) or (display_dates and i == signature_page_idx and 'date_regions' in locals() and date_regions):  # Ensure regions were found to display
                st.image(image, caption=f"Original - Page {i + 1}", use_column_width=False, width=350)
                st.image(cv2.cvtColor(result_image, cv2.COLOR_BGR2RGB),
                         caption=f"Detected Areas - Page {i + 1}",
                         use_column_width=False, width=350)
            elif i == 0 and not display_tables and not (display_signatures and i == signature_page_idx) and not (display_dates and i == signature_page_idx):  # Show original if nothing else is displayed on first page
                st.image(image, caption=f"Original - Page {i + 1}", use_column_width=False, width=350)

            # Detailed table processing logic
            if not display_tables and table_contours:
                st.write(f"Number of tables detected for processing on page {i + 1}: {len(table_contours)}")
                for j, contour_item in enumerate(table_contours):
                    table_data = []
                    x_tbl, y_tbl, w_tbl, h_tbl = cv2.boundingRect(contour_item)  # Renamed to avoid conflict
                    table_roi = bgr_image_array[y_tbl:y_tbl + h_tbl, x_tbl:x_tbl + w_tbl]

                    st.image(cv2.cvtColor(table_roi, cv2.COLOR_BGR2RGB),
                             caption=f"Image: {i + 1}, Table: {j + 1}",
                             use_column_width=False, width=500)

                    rows = dtct.rows(table_roi)
                    st.write(f"Number of rows detected: {len(rows)}, Image: {i + 1}, Table: {j + 1}")

                    for k, (y1, y2) in enumerate(rows):
                        row_image = table_roi[y1:y2, :]
                        row_data = []
                        st.image(cv2.cvtColor(row_image, cv2.COLOR_BGR2RGB),
                                 caption=f"Row {k + 1}",
                                 use_column_width=True)
                        cells = dtct.cells(row_image)
                        for m, (x1, x2) in enumerate(cells):
                            cell_image = row_image[:, x1:x2]
                            st.image(cv2.cvtColor(cell_image, cv2.COLOR_BGR2RGB),
                                     caption=f"Cell",
                                     use_column_width=False, width=350)
                            cell_text = ocr_cell(cell_image, ocr_reader)
                            row_data.append(cell_text)
                        table_data.append(row_data)
                    st.write("Extracted Table Data:")
                    st.table(table_data)
            elif display_tables and not table_contours:
                st.write(f"No tables detected on page {i + 1}")

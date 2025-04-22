"""
This module contains functions for generating visuals.
"""
import pandas as pd
import re
import matplotlib.pyplot as plt
import streamlit as st
import logging

# Custom imports
from cls.database import Database
from cls.document import PDF


# Set up logging
log = logging.getLogger(__name__)


# TODO: Fix issue with labels overlapping
def pie_submission_ratio() -> plt.Figure:
    """
    This function generates a pie chart showing the ratio of companies that have already submitted something.

    :return: The plot as a matplotlib figure.
    """
    db = Database.get_instance()

    clients_processed = db.query("""
    SELECT COUNT(DISTINCT client_id)
    FROM audit_case
    WHERE stage = 5
    """)[0][0]

    # This does not include cases that are in stage 1 and don't have an email attached to it!
    clients_processing = db.query("""
    SELECT COUNT(DISTINCT client_id)
    FROM audit_case
    WHERE stage > 1 AND stage < 5 OR (stage = 1 AND email_id NOT null)
    """)[0][0]

    clients_no_submission = db.query("""
    SELECT COUNT(DISTINCT id)
    FROM client
    """)[0][0] - clients_processed - clients_processing

    # Check if there is no data
    if clients_processed == 0 and clients_processing == 0 and clients_no_submission == 0:
        # Create a pie chart
        labels = ['No data']
        sizes = [1]
        colors = ['gray']
        fig, ax = plt.subplots()
        ax.pie(sizes, labels=labels, colors=colors)
        ax.axis('equal')
        return fig

    # Create a pie chart
    labels = ['Processed successfully', 'In progress','No submission']
    sizes = [clients_processed, clients_processing, clients_no_submission]
    colors = ['green', 'yellow', 'red']

    fig, ax = plt.subplots()
    ax.pie(sizes, labels=labels, colors=colors)
    ax.axis('equal')

    return fig


def stage_badge(stage: int, pure_string: bool = False) -> str:
    """
    Return HTML for a status badge based on the audit case status code.

    :param stage: The status code from the audit_case table
    :param pure_string: If True, return only the status text without HTML
    :return: HTML string for a colored badge showing the status
    """
    if pure_string:
        # Return only the status text without HTML
        status_map = {
            1: "Waiting for documents",
            2: "Data verification",
            3: "Certification",
            4: "Process completion",
            5: "Archived",
        }
        return status_map.get(stage, "Unknown")

    # Return HTML for a colored badge
    status_map = {
        1: ("Waiting for documents", "#FFA500"),  # Orange
        2: ("Data verification", "#1E90FF"),  # Blue
        3: ("Certification", "#9370DB"),  # Purple
        4: ("Process completion", "#228B22"),  # Green
        5: ("Archived", "#808080"),  # Gray
    }

    stage_text, color = status_map.get(stage, ("Unknown", "#FF0000"))

    return f"""
    <span style="
        background-color: {color};
        color: white;
        padding: 0.2rem 0.5rem;
        border-radius: 0.25rem;
        font-size: 0.8rem;
        font-weight: bold;
    ">
        {stage_text}
    </span>
    """


def client_info_box(client_data):
    """
    Display client information in a formatted info box.

    :param client_data: Pandas DataFrame row containing client information
    """
    if client_data is None:
        st.warning("No client data available")
        return

    # Create a box with client information
    st.subheader("Client Information")

    # Use columns for better layout
    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"**Institute:** {client_data['institute']}")
        st.markdown(f"**BaFin ID:** {client_data['bafin_id']}")
        st.markdown(f"**Address:** {client_data['address']}")
        st.markdown(f"**City:** {client_data['city']}")

    with col2:
        st.markdown(f"**Contact Person:** {client_data['contact_person']}")
        st.markdown(f"**Phone:** {client_data['phone']}")
        st.markdown(f"**Fax:** {client_data['fax']}")
        st.markdown(f"**Email:** {client_data['email']}")

    # Add a divider
    st.divider()


# TODO: Remove this function since it's not used anymore!
def client_db_value_comparison(client_document: PDF, include_all_fields=True, database: Database = None) -> pd.DataFrame:
    """
    Generate a DataFrame comparing values from the database with values extracted from the document.

    :param include_all_fields: If True, includes all fields in the comparison; otherwise only includes fields that
     are required for validation.
    :param client_document: The document to compare values from.
    :param database: Optional database instance; if not provided, uses the default instance.
    :return: Pandas DataFrame with columns for key figure, database value, document value, and match status
    """
    if database:
        db = database
    else:
        db = Database.get_instance()

    # print(client_document.__str__())
    log.debug(f"Audit values available: {hasattr(client_document, '_audit_values')}")
    if hasattr(client_document, '_audit_values'):
        log.debug(f"Audit values keys: {client_document._audit_values.keys() if client_document._audit_values else 'None'}")

    if not client_document.bafin_id:
        log.warning("No BaFin ID found for document, cannot compare values")
        return pd.DataFrame(columns=["Key figure", "Database value", "Document value", "Match status"])

    # Fetch client data from database
    client_data = db.query(f"""
    SELECT 
        id,
        p033, p034, p035, p036,
        ab2s1n01, ab2s1n02, ab2s1n03, ab2s1n04, 
        ab2s1n05, ab2s1n06, ab2s1n07, ab2s1n08, 
        ab2s1n09, ab2s1n10, ab2s1n11
    FROM client 
    WHERE bafin_id = ?
    """, (client_document.bafin_id,))

    # Check if client exists in database
    if not client_data:
        log.warning(f"Client with BaFin ID {client_document.bafin_id} not found in database")
        return pd.DataFrame(columns=["Key figure", "Database value", "Document value", "Match status"])

    client_data = client_data[0]  # Get first row of results

    # Get document attributes
    document_attributes = client_document.get_attributes()
    if not document_attributes:
        log.warning("No attributes found in document")
        return pd.DataFrame(columns=["Key figure", "Database value", "Document value", "Match status"])

    # Extract audit values if they're not already present
    if not hasattr(client_document, '_audit_values') or not client_document._audit_values:
        log.info("Extracting audit values from document attributes")
        client_document.extract_audit_values()

    # Required fields as defined in compare_values method
    required_fields = [1, 5, 6, 7, 8, 9, 10]  # p033 and ab2s1n01-ab2s1n06 are mandatory

    # Define field mappings and readable names
    field_mappings = {
        # Position fields
        1: {"code": "p033", "name": "Position 033 (Provisionsergebnis)"},
        2: {"code": "p034", "name": "Position 034 (Nettoergebnis Wertpapieren)"},
        3: {"code": "p035", "name": "Position 035 (Nettoergebnis Devisen)"},
        4: {"code": "p036", "name": "Position 036 (Nettoergebnis Derivaten)"},

        # Section fields (§ 16j Abs. 2 Satz 1 Nr. X FinDAG)
        5: {"code": "ab2s1n01", "name": "Nr. 1 (Zahlungsverkehr)"},
        6: {"code": "ab2s1n02", "name": "Nr. 2 (Außenhandelsgeschäft)"},
        7: {"code": "ab2s1n03", "name": "Nr. 3 (Reisezahlungsmittelgeschäft)"},
        8: {"code": "ab2s1n04", "name": "Nr. 4 (Treuhandkredite)"},
        9: {"code": "ab2s1n05", "name": "Nr. 5 (Vermittlung von Kredit)"},
        10: {"code": "ab2s1n06", "name": "Nr. 6 (Kreditbearbeitung)"},
        11: {"code": "ab2s1n07", "name": "Nr. 7 (ausländischen Tochterunternehmen)"},
        12: {"code": "ab2s1n08", "name": "Nr. 8 (Nachlassbearbeitungen)"},
        13: {"code": "ab2s1n09", "name": "Nr. 9 (Electronic Banking)"},
        14: {"code": "ab2s1n10", "name": "Nr. 10 (Gutachtertätigkeiten)"},
        15: {"code": "ab2s1n11", "name": "Nr. 11 (sonstigen Bearbeitungsentgelten)"}
    }

    # Prepare data for the DataFrame
    comparison_data = []

    for db_index, field_info in field_mappings.items():
        # Skip non-required fields if include_all_fields is False
        if not include_all_fields and db_index not in required_fields:
            continue

        field_code = field_info["code"]
        key_figure = field_info["name"]
        db_value = client_data[db_index]
        doc_value = "Not found"
        matches = False

        # Check if this field was extracted from the document
        if hasattr(client_document, '_audit_values') and client_document._audit_values:
            if f"raw_{field_code}" in client_document._audit_values:
                doc_value = client_document._audit_values[f"raw_{field_code}"]

                # If there's a normalized value, use it for comparison
                if field_code in client_document._audit_values:
                    normalized_value = client_document._audit_values[field_code]
                    matches = (normalized_value == db_value)

        # Use icons for match status
        match_status = "✅" if matches else "❌"

        # Add to comparison data
        comparison_data.append({
            "Key figure": key_figure,
            "Database value": db_value,
            "Document value": doc_value,
            "Match status": match_status
        })

    # Create DataFrame
    return pd.DataFrame(comparison_data)

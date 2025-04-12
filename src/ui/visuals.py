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


def client_db_value_comparison(client_document: PDF, include_all_fields=True, database: Database = None) -> pd.DataFrame:
    """
    Generate a DataFrame comparing values from the database with values extracted from the document.
    
    :param include_all_fields: If True, includes all fields in the comparison; otherwise only includes
                              fields that are required for validation.
    :return: Pandas DataFrame with columns for key figure, database value, document value, and match status
    """
    if database:
        db = database
    else:
        db = Database.get_instance()

    # print(client_document.__str__())
    # TODO: CONTINUE HERE IMPLEMENTING THE NEW DISPLAY FUNCTION!!!

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
    
    # Required fields as defined in compare_values method
    required_fields = [1, 5, 6, 7, 8, 9, 10]  # p033 and ab2s1n01-ab2s1n06 are mandatory
    
    # Define field mappings and readable names
    field_mappings = {
        # Position fields
        1: {"patterns": [r"Position 033", r"Position033", r"Pos\.? 033", r"Provisionsergebnis"],
            "name": "Position 033 (Provisionsergebnis)"},
        2: {"patterns": [r"Position 034", r"Position034", r"Pos\.? 034", r"Nettoergebnis.*Wertpapieren"],
            "name": "Position 034 (Nettoergebnis Wertpapieren)"},
        3: {"patterns": [r"Position 035", r"Position035", r"Pos\.? 035", r"Nettoergebnis.*Devisen"],
            "name": "Position 035 (Nettoergebnis Devisen)"},
        4: {"patterns": [r"Position 036", r"Position036", r"Pos\.? 036", r"Nettoergebnis.*Derivaten"],
            "name": "Position 036 (Nettoergebnis Derivaten)"},
        
        # Section fields (§ 16j Abs. 2 Satz 1 Nr. X FinDAG)
        5: {"patterns": [r"Nr\.? 1 FinDAG", r"Nr\.? 1", r"Zahlungsverkehr"],
            "name": "Nr. 1 (Zahlungsverkehr)"},
        6: {"patterns": [r"Nr\.? 2 FinDAG", r"Nr\.? 2", r"Außenhandelsgeschäft"],
            "name": "Nr. 2 (Außenhandelsgeschäft)"},
        7: {"patterns": [r"Nr\.? 3 FinDAG", r"Nr\.? 3", r"Reisezahlungsmittelgeschäft"],
            "name": "Nr. 3 (Reisezahlungsmittelgeschäft)"},
        8: {"patterns": [r"Nr\.? 4 FinDAG", r"Nr\.? 4", r"Treuhandkredite"],
            "name": "Nr. 4 (Treuhandkredite)"},
        9: {"patterns": [r"Nr\.? 5 FinDAG", r"Nr\.? 5", r"Vermittlung von Kredit"],
            "name": "Nr. 5 (Vermittlung von Kredit)"},
        10: {"patterns": [r"Nr\.? 6 FinDAG", r"Nr\.? 6", r"Kreditbearbeitung"],
             "name": "Nr. 6 (Kreditbearbeitung)"},
        11: {"patterns": [r"Nr\.? 7 FinDAG", r"Nr\.? 7", r"ausländischen Tochterunternehmen"],
             "name": "Nr. 7 (ausländischen Tochterunternehmen)"},
        12: {"patterns": [r"Nr\.? 8 FinDAG", r"Nr\.? 8", r"Nachlassbearbeitungen"],
             "name": "Nr. 8 (Nachlassbearbeitungen)"},
        13: {"patterns": [r"Nr\.? 9 FinDAG", r"Nr\.? 9", r"Electronic Banking"],
             "name": "Nr. 9 (Electronic Banking)"},
        14: {"patterns": [r"Nr\.? 10 FinDAG", r"Nr\.? 10", r"Gutachtertätigkeiten"],
             "name": "Nr. 10 (Gutachtertätigkeiten)"},
        15: {"patterns": [r"Nr\.? 11 FinDAG", r"Nr\.? 11", r"sonstigen Bearbeitungsentgelten"],
             "name": "Nr. 11 (sonstigen Bearbeitungsentgelten)"}
    }
    
    # Prepare data for the DataFrame
    comparison_data = []
    
    for db_index, field_info in field_mappings.items():
        # Skip non-required fields if include_all_fields is False
        if not include_all_fields and db_index not in required_fields:
            continue
            
        key_figure = field_info["name"]
        db_value = client_data[db_index]
        doc_value = "Not found"
        matches = False
        
        # Search for this field in document attributes
        for key, value in document_attributes.items():
            # Skip non-value attributes and empty values
            if key in ['filename', 'content_type', 'email_id', 'sender', 'date', 'client_id', 'BaFin-ID'] or not value:
                continue
                
            # Check if the key matches any of the patterns for this field
            if any(re.search(pattern, key, re.IGNORECASE) for pattern in field_info["patterns"]):
                # Found a match, try to convert the value for comparison
                try:
                    # Remove dots (thousand separators) and convert commas to periods for decimal values
                    processed_value = value.replace('.', '')
                    
                    # Handle decimal values (with comma as decimal separator)
                    if ',' in processed_value:
                        # For decimal values, keep the decimal part
                        processed_value = processed_value.replace(',', '.')
                        # If it's a legitimate decimal, convert to float first
                        normalized_value = int(float(processed_value))
                    else:
                        # For integers
                        normalized_value = int(processed_value)
                    
                    doc_value = value  # Store the original value for display
                    # Check if values match
                    matches = (normalized_value == db_value)
                    
                except (ValueError, TypeError):
                    # Keep original value if conversion fails
                    doc_value = value
                    matches = False
                
                break  # Stop checking once we find a match
        
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

"""
This module contains functions for generating visuals.
"""
import matplotlib.pyplot as plt
import streamlit as st

# Custom imports
from cls.database import Database


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

"""
This module contains functions for generating visuals.
"""
import matplotlib.pyplot as plt
import streamlit as st
import logging

# Custom imports
from cls.database import Database


# Set up logging
log = logging.getLogger(__name__)


# TODO: Fix issue with labels overlapping
def pie_submission_ratio() -> plt.Figure:
    """
    Generates a pie chart illustrating the distribution of client cases categorized
    into successfully processed, currently in progress, and not submitted. The chart
    also accounts for situations where no data is available.

    The calculation uses data retrieved from the `Database` instance. It queries the
    number of distinct clients in the following categories:
      - Successfully processed cases (stage 5).
      - Cases in progress (stages > 1 and < 5, or stage 1 with an associated email).
      - Clients with no submitted cases.

    If all these categories have zero values, the chart will indicate "No data".

    :return: A matplotlib figure containing the generated pie chart.
    :rtype: plt.Figure
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
    Returns a status badge or status text based on the given stage. The badge can be
    formatted in HTML or returned as plain text depending on the `pure_string` flag.

    The function supports five stages with respective statuses and colors. If the
    stage number does not correspond to a predefined value, "Unknown" and a red
    color (#FF0000) are returned.

    :param stage: The numeric representation of the current process stage. Accepted
        stages range from 1 to 5.
    :type stage: int
    :param pure_string: Determines whether the return value should be plain text or
        an HTML-formatted badge. If True, plain text is returned. Defaults to False.
    :type pure_string: bool
    :return: A plain status string or an HTML-formatted badge summarizing the
        corresponding process stage.
    :rtype: str
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
    Displays a formatted information box about a client based on the provided
    data. The information is divided into columns for better layout and includes
    details such as institute name, BaFin ID, address, contact person, and
    other contact details. A warning message is displayed if no client data
    is available.

    :param client_data: Dictionary containing client-related information. Expected
        keys are 'institute', 'bafin_id', 'address', 'city', 'contact_person',
        'phone', 'fax', and 'email'.
    :type client_data: dict or None
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

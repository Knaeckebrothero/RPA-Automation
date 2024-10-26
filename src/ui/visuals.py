"""
This module contains functions for generating visuals.
"""
import matplotlib.pyplot as plt

# Custom imports
from cfg.cache import get_database


def pie_submission_ratio() -> plt.Figure:
    """
    This function generates a pie chart showing the ratio of companies that have already submitted something.

    :return: The plot as a matplotlib figure.
    """
    db = get_database()

    cmp_processed = db.query("""
    SELECT COUNT(DISTINCT company_id)
    FROM status
    WHERE status = 'processed'
    """)[0][0]

    cmp_processing = db.query("""
    SELECT COUNT(DISTINCT company_id)
    FROM status
    WHERE status = 'processing'
    """)[0][0]

    cmp_no_submission = db.query("""
    SELECT COUNT(DISTINCT id)
    FROM companies
    """)[0][0] - cmp_processed - cmp_processing

    # Check if there is no data
    if cmp_processed == 0 and cmp_processing == 0 and cmp_no_submission == 0:
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
    sizes = [cmp_processed, cmp_processing, cmp_no_submission]
    colors = ['green', 'yellow', 'red']

    fig, ax = plt.subplots()
    ax.pie(sizes, labels=labels, colors=colors)
    ax.axis('equal')

    return fig

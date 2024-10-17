"""
This module contains functions for generating visuals.
"""
import matplotlib.pyplot as plt

# Custom imports
# from cfg.cache import get_database
from cls.database import Database


def pie_submission_ratio() -> plt.Figure:
    """
    This function generates a pie chart showing the ratio of companies that have already submitted something.

    :return: The plot as a matplotlib figure.
    """
    db = Database().get_instance()

    cmp_processed = db.query("""
    SELECT COUNT(DISTINCT company_id)
    FROM status
    WHERE status = 'processed'
    """)[0]

    cmp_processing = db.query("""
    SELECT COUNT(DISTINCT company_id)
    FROM status
    WHERE status = 'processing'
    """)[0]

    cmp_no_submission = db.query("""
    SELECT COUNT(DISTINCT id)
    FROM companies
    """)[0] - cmp_processed - cmp_processing

    # Create a pie chart
    labels = ['Processed successfully', 'In progress','No submission']
    sizes = [cmp_processed, cmp_processing, cmp_no_submission]
    colors = ['green', 'yellow', 'red']
    # explode = (0.1, 0, 0)  # Explode the first slice

    fig, ax = plt.subplots()
    ax.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', shadow=True, startangle=140) # explode=explode,
    ax.axis('equal')

    return fig

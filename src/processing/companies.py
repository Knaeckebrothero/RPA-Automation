"""
This module contains functions for processing company data.
"""


def get_submission_ratio(self):
    """
    Function that returns a percentage of how many companies have already submitted something.
    """
    try:
        self.cursor.execute("""
            SELECT COUNT(DISTINCT customer_id) FROM status
            """)

        submitted = self.cursor.fetchone()[0]
        self.cursor.execute("""
            SELECT COUNT(DISTINCT customer_id) FROM customers;
            """)
        total = self.cursor.fetchone()[0]
        return submitted / total
    except sqlite3.Error as e:
        log.error(f"Error getting submission ratio: {e}")
        return 0.0


def check_submissions(submissions, companies):
    """
    This function checks whether a company has already submitted the required documents or not.
    It does so by comparing the submissions with a list of companies from the database.
    """
    pass # TODO: Implement this function

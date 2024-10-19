"""
This module contains functions for processing company data.
"""
import logging as log

# Custom imports
from cfg.cache import get_database as db
from cls import Document


def compare_company_values(company_document: Document):
    bafin_id = company_document.get_attributes("BaFin-ID")

    if bafin_id:
        company = db.query(f"SELECT * FROM companies WHERE bafin_id = {bafin_id}")

        if company:
            log.debug(f"Company with BaFin ID {bafin_id} found in database")

            # TODO: Implement comparison logic
            return True
        else:
            log.warning(f"Company with BaFin ID {bafin_id} not found in database")
            return False
    else:
        log.warning("No BaFin ID found for company")
        return False


def check_company_submission(submissions, companies):
    """
    This function checks whether a company has already submitted the required documents or not.
    It does so by comparing the submissions with a list of companies from the database.
    """
    pass # TODO: Implement this function

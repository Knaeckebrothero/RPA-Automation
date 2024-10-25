"""
This module contains functions for processing company data.
"""
import logging as log
import re

# Custom imports
from cfg.cache import get_database
from cls import Document


def initialize_company_status(company_document: Document):
    bafin_id = company_document.get_attributes("BaFin-ID")

    if bafin_id:
        # TODO: Find a better way to check for the BaFin-ID!
        bafin_id = re.search(r'\b\d{8}\b', bafin_id)

        if bafin_id:
            db = get_database()
            bafin_id = bafin_id.group()

            company = db.query(f"SELECT * FROM companies WHERE bafin_id = {bafin_id}")

            # TODO: Implement the initialize_company_status function


def compare_company_values(company_document: Document):
    bafin_id = company_document.get_attributes("BaFin-ID")

    if bafin_id:
        # TODO: Find a better way to check for the BaFin-ID!
        bafin_id = re.search(r'\b\d{8}\b', bafin_id)

        if bafin_id:
            db = get_database()
            bafin_id = bafin_id.group()

            company = db.query(f"""
            SELECT 
                id,
                p033, p034, p035, p036,
                ab2s1n01, ab2s1n02, ab2s1n03, ab2s1n04, 
                ab2s1n05, ab2s1n06, ab2s1n07, ab2s1n08, 
                ab2s1n09, ab2s1n10, ab2s1n11
            FROM companies 
            WHERE bafin_id = {bafin_id}
            """)

            print(company)

            if len(company) > 0:
                log.debug(f"Company with BaFin ID {bafin_id} found in database")
                document_attributes = company_document.get_attributes()

                # TODO: Doesn't work because db returns a list of tuples...

                for db_key, db_value in company[0].items().drop("id"):
                    for doc_key, doc_value in document_attributes.keys():
                        if db_key in doc_key:
                            try:
                                if int(db_value) != int(doc_value):
                                    log.debug(f"Value mismatch for key {db_key}: {db_value} (database) vs {doc_value} (document)")
                                    return False
                                else:
                                    log.debug(f"Value match for key {db_key}: {db_value} (database) vs {doc_value} (document)")
                                    return True
                            except ValueError:
                                log.error(f"Value for key {db_key} is not an integer")
                                return False
                        else:
                            log.debug(f"Key {db_key} not found in document")
                            return False
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
    pass # TODO: Implement the check_company_submission function

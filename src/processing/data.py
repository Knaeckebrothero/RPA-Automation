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

            company = db.query(f"SELECT * FROM clients WHERE bafin_id = {bafin_id}" )

            # TODO: Implement the initialize_company_status function


def compare_company_values(company_document: Document):
    bafin_id = company_document.get_attributes("BaFin-ID")

    if bafin_id:
        # TODO: Find a better way to check for the BaFin-ID!
        bafin_id = re.search(r'\b\d{8}\b', bafin_id)

        if bafin_id:
            db = get_database()
            bafin_id = bafin_id.group()

            company_data = db.query(f"""
            SELECT 
                id,
                p033, p034, p035, p036,
                ab2s1n01, ab2s1n02, ab2s1n03, ab2s1n04, 
                ab2s1n05, ab2s1n06, ab2s1n07, ab2s1n08, 
                ab2s1n09, ab2s1n10, ab2s1n11
            FROM companies 
            WHERE bafin_id = {bafin_id}
            """)

            if len(company_data) > 0:
                log.debug(f"Company with BaFin ID {bafin_id} found in database")
                document_attributes = company_document.get_attributes()

                # TODO: Implement a proper way to compare the values
                for key in document_attributes.keys():
                    try:
                        value = int(document_attributes[key].replace(".", ""))
                    except ValueError:
                        continue

                    if "033" in key:
                        if company_data[0][1] != value:
                            log.warning(f"db: {type(company_data[0][1])} vs doc: {type(value)}")
                            log.warning(f"Value mismatch for key {key}: {company_data[0][1]} (database) vs {value} (document)")
                            return False
                    elif "034" in key:
                        if company_data[0][2] != value:
                            log.warning(f"Value mismatch for key {key}: {company_data[0][2]} (database) vs {value} (document)")
                            return False
                    elif "035" in key:
                        if company_data[0][3] != value:
                            log.warning(f"Value mismatch for key {key}: {company_data[0][3]} (database) vs {value} (document)")
                            return False
                    elif "036" in key:
                        if company_data[0][4] != value:
                            log.warning(f"Value mismatch for key {key}: {company_data[0][4]} (database) vs {value} (document)")
                            return False
                    elif "Nr. 1" in key:
                        if company_data[0][5] != value:
                            log.warning(f"Value mismatch for key {key}: {company_data[0][5]} (database) vs {value} (document)")
                            return False
                    elif "Nr. 2" in key:
                        if company_data[0][6] != value:
                            log.warning(f"Value mismatch for key {key}: {company_data[0][6]} (database) vs {value} (document)")
                            return False
                    elif "Nr. 3" in key:
                        if company_data[0][7] != value:
                            log.warning(f"Value mismatch for key {key}: {company_data[0][7]} (database) vs {value} (document)")
                            return False
                    elif "Nr. 4" in key:
                        if company_data[0][8] != value:
                            log.warning(f"Value mismatch for key {key}: {company_data[0][8]} (database) vs {value} (document)")
                            return False
                    elif "Nr. 5" in key:
                        if company_data[0][9] != value:
                            log.warning(f"Value mismatch for key {key}: {company_data[0][9]} (database) vs {value} (document)")
                            return False
                    elif "Nr. 6" in key:
                        if company_data[0][10] != value:
                            log.warning(f"Value mismatch for key {key}: {company_data[0][10]} (database) vs {value} (document)")
                            return False
                    elif "Nr. 7" in key:
                        if company_data[0][11] != value:
                            log.warning(f"Value mismatch for key {key}: {company_data[0][11]} (database) vs {value} (document)")
                            return False
                    elif "Nr. 8" in key:
                        if company_data[0][12] != value:
                            log.warning(f"Value mismatch for key {key}: {company_data[0][12]} (database) vs {value} (document)")
                            return False
                    elif "Nr. 9" in key:
                        if company_data[0][13] != value:
                            log.warning(f"Value mismatch for key {key}: {company_data[0][13]} (database) vs {value} (document)")
                            return False
                    elif "Nr. 10" in key:
                        if company_data[0][14] != value:
                            log.warning(f"Value mismatch for key {key}: {company_data[0][14]} (database) vs {value} (document)")
                            return False
                    #elif "Nr. 11" in key:
                    #    if company_data[0][15] != float(value.replace(".", "").replace(",", ".")):
                    #        log.debug(f"Value mismatch for key {key}: {company_data[0][15]} (database) vs {value} (
                            #        document)")
                    #        return False

                # Return True if all conditions are met and no mismatches are found
                log.info(f"Values for company with BaFin ID {bafin_id} match the database.")
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
    pass # TODO: Implement the check_company_submission function

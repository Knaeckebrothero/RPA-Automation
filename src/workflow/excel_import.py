"""
This module handles importing audit season initialization data from Excel files.
"""
import pandas as pd
import logging
from typing import List, Dict, Tuple
from io import BytesIO

# Custom imports
from cls.database import Database
from cls.accesscontrol import AccessControl
import workflow.security as sec


# Set up logging
log = logging.getLogger(__name__)

# TODO: Move this functionality into the processing/files module!
class ExcelImporter:
    """
    Handles importing audit initialization data from Excel files.
    """

    def __init__(self, database: Database = None):
        """
        Initialize the Excel importer.

        :param database: Database instance (optional)
        """
        self.db = database or Database.get_instance()
        self.errors = []
        self.warnings = []
        self.success_count = 0
        self.created_users = []  # Track users created during import

    def import_audit_season(self, excel_data: BytesIO | str, granted_by: int) -> Dict:
        """
        Import audit season data from an Excel file.

        :param excel_data: Either a file path or BytesIO object containing Excel data
        :param granted_by: The ID of the user performing the import (for audit trail)
        :return: Dictionary with import results
        """
        self.errors = []
        self.warnings = []
        self.success_count = 0
        self.created_users = []

        try:
            # Read Excel file
            df = pd.read_excel(excel_data)
            log.info(f"Read Excel file with {len(df)} rows")

            # Validate required columns
            required_columns = ['Bank ID']  # Minimum required
            missing_columns = [col for col in required_columns if col not in df.columns]

            if missing_columns:
                self.errors.append(f"Missing required columns: {', '.join(missing_columns)}")
                return self._get_results()

            # Process each row
            for index, row in df.iterrows():
                self._process_row(row, index + 2, granted_by)  # +2 for Excel row number (header + 0-index)

            log.info(f"Import completed. Success: {self.success_count}, Errors: {len(self.errors)}")

        except Exception as e:
            self.errors.append(f"Failed to read Excel file: {str(e)}")
            log.error(f"Excel import failed: {e}")

        return self._get_results()

    def _process_row(self, row: pd.Series, row_number: int, granted_by: int):
        """
        Process a single row from the Excel file.

        :param row: Pandas Series representing one row
        :param row_number: The row number in Excel (for error reporting)
        :param granted_by: User ID performing the import
        """
        try:
            # Get BaFin ID
            bafin_id = row.get('Bank ID')
            if pd.isna(bafin_id):
                self.warnings.append(f"Row {row_number}: Missing Bank ID, skipping")
                return

            # Convert to integer if it's a float
            bafin_id = int(bafin_id)

            # Find client by BaFin ID
            client = self.db.get_client_by_bafin_id(bafin_id)
            if not client:
                self.errors.append(f"Row {row_number}: No client found with BaFin ID {bafin_id}")
                return

            client_id = client['id']

            # Check if audit case exists for this client
            existing_case = self.db.query("""
                                          SELECT id FROM audit_case
                                          WHERE client_id = ? AND stage < 5
                                          """, (client_id,))

            if not existing_case:
                # Create new audit case
                case_id = self.db.insert("""
                                         INSERT INTO audit_case (client_id, stage, comments)
                                         VALUES (?, 1, 'Created from Excel import')
                                         """, (client_id,))
                log.info(f"Created audit case {case_id} for client {client_id}")

            # Process access permissions
            assignments = []

            # Process Inspector 1
            inspector1 = row.get('Inspector 1')
            if not pd.isna(inspector1) and inspector1:
                user = self._find_or_create_user(str(inspector1).strip(), 'inspector', row_number)
                if user:
                    assignments.append({
                        'user_id': user['id'],
                        'client_id': client_id,
                        'role': 'inspector'
                    })

            # Process Inspector 2
            inspector2 = row.get('Inspector 2')
            if not pd.isna(inspector2) and inspector2:
                user = self._find_or_create_user(str(inspector2).strip(), 'inspector', row_number)
                if user:
                    assignments.append({
                        'user_id': user['id'],
                        'client_id': client_id,
                        'role': 'inspector'
                    })

            # Process Auditor
            auditor = row.get('Auditor')
            if not pd.isna(auditor) and auditor:
                user = self._find_or_create_user(str(auditor).strip(), 'auditor', row_number)
                if user:
                    assignments.append({
                        'user_id': user['id'],
                        'client_id': client_id,
                        'role': 'auditor'
                    })

            # Grant access permissions
            for assignment in assignments:
                # Grant access
                success = AccessControl.grant_client_access(
                    assignment['user_id'],
                    client_id,
                    granted_by,
                    self.db
                )

                if not success:
                    self.errors.append(
                        f"Row {row_number}: Failed to grant access for user {assignment['user_id']} "
                        f"to client {client_id}"
                    )

            self.success_count += 1

        except Exception as e:
            self.errors.append(f"Row {row_number}: Processing error - {str(e)}")
            log.error(f"Error processing row {row_number}: {e}")

    def _find_or_create_user(self, identifier: str, role: str, row_number: int) -> Dict | None:
        """
        Find a user by identifier or create a new one if not found.

        :param identifier: Name or email address from Excel
        :param role: The role to assign to the user ('inspector' or 'auditor')
        :param row_number: Row number for error reporting
        :return: User dictionary or None
        """
        # First check if it's already an email address
        if '@' in identifier:
            # Try to find by email
            user = self.db.get_user_by_email(identifier)
            if user:
                return user

            # If it looks like an email but user not found, log warning
            self.warnings.append(f"Row {row_number}: User with email '{identifier}' not found, creating new user")
            username = identifier
        else:
            # Generate username from name
            username = self._generate_username(identifier)

            # Check if user already exists
            user = self.db.get_user_by_email(username)
            if user:
                return user

        # User doesn't exist, create new one
        log.info(f"Creating new user: {username} with role: {role}")

        # Generate secure password
        password = sec.generate_secure_password()

        # Hash the password
        password_hash, password_salt = sec.hash_password(password)

        try:
            # Insert the new user
            user_id = self.db.insert("""
                                     INSERT INTO user (username_email, password_hash, password_salt, role)
                                     VALUES (?, ?, ?, ?)
                                     """, (username, password_hash, password_salt, role))

            # Track the created user with their credentials
            self.created_users.append({
                'username': username,
                'password': password,  # Store plaintext password for reporting
                'role': role,
                'name': identifier,
                'row': row_number
            })

            log.info(f"Successfully created user: {username} with ID: {user_id}")

            # Return the created user info
            return {
                'id': user_id,
                'email': username,
                'role': role
            }

        except Exception as e:
            self.errors.append(f"Row {row_number}: Failed to create user '{username}' - {str(e)}")
            log.error(f"Error creating user: {e}")
            return None

    def _generate_username(self, name: str, domain: str = "example.com") -> str:
        """
        Generate a username from a name by removing ALL whitespaces and converting to lowercase.

        :param name: The name to convert
        :param domain: Email domain to append (default: example.com)
        :return: Generated username as email
        """
        # Remove ALL whitespaces (including between words) and convert to lowercase
        username_part = ''.join(name.split()).lower()

        # Append domain
        return f"{username_part}@{domain}"

    def _find_user(self, identifier: str) -> Dict | None:
        """
        Find a user by email or username.

        :param identifier: Email address or username
        :return: User dictionary or None
        """
        # First try as email
        user = self.db.get_user_by_email(identifier)
        if user:
            return user

        # If contains @, it's likely an email that wasn't found
        if '@' in identifier:
            return None

        # Try to find by partial match (username part of email)
        result = self.db.query("""
                               SELECT id, username_email, role, created_at
                               FROM user
                               WHERE LOWER(username_email) LIKE LOWER(?)
                               """, (f'{identifier}@%',))

        if result and len(result) == 1:
            return {
                'id': result[0][0],
                'email': result[0][1],
                'role': result[0][2],
                'created_at': result[0][3]
            }

        return None

    def _get_results(self) -> Dict:
        """
        Get the results of the import operation.

        :return: Dictionary with results
        """
        return {
            'success': len(self.errors) == 0,
            'success_count': self.success_count,
            'errors': self.errors,
            'warnings': self.warnings,
            'created_users': self.created_users,
            'total_errors': len(self.errors),
            'total_warnings': len(self.warnings),
            'total_created_users': len(self.created_users)
        }

    @staticmethod
    def validate_excel_structure(excel_data: BytesIO | str) -> Tuple[bool, List[str]]:
        """
        Validate that an Excel file has the expected structure.

        :param excel_data: Either a file path or BytesIO object containing Excel data
        :return: Tuple of (is_valid, list_of_issues)
        """
        issues = []

        try:
            df = pd.read_excel(excel_data)

            # Check for required columns
            required_columns = ['Bank ID']
            recommended_columns = ['Nr', 'Name', 'PLZ', 'City', 'Comment',
                                   'Inspector 1', 'Inspector 2', 'Auditor']

            # Check required columns
            missing_required = [col for col in required_columns if col not in df.columns]
            if missing_required:
                issues.append(f"Missing required columns: {', '.join(missing_required)}")

            # Check recommended columns
            missing_recommended = [col for col in recommended_columns if col not in df.columns]
            if missing_recommended:
                issues.append(f"Missing recommended columns: {', '.join(missing_recommended)}")

            # Check if file is empty
            if len(df) == 0:
                issues.append("Excel file contains no data rows")

            # Check for duplicate Bank IDs
            if 'Bank ID' in df.columns:
                duplicates = df[df.duplicated(subset=['Bank ID'], keep=False)]
                if not duplicates.empty:
                    duplicate_ids = duplicates['Bank ID'].unique()
                    issues.append(f"Duplicate Bank IDs found: {', '.join(map(str, duplicate_ids))}")

        except Exception as e:
            issues.append(f"Failed to read Excel file: {str(e)}")

        return len(issues) == 0, issues

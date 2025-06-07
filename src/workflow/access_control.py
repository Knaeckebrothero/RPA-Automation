"""
This module handles access control for the application, managing both role-based
and resource-based permissions.
"""
import logging
from typing import List, Optional, Set
from datetime import datetime

# Custom imports
from cls.database import Database


# Set up logging
log = logging.getLogger(__name__)


class AccessControl:
    """
    Centralized access control management for the application.
    Handles both role-based permissions (for features) and resource-based
    permissions (for client access).
    """

    # Define feature permissions by role
    FEATURE_PERMISSIONS = {
        'admin': {
            'settings', 'user_management', 'archive_cases', 'initialize_audit',
            'view_all_cases', 'edit_all_cases', 'generate_certificate',
            'complete_process', 'view_logs'
        },
        'inspector': {
            'view_assigned_cases', 'edit_assigned_cases', 'generate_certificate',
            'view_logs'
        },
        'auditor': {
            'view_assigned_cases', 'edit_assigned_cases'
        }
    }

    @staticmethod
    def can_access_client(user_id: int, client_id: int, user_role: str = None,
                          database: Database = None) -> bool:
        """
        Check if a user can access a specific client.

        :param user_id: The ID of the user
        :param client_id: The ID of the client
        :param user_role: The user's role (optional, will be fetched if not provided)
        :param database: Database instance (optional)
        :return: True if user can access the client, False otherwise
        """
        # Get database instance
        db = database or Database.get_instance()

        # Get user role if not provided
        if not user_role:
            result = db.query("SELECT role FROM user WHERE id = ?", (user_id,))
            if not result:
                log.warning(f"User {user_id} not found")
                return False
            user_role = result[0][0]

        # Admins can access all clients
        if user_role == 'admin':
            return True

        # Check if user has explicit access to this client
        result = db.query("""
                          SELECT 1 FROM user_client_access
                          WHERE user_id = ? AND client_id = ?
                          """, (user_id, client_id))

        return bool(result)

    @staticmethod
    def get_accessible_clients(user_id: int, user_role: str = None,
                               database: Database = None) -> List[int]:
        """
        Get list of client IDs that a user can access.

        :param user_id: The ID of the user
        :param user_role: The user's role (optional, will be fetched if not provided)
        :param database: Database instance (optional)
        :return: List of client IDs the user can access
        """
        # Get database instance
        db = database or Database.get_instance()

        # Get user role if not provided
        if not user_role:
            result = db.query("SELECT role FROM user WHERE id = ?", (user_id,))
            if not result:
                log.warning(f"User {user_id} not found")
                return []
            user_role = result[0][0]

        # Admins can access all clients
        if user_role == 'admin':
            result = db.query("SELECT id FROM client")
            return [row[0] for row in result] if result else []

        # Get explicitly granted client access
        result = db.query("""
                          SELECT client_id FROM user_client_access
                          WHERE user_id = ?
                          """, (user_id,))

        return [row[0] for row in result] if result else []

    @staticmethod
    def can_access_feature(user_role: str, feature_name: str) -> bool:
        """
        Check if a role has access to a specific feature.

        :param user_role: The user's role
        :param feature_name: The name of the feature
        :return: True if role can access the feature, False otherwise
        """
        if not user_role or user_role not in AccessControl.FEATURE_PERMISSIONS:
            return False

        return feature_name in AccessControl.FEATURE_PERMISSIONS.get(user_role, set())

    @staticmethod
    def grant_client_access(user_id: int, client_id: int, granted_by: int = None,
                            database: Database = None) -> bool:
        """
        Grant a user access to a specific client.

        :param user_id: The ID of the user to grant access
        :param client_id: The ID of the client
        :param granted_by: The ID of the user granting access (optional)
        :param database: Database instance (optional)
        :return: True if access was granted, False if failed
        """
        db = database or Database.get_instance()

        try:
            # Check if access already exists
            existing = db.query("""
                                SELECT 1 FROM user_client_access
                                WHERE user_id = ? AND client_id = ?
                                """, (user_id, client_id))

            if existing:
                log.info(f"User {user_id} already has access to client {client_id}")
                return True

            # Grant access
            db.insert("""
                      INSERT INTO user_client_access (user_id, client_id, granted_by)
                      VALUES (?, ?, ?)
                      """, (user_id, client_id, granted_by))

            log.info(f"Granted user {user_id} access to client {client_id}")
            return True

        except Exception as e:
            log.error(f"Error granting client access: {e}")
            return False

    @staticmethod
    def revoke_client_access(user_id: int, client_id: int, database: Database = None) -> bool:
        """
        Revoke a user's access to a specific client.

        :param user_id: The ID of the user
        :param client_id: The ID of the client
        :param database: Database instance (optional)
        :return: True if access was revoked, False if failed
        """
        db = database or Database.get_instance()

        try:
            db.query("""
                     DELETE FROM user_client_access
                     WHERE user_id = ? AND client_id = ?
                     """, (user_id, client_id))

            log.info(f"Revoked user {user_id} access to client {client_id}")
            return True

        except Exception as e:
            log.error(f"Error revoking client access: {e}")
            return False

    @staticmethod
    def get_user_client_access(user_id: int, database: Database = None) -> List[dict]:
        """
        Get all client access records for a user.

        :param user_id: The ID of the user
        :param database: Database instance (optional)
        :return: List of dictionaries containing client access information
        """
        db = database or Database.get_instance()

        result = db.query("""
                          SELECT
                              uca.client_id,
                              c.institute,
                              c.bafin_id,
                              uca.granted_at,
                              u.username_email as granted_by_email
                          FROM user_client_access uca
                                   JOIN client c ON uca.client_id = c.id
                                   LEFT JOIN user u ON uca.granted_by = u.id
                          WHERE uca.user_id = ?
                          ORDER BY c.institute
                          """, (user_id,))

        if not result:
            return []

        return [
            {
                'client_id': row[0],
                'institute': row[1],
                'bafin_id': row[2],
                'granted_at': row[3],
                'granted_by': row[4]
            }
            for row in result
        ]

    @staticmethod
    def bulk_grant_access(assignments: List[dict], granted_by: int = None,
                          database: Database = None) -> dict:
        """
        Grant multiple users access to multiple clients in bulk.

        :param assignments: List of dicts with 'user_id' and 'client_id' keys
        :param granted_by: The ID of the user granting access
        :param database: Database instance (optional)
        :return: Dictionary with success count and errors
        """
        db = database or Database.get_instance()
        success_count = 0
        errors = []

        for assignment in assignments:
            user_id = assignment.get('user_id')
            client_id = assignment.get('client_id')

            if not user_id or not client_id:
                errors.append(f"Invalid assignment: {assignment}")
                continue

            if AccessControl.grant_client_access(user_id, client_id, granted_by, db):
                success_count += 1
            else:
                errors.append(f"Failed to grant user {user_id} access to client {client_id}")

        return {
            'success_count': success_count,
            'errors': errors
        }

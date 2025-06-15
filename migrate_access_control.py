"""
Migration script to add access control tables to existing database.
Run this script to update your database schema for the new access control features.
"""
import os
import sys
import logging

# Add parent directory to path so we can import from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.cls.database import Database


# Set up logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


def migrate_database():
    """
    Add the user_client_access table to existing database.
    """
    # Migration SQL
    migration_sql = """
                    -- User-Client Access Control table
                    CREATE TABLE IF NOT EXISTS user_client_access (
                                                                      user_id INTEGER NOT NULL,
                                                                      client_id INTEGER NOT NULL,
                                                                      granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                                                      granted_by INTEGER,
                                                                      PRIMARY KEY (user_id, client_id),
                                                                      FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE,
                                                                      FOREIGN KEY (client_id) REFERENCES client(id) ON DELETE CASCADE,
                                                                      FOREIGN KEY (granted_by) REFERENCES user(id)
                    );

                    -- Indexes for performance
                    CREATE INDEX IF NOT EXISTS idx_user_client_access_user ON user_client_access(user_id);
                    CREATE INDEX IF NOT EXISTS idx_user_client_access_client ON user_client_access(client_id); \
                    """

    try:
        # Get database instance
        db = Database.get_instance()

        # Check if table already exists
        result = db.query("""
                          SELECT name FROM sqlite_master
                          WHERE type='table' AND name='user_client_access'
                          """)

        if result:
            log.info("Table 'user_client_access' already exists. Migration not needed.")
            return True

        # Execute migration
        log.info("Creating 'user_client_access' table...")
        success = db.execute_migration(migration_sql)

        if success:
            log.info("Migration completed successfully!")

            # Optional: Grant all existing non-admin users access to all clients
            # This maintains backward compatibility
            migrate_existing_access = input(
                "Do you want to grant all existing users access to all clients? (y/n): "
            ).lower() == 'y'

            if migrate_existing_access:
                # Get all non-admin users
                users = db.query("SELECT id FROM user WHERE role != 'admin'")
                clients = db.query("SELECT id FROM client")

                if users and clients:
                    assignments = []
                    for user in users:
                        for client in clients:
                            assignments.append({
                                'user_id': user[0],
                                'client_id': client[0]
                            })

                    # Use AccessControl to grant access
                    from cls.accesscontrol import AccessControl
                    results = AccessControl.bulk_grant_access(assignments, database=db)

                    log.info(f"Granted access: {results['success_count']} assignments created")
                    if results['errors']:
                        log.error(f"Errors during access grant: {results['errors']}")
        else:
            log.error("Migration failed!")
            return False

    except Exception as e:
        log.error(f"Migration error: {e}")
        return False

    return True


if __name__ == "__main__":
    if migrate_database():
        print("\nMigration completed successfully!")
        print("The database has been updated with access control tables.")
        print("\nNext steps:")
        print("1. Restart the application")
        print("2. Use the Excel import feature to assign users to clients")
        print("3. Or use the Access Control tab in Settings to manually assign access")
    else:
        print("\nMigration failed! Please check the logs for details.")

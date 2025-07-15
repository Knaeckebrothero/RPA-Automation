import os
import sys
import argparse
import logging
import subprocess
import shutil

# Import db_init to use its functions directly
import db_init

# ConfigHandler import is removed


def setup_logging():
    """
    Set up logging configuration.

    :return: Logger instance
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger(__name__)


def parse_args():
    """
    Parse command line arguments.

    :return: Parsed arguments
    """
    parser = argparse.ArgumentParser(description='Initialize the complete application.')
    # Database arguments (passing through to db_init.py)
    parser.add_argument(
        '--db-path',
        default=os.environ.get('DB_PATH', './.filesystem/database.db'),
        help='Path to the SQLite database file (default: DB_PATH env var or ./.filesystem/database.db)'
    )
    parser.add_argument(
        '--schema-path',
        default='./src/schema.sql',
        help='Path to the schema SQL file (default: ./src/schema.sql)'
    )
    parser.add_argument(
        '--json-path',
        default='./examples/examples.json',
        help='Path to the JSON file with example data (default: ./examples/examples.json)'
    )
    parser.add_argument(
        '--force-reset',
        action='store_true',
        help='Force reset the database (warning: this will delete all existing data)'
    )

    # Email downloader arguments
    parser.add_argument(
        '--download-emails',
        action='store_true',
        help='Download emails from the mail server'
    )
    parser.add_argument(
        '--num-emails',
        type=int,
        default=10,
        help='Number of emails to download (default: 10)'
    )

    # Application init specific arguments
    parser.add_argument(
        '--skip-db-init',
        action='store_true',
        help='Skip database initialization'
    )
    parser.add_argument(
        '--setup-only',
        action='store_true',
        help='Only set up the filesystem structure without initializing components'
    )

    return parser.parse_args()


def setup_filesystem(logger, base_dir, filesystem_dirs, force_reset=False): # config object removed from parameters
    """
    Set up the filesystem structure required by the application.

    :param logger: Logger instance
    :param base_dir: Base directory for the filesystem, consistent with ConfigHandler's default
    :param force_reset: If True, delete all existing content in .filesystem
    :param filesystem_dirs: List of directories to create
    :return: True if successful, False otherwise
    """
    try:
        # Ensure the base directorys exists
        if force_reset and os.path.exists(base_dir):
            logger.warning(f"Force reset enabled - deleting all content in {base_dir}")
            try:
                shutil.rmtree(base_dir)
                logger.info(f"Successfully deleted {base_dir} directory and all its contents")
            except Exception as e:
                logger.error(f"Error deleting {base_dir}: {e}")
                return False

        created_count = 0
        for directory in filesystem_dirs:
            if not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
                logger.info(f"Created directory: {directory}")
                created_count += 1

        if created_count == 0 and not force_reset:
            logger.info("All required directories already exist")
        else:
            logger.info(f"Created {created_count} directories")

        if not os.path.exists('./.env'):
            if os.path.exists('./.env.example'):
                shutil.copy('./.env.example', './.env')
                logger.info("Created .env file from .env.example")
            else:
                logger.warning(".env.example not found, skipping .env creation")

        # Copy template files to their locations specified by environment variables or defaults
        try:
            # Get destination paths from environment variables, with fallbacks to defaults
            certificate_template_dest_path = os.getenv(
                'CERTIFICATE_TEMPLATE_PATH',
                os.path.join(base_dir, "certificate_template.docx")
            )
            terms_conditions_dest_path = os.getenv(
                'CERTIFICATE_TOS_PATH',
                os.path.join(base_dir, "terms_conditions.pdf")
            )

            # Ensure destination directories exist
            for dest_path in [certificate_template_dest_path, terms_conditions_dest_path]:
                dest_dir = os.path.dirname(dest_path)
                if not os.path.exists(dest_dir):
                    os.makedirs(dest_dir, exist_ok=True)
                    logger.info(f"Created directory for template: {dest_dir}")

            files_to_copy = [
                ('examples/certificate_template.docx', certificate_template_dest_path),
                ('examples/terms_conditions.pdf', terms_conditions_dest_path)
            ]

            for source_file, dest_file in files_to_copy:
                if os.path.exists(source_file):
                    shutil.copy2(source_file, dest_file)
                    logger.info(f"Copied {source_file} to {dest_file}")
                else:
                    logger.warning(f"Source file not found: {source_file}")

            # Copy email_templates folder
            email_templates_source = 'examples/email_templates'
            email_templates_dest = os.path.join(base_dir, 'email_templates')

            if os.path.exists(email_templates_source):
                # If destination exists and force_reset is not set, skip or merge
                if os.path.exists(email_templates_dest):
                    if force_reset:
                        shutil.rmtree(email_templates_dest)
                        shutil.copytree(email_templates_source, email_templates_dest)
                        logger.info(f"Replaced email_templates directory at {email_templates_dest}")
                    else:
                        # Copy individual files to avoid overwriting customizations
                        for item in os.listdir(email_templates_source):
                            source_item = os.path.join(email_templates_source, item)
                            dest_item = os.path.join(email_templates_dest, item)

                            if os.path.isfile(source_item):
                                if not os.path.exists(dest_item) or force_reset:
                                    shutil.copy2(source_item, dest_item)
                                    logger.info(f"Copied email template: {item}")
                                else:
                                    logger.info(f"Email template already exists, skipping: {item}")
                else:
                    # Directory doesn't exist, copy the whole thing
                    shutil.copytree(email_templates_source, email_templates_dest)
                    logger.info(f"Copied email_templates directory to {email_templates_dest}")

                # List what was copied
                if os.path.exists(email_templates_dest):
                    template_files = os.listdir(email_templates_dest)
                    logger.info(f"Email templates directory contains: {', '.join(template_files)}")
            else:
                logger.warning(f"Email templates source directory not found: {email_templates_source}")

        except Exception as e:
            logger.error(f"Error copying template files: {e}")

        return True

    except Exception as e:
        logger.error(f"Error setting up filesystem: {e}")
        return False


def download_emails(num_emails, logger):
    """
    Download emails using the email_downloader.py script.

    :param num_emails: Number of emails to download
    :param logger: Logger instance
    :return: True if successful, False otherwise
    """
    try:
        logger.info(f"Downloading {num_emails} emails...")

        downloader_script_path = './examples/email_downloader.py'
        if not os.path.exists(downloader_script_path):
            logger.error(f"{downloader_script_path} not found")
            return False

        base_dir = os.getenv('FILESYSTEM_PATH', './.filesystem')
        email_output_dir = os.path.join(base_dir, 'test_emails')

        cmd = [
            sys.executable,
            downloader_script_path,
            '--num-emails', str(num_emails),
            '--output-dir', email_output_dir,
            '--force'
        ]

        process = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if process.returncode == 0:
            logger.info("Email download completed successfully")
            return True
        else:
            logger.error(f"Email download failed with exit code {process.returncode}")
            logger.error(f"Error: {process.stderr}")
            return False

    except Exception as e:
        logger.error(f"Error downloading emails: {e}")
        return False


def init_database(args, logger):
    """
    Initialize the database by calling db_init functions directly.

    :param args: Command line arguments
    :param logger: Logger instance
    :return: True if successful, False otherwise
    """
    try:
        logger.info("Initializing database...")

        success = db_init.initialize_database(
            args.db_path,
            args.schema_path,
            args.json_path,
            args.force_reset,
            logger
        )

        if success:
            return True
        else:
            logger.error("Database initialization failed")
            return False

    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        return False


def verify_application_setup(logger, required_dirs):
    """
    Verify that all components of the application are properly set up.

    :param logger: Logger instance
    :param required_dirs: List of required directories to check
    :return: True if successful, False otherwise
    """
    try:
        logger.info("Verifying application setup...")

        base_dir = os.getenv('FILESYSTEM_PATH', './.filesystem')

        # Check all required directories
        for directory in required_dirs:
            if not os.path.exists(directory):
                logger.error(f"Required directory not found: {directory}")

        # Check for database
        default_db_path = os.path.join(base_dir, 'database.db')
        if not os.path.exists(default_db_path):
            logger.warning(f"Database file not found at default location {default_db_path}. If custom path used, this may be normal.")

        # Check for .env file
        if not os.path.exists('./.env'):
            logger.warning(".env file not found - application may not function correctly")

        # Check for email templates
        email_templates_dir = os.path.join(base_dir, 'email_templates')
        if os.path.exists(email_templates_dir):
            templates = os.listdir(email_templates_dir)
            logger.info(f"Found {len(templates)} email template(s): {', '.join(templates)}")
        else:
            logger.warning("Email templates directory not found")

        logger.info("Application setup verified successfully")
        return True

    except Exception as e:
        logger.error(f"Error verifying application setup: {e}")
        return False


def main():
    """
    Main function to initialize the application.

    :return: Exit code (0 for success, 1 for failure)
    """
    logger = setup_logging()
    args = parse_args()

    # ConfigHandler instantiation removed from here

    logger.info("Starting application initialization")

    # Define the base filesystem directory, consistent with ConfigHandler's default
    base_dir = os.getenv('FILESYSTEM_PATH', './.filesystem')

    # Define the required directories to create
    filesystem_dirs = [
        base_dir,
        os.path.join(base_dir, 'documents'),
        os.path.join(base_dir, 'email_templates'),  # Added email_templates
        './example_mails',
        os.path.join(base_dir, 'logs')
    ]

    # Step 1: Set up the filesystem structure
    if not setup_filesystem(logger, base_dir, filesystem_dirs, args.force_reset): # config argument removed
        logger.error("Failed to set up filesystem structure")
        return 1

    if args.setup_only:
        logger.info("Setup only mode - exiting after filesystem setup")
        return 0

    if args.download_emails:
        if not download_emails(args.num_emails, logger):
            logger.error("Failed to download emails")

    if not args.skip_db_init:
        if not init_database(args, logger):
            logger.error("Failed to initialize database")
            return 1
    else:
        logger.info("Database initialization skipped (--skip-db-init)")

    if not verify_application_setup(logger, filesystem_dirs):
        logger.warning("Application setup verification failed")

    logger.info("Application initialization completed successfully")

    print("\nApplication initialized successfully!")
    print("To start the application, run: python src/main.py")
    print("\nDefault login credentials:")
    print("  Admin:     admin@example.com / admin123")
    print("  Auditor:   auditor@example.com / auditor123")
    print("  Inspector: inspector@example.com / inspector123")

    return 0


if __name__ == "__main__":
    # Check if running in CI environment
    is_ci = os.environ.get("CI", "").lower() == "true"

    if is_ci:
        print("Running in CI mode - using minimal test data")

        # Override settings for CI
        os.environ["DB_PATH"] = os.environ.get("DB_PATH", "test_db.sqlite")
        os.environ["DEV_MODE"] = "true"
        os.environ["LOG_LEVEL"] = "WARNING"

        # You can modify your existing initialization functions to accept parameters
        # For example, if you have a create_test_data() function:
        # create_test_data(minimal=True)

        # Or add CI-specific initialization here
        print("Initializing database for CI...")
        # Your existing initialization code but with fewer records

        # Example: Create only essential test data
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
        from cls.database import Database
        db = Database.get_instance()

        # Create admin user for tests
        db.insert("""
            INSERT OR IGNORE INTO user (username_email, password_hash, password_salt, role)
            VALUES ('test_admin@test.com', 'hashed_test_password', 'test_salt', 'admin')
        """)

        # Create one test client
        db.insert("""
            INSERT OR IGNORE INTO client (
                institute, bafin_id, email, address, city, contact_person,
                phone, fax, p033, p034, p035, p036, ab2s1n01, ab2s1n02,
                ab2s1n03, ab2s1n04, ab2s1n05, ab2s1n06, ab2s1n07, ab2s1n08,
                ab2s1n09, ab2s1n10, ab2s1n11, ratio
            ) VALUES (
                'Test Client CI', 99999, 'client@test.com', '123 Test St', 'Test City',
                'Test Person', '555-1234', '555-5678', 1000, 2000, 3000, 4000,
                5000, 6000, 7000, 8000, 9000, 10000, 11000, 12000, 13000, 14000, 15000, 1.5
            )
        """)

        print("CI initialization complete")
    else:
        # Normal initialization for development/production
        print("Running normal initialization...")
        # Your existing initialization code goes here
        sys.exit(main())

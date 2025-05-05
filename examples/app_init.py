"""
Initialization script for the complete application.

This script initializes the entire application by:
1. Setting up the filesystem structure
2. Downloading emails using email_downloader.py (if requested)
3. Initializing the database by calling db_init.py
4. Verifying that all components are ready

Usage:
    python app_init.py [options]

Options:
    --db-path PATH         Path to the SQLite database file
    --schema-path PATH     Path to the schema SQL file
    --json-path PATH       Path to the JSON file with example data
    --force-reset          Force reset the database (warning: this will delete all existing data)
    --download-emails      Download emails from the mail server
    --num-emails N         Number of emails to download (default: 10)
    --skip-db-init         Skip database initialization
    --setup-only           Only set up the filesystem structure without initializing components
"""
import os
import sys
import argparse
import logging
import subprocess
import shutil
from pathlib import Path

# Import db_init to use its functions directly
import db_init


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
        default='./.filesystem/database.db',
        help='Path to the SQLite database file (default: ./.filesystem/database.db)'
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


def setup_filesystem(logger, force_reset=False):
    """
    Set up the filesystem structure required by the application.
    
    :param logger: Logger instance
    :param force_reset: If True, delete all existing content in .filesystem
    :return: True if successful, False otherwise
    """
    try:
        # Define the base filesystem directory
        base_dir = './.filesystem'
        
        # Define the required directories to create
        filesystem_dirs = [
            base_dir,
            f'{base_dir}/uploads',
            f'{base_dir}/processed',
            f'{base_dir}/test_emails',
            f'{base_dir}/logs',
            f'{base_dir}/temp'
        ]
        
        # If force reset is enabled and the base directory exists, delete it completely
        if force_reset and os.path.exists(base_dir):
            logger.warning(f"Force reset enabled - deleting all content in {base_dir}")
            try:
                shutil.rmtree(base_dir)
                logger.info(f"Successfully deleted {base_dir} directory and all its contents")
            except Exception as e:
                logger.error(f"Error deleting {base_dir}: {e}")
                return False
        
        # Create each directory
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
        
        # Create an empty .env file if it doesn't exist, copying from .env.example
        if not os.path.exists('./.env'):
            if os.path.exists('./.env.example'):
                shutil.copy('./.env.example', './.env')
                logger.info("Created .env file from .env.example")
            else:
                logger.warning(".env.example not found, skipping .env creation")
        
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

        # Check if email_downloader.py exists
        if not os.path.exists('./examples/email_downloader.py'):
            logger.error("email_downloader.py not found in examples directory")
            return False

        # Build the command
        cmd = [
            sys.executable,
            './examples/email_downloader.py',
            '--num-emails', str(num_emails),
            '--output-dir', './.filesystem/test_emails',
            '--force'
        ]

        # Execute the command
        process = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Check if the command was successful
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

        # Call the db_init.initialize_database function directly
        success = db_init.initialize_database(
            args.db_path,
            args.schema_path,
            args.json_path,
            args.force_reset,
            logger
        )

        if success:
            logger.info("Database initialization completed successfully")
            return True
        else:
            logger.error("Database initialization failed")
            return False

    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        return False


def verify_application_setup(logger):
    """
    Verify that all components of the application are properly set up.

    :param logger: Logger instance
    :return: True if successful, False otherwise
    """
    try:
        logger.info("Verifying application setup...")

        # Check for required directories
        required_dirs = [
            './.filesystem',
            './.filesystem/uploads',
            './.filesystem/processed'
        ]

        for directory in required_dirs:
            if not os.path.exists(directory):
                logger.error(f"Required directory not found: {directory}")
                return False

        # Check for database file
        if not os.path.exists('./.filesystem/database.db'):
            logger.warning("Database file not found at ./.filesystem/database.db")
            return False

        # Check for .env file
        if not os.path.exists('./.env'):
            logger.warning(".env file not found - application may not function correctly")

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

    logger.info("Starting application initialization")

    # Step 1: Set up the filesystem structure
    if not setup_filesystem(logger, args.force_reset):
        logger.error("Failed to set up filesystem structure")
        return 1

    # If setup-only flag is set, exit after setting up filesystem
    if args.setup_only:
        logger.info("Setup only mode - exiting after filesystem setup")
        return 0

    # Step 2: Download emails if requested
    if args.download_emails:
        if not download_emails(args.num_emails, logger):
            logger.error("Failed to download emails")
            # Continue with initialization even if email download fails

    # Step 3: Initialize database unless skipped
    if not args.skip_db_init:
        if not init_database(args, logger):
            logger.error("Failed to initialize database")
            return 1
    else:
        logger.info("Database initialization skipped (--skip-db-init)")

    # Step 4: Verify application setup
    if not verify_application_setup(logger):
        logger.warning("Application setup verification failed")
        # Don't return error code here, just warn the user

    logger.info("Application initialization completed successfully")

    # Print usage instructions
    print("\nApplication initialized successfully!")
    print("To start the application, run: python src/main.py")
    print("\nDefault login credentials:")
    print("  Admin:     admin@example.com / admin123")
    print("  Auditor:   auditor@example.com / auditor123")
    print("  Inspector: inspector@example.com / inspector123")

    return 0


if __name__ == "__main__":
    sys.exit(main())

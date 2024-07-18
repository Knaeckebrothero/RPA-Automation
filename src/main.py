"""
This file holds the main function for the eBonFetcher application.
"""
import os
from dotenv import load_dotenv, find_dotenv

# Custom imports
from src.config.custom_logger import configure_custom_logger
from src.email.client import Client
import src.ui.home as ui


def main():
    # Initialize the logger
    logger = configure_custom_logger(
        module_name='main',
        console_level=int(os.getenv('LOG_LEVEL')),
        file_level=int(os.getenv('LOG_LEVEL')),
    )

    load_dotenv(find_dotenv())
    logger.debug('Environment variables loaded')

    # Initialize the mail client
    logger.debug('initializing mail client')
    mailbox = Client(
        imap_server=os.getenv('IMAP_HOST'),
        imap_port=int(os.getenv('IMAP_PORT')),
        username=os.getenv('IMAP_USER'),
        password=os.getenv('IMAP_PASSWORD'),
        inbox=os.getenv('INBOX'),
    )

    # Start the UI
    logger.debug('Starting the UI')
    ui.home(logger)


if __name__ == '__main__':
    main()

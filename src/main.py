"""
This file holds the main function for the eBonFetcher application.
"""
import os
from dotenv import load_dotenv, find_dotenv
from src.email.client import Client
import src.ui.home as ui


def main():
    """
    """
    print('Starting eBonFetcher')

    # Load environment variables
    load_dotenv(find_dotenv())

    print(os.getenv('IMAP_HOST'))
    print(os.getenv('IMAP_PORT'))

    # Initialize the mail client
    mailbox = Client(
        imap_server=os.getenv('IMAP_HOST'),
        imap_port=int(os.getenv('IMAP_PORT')),
        username=os.getenv('IMAP_USER'),
        password=os.getenv('IMAP_PASSWORD'),
        inbox=os.getenv('INBOX'),
    )

    for box in mailbox.list_inboxes():
        print(box, '\n')

    # Start the UI
    ui.home()


if __name__ == '__main__':
    main()

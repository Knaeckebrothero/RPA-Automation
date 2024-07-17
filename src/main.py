"""
This file holds the main function for the eBonFetcher application.
"""
import os
from dotenv import load_dotenv, find_dotenv
import logging
from email.client import Client


def main():
    """
    """
    print('Starting eBonFetcher')

    # Load environment variables
    load_dotenv(find_dotenv())

    # Create a mailbox object
    box = mail(
        imap_server=os.getenv('IMAP_HOST'),
        imap_port=os.getenv('IMAP_PORT'),
        username=os.getenv('IMAP_USER'),
        password=os.getenv('IMAP_PASS'),
        mailbox='INBOX'
    )


if __name__ == '__main__':
    main()

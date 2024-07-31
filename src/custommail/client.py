"""
This module holds the mail.Client class.
"""
import os
import imaplib
import email
from email.header import decode_header
from bs4 import BeautifulSoup
import pandas as pd
# Custom imports
from config.custom_logger import configure_custom_logger
from config.singleton import Singleton


class Client(Singleton):
    """
    This class is used to connect and interact with the mail server.
    It uses the custom singleton class to ensure only one instance of the class is created.

    The class uses the imaplib library to connect to the mail server and offers
    a bunch of methods to interact with the mailbox.
    """
    _connection = None  # Connection to the mail server
    _log = None  # Logger for the class
    _decoding_format = 'utf-8'  # 'iso-8859-1'

    def __init__(self, imap_server: str, imap_port: int, username: str,
                 password: str, inbox: str = None, *args, **kwargs):
        """
        Automatically connects to the mailclient, using the provided credentials,
        once the class is instantiated.

        If no inbox is provided, it will default to the 'INBOX'.
        It also defines a custom logger for the class.

        :param imap_server: The imap server to connect to.
        :param imap_port: The port of the imap server.
        :param username: The username/mail to connect to.
        :param password: The user's password.
        :param inbox: Inbox to connect to. Defaults to None.
        """
        self._log = configure_custom_logger(
            module_name=__name__,
            console_level=int(os.getenv('LOG_LEVEL_CONSOLE')),
            file_level=int(os.getenv('LOG_LEVEL_FILE')),
            logging_directory=os.getenv('LOG_PATH') if os.getenv('LOG_PATH') else None
        )
        self._log.debug('Logger initialized')

        # Connect to the mail server if not connected already
        if not self._connection:
            self.connect(imap_server, imap_port)
            self.login(username, password)
        else:
            self._log.debug('Instance already connected, skipping connection and login.')

        # Select the inbox
        self._inbox = inbox
        self.select_inbox(inbox)

        self._log.debug('Mail client initialized')

    def __del__(self):
        """
        Destructor for the mailbox class.
        Automatically closes the connection to the server when the class is destroyed.
        """
        if self._connection:
            self.close()

        self._log.debug('Mail client destroyed')

    # Getters
    def get_connection(self):
        return self._connection

    def get_inbox(self):
        return self._inbox

    def get__decoding_format(self):
        return self._decoding_format

    def set_decoding_format(self, decoding_format: str):
        self._decoding_format = decoding_format

    def connect(self, imap_server: str, imap_port: int):
        """
        Method to connect to the mailserver using the classes credentials.
        It connects to the inbox attribute to connect to.
        Defaults to None, which will connect to the default inbox.
        """
        try:
            self._connection = imaplib.IMAP4_SSL(host=imap_server, port=imap_port)
            self._log.debug(f'Successfully connected to mailbox at {imap_server}:{imap_port}')

        except Exception as e:
            self._log.error(f'Error connecting to the mail server: {e}')

    def login(self, username: str, password: str):
        """
        Method to login to the mail server.

        :param username: The username to login with.
        :param password: The password to login with.
        """
        if not self._connection:
            self._log.error('Not connected to any mail server at the moment, cannot login!')
            return

        self._connection.login(user=username, password=password)
        self._log.debug(f'Successfully logged in to the mail server using {username[:3]}, password {password[0]}')

    def close(self):
        """
        Closes the mailclient and logs out of the server.
        Sets the mail attribute to None.
        """
        self._log.debug('Closing the connection to the mail server...')

        self._connection.logout()
        self._connection = None

        self._log.debug('Connection server closed, mail set to none.')

    def select_inbox(self, inbox: str = None):
        """
        Method to select an inbox.

        :param inbox: The inbox to select.
        """
        if not self._connection:
            self._log.error('Not connected to any mail server at the moment, cannot select inbox!')
            return

        self._log.debug('Selecting inbox...')
        if not inbox and not self._inbox:
            self._connection.select('INBOX')
            self._inbox = 'INBOX'
            self._log.debug('No inbox provided, defaulting to "INBOX"')
        elif not inbox and self._inbox:
            self._connection.select(self._inbox)
            self._log.debug(f'No inbox provided, defaulting to {self._inbox}')
        else:
            self._connection.select(inbox)
            self._inbox = f'"{inbox}"'  # TODO: Check if quotation marks are necessary
            self._log.debug(f'Selected inbox: {inbox}')

    def list_inboxes(self):
        """
        Method to get a list of possible inboxes.
        """
        self._log.debug('Listing inboxes...')
        return self._connection.list()[1]

    def list_mails(self):
        """
        Method to list the mails in the selected inbox.
        """
        self._log.debug('Listing mails...')
        status, response = self._connection.search(None, 'ALL')
        self._log.info('Requested mails, server responded with: %s', status)
        return response

    def get_mails(self):
        """
        Method to list the mails in the selected inbox and return them as a pandas DataFrame.
        """
        self._log.debug('Listing mails...')
        status, response = self._connection.search(None, 'ALL')
        self._log.info('Requested mails, server responded with: %s', status)

        email_ids = response[0].split()
        emails_data = []
        decoding_format = 'utf-8'  # 'iso-8859-1'

        # Loop through custommail ids
        for email_id in email_ids:
            # Fetch the custommail
            _, msg_data = self._connection.fetch(email_id, '(RFC822)')

            # Loop through the parts of the custommail
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    email_message = email.message_from_bytes(response_part[1])

                    # Get the subject
                    subject = decode_header(email_message['Subject'])[0][0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(decoding_format)

                    # Get the sender and date
                    sender = email_message['From']
                    date = email_message['Date']

                    # Get custommail body
                    if email_message.is_multipart():
                        for part in email_message.walk():

                            # If the custommail part is text/plain, extract the body
                            if part.get_content_type() == "text/plain":
                                body = part.get_payload(decode=True).decode(decoding_format)
                                break

                            # If the custommail part is html, use BeautifulSoup to extract text
                            elif part.get_content_type() == "text/html":
                                body = BeautifulSoup(part.get_payload(decode=True).decode(decoding_format), 'html.parser').get_text()
                                break
                    else:
                        # If the custommail is not multipart, extract the body
                        body = email_message.get_payload(decode=True).decode(decoding_format)

                    # Truncate body to a snippet
                    body_snippet = body[:100] + '...' if len(body) > 100 else body

                    # Append the custommail data to the list
                    emails_data.append({
                        'ID': email_id.decode(decoding_format),
                        'Subject': subject,
                        'From': sender,
                        'Date': date,
                        'Body Snippet': body_snippet
                    })

        # Return the emails in a pandas DataFrame
        df = pd.DataFrame(emails_data)
        self._log.info(f'Retrieved {len(df)} emails')
        return df

    def get_attachment(self, email_id) -> list:
        """
        Method to get the attachments of an custommail.

        :param email_id: The id of the custommail to get the attachments from.
        :return: A list of attachments or an empty list if no attachments are found.
        """
        try:
            # Fetch the custommail
            _, msg_data = self._connection.fetch(email_id, '(RFC822)')
            raw_email = msg_data[0][1]

            # Parse the custommail
            email_message = email.message_from_bytes(raw_email)

            # List to store attachments in
            attachments = []

            # Walk through custommail parts and look for attachments
            for part in email_message.walk():
                if part.get_content_maintype() == 'multipart':
                    continue
                if part.get('Content-Disposition') is None:
                    continue

                # Get the filename
                filename = part.get_filename()
                if not filename:
                    continue

                # Decode the filename
                filename = decode_header(filename)[0][0]
                if isinstance(filename, bytes):
                    filename = filename.decode()

                # Get the attachment data
                attachment_data = part.get_payload(decode=True)

                # Append the attachment to the list
                attachments.append({
                    'filename': filename,
                    'data': attachment_data
                })

            if attachments:
                self._log.info(f'Found {len(attachments)} attachments in custommail {email_id}')
            else:
                self._log.warning(f'No attachments found in custommail {email_id}')

            # Return the attachments, if non are found list will be empty
            return attachments

        except Exception as e:
            self._log.error(f"Error processing custommail {email_id}: {str(e)}")
            return []

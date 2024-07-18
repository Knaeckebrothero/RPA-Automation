"""
This module holds the mail.Client class.
"""
import os
import imaplib
import pandas as pd

# Custom imports
from config.custom_logger import configure_custom_logger


class Client:
    """
    This class is used to connect and interact with the mail server.
    """

    def __init__(self, imap_server: str, imap_port: int, username: str,
                 password: str, inbox: str = None):
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
        # Check environment variables for log level
        if os.getenv('LOG_LEVEL'):
            log_level = int(os.environ['LOG_LEVEL'])
        else:
            log_level = 30

        # Initialize the logger
        self.logger = configure_custom_logger(
            module_name='mailclient', console_level=log_level, file_level=log_level,
            logging_directory=os.environ['LOG_PATH'] if os.getenv('LOG_PATH') else None
        )
        self.logger.debug('Logger initialized')

        # Set the class attributes
        self._imap_server = imap_server
        self._imap_port = imap_port
        self._username = username
        self._password = password
        self.mail = None
        self.inbox = inbox
        self.logger.debug('Class attributes set')

        # Connect to the inbox
        self.connect()

    def __del__(self):
        """
        Destructor for the mailbox class.
        Automatically closes the connection to the server when the class is destroyed.
        """
        self.logger.info('Closing the connection to the mail server...')
        self.close()

    def connect(self):
        """
        Method to connect to the mailserver using the classes credentials.
        It connects to the inbox attribute to connect to.
        Defaults to None, which will connect to the default inbox.
        """
        self.logger.debug('Connecting to the mail server...')

        try:
            self.mail = imaplib.IMAP4_SSL(host=self._imap_server, port=self._imap_port)
            self.mail.login(user=self._username, password=self._password)
            self.logger.info(f'Successfully connected to mailbox at {self._imap_server}:{self._imap_port}')

            if self.inbox:
                self.select_inbox()

        except Exception as e:
            self.logger.error(f'Error connecting to the mail server: {e}')

    def close(self):
        """
        Closes the mailclient and logs out of the server.
        Sets the mail attribute to None.
        """
        self.logger.debug('Closing the connection to the mail server...')

        self.mail.logout()
        self.mail = None

        self.logger.debug('Connection server closed, mail set to none.')

    def select_inbox(self, inbox: str = None):
        """
        Method to select an inbox.

        :param inbox: The inbox to select.
        """
        self.logger.debug('Selecting inbox...')
        if not inbox:
            self.mail.select('INBOX')
            self.inbox = 'INBOX'
            self.logger.debug('No inbox provided, defaulting to "INBOX"')
        else:
            self.mail.select(inbox)
            self.inbox = inbox
            self.logger.debug(f'Selected inbox: {inbox}')

    def list_inboxes(self):
        """
        Method to get a list of possible inboxes.
        """
        self.logger.debug('Listing inboxes...')
        return self.mail.list()[1]

    def list_mails(self):
        """
        Method to list the mails in the selected inbox.
        """
        self.logger.debug('Listing mails...')
        status, response = self.mail.search(None, 'ALL')
        self.logger.info('Requested mails, server responded with: %s', status)
        return response

    def get_mails(self):
        """
        Method to list the mails in the selected inbox and return them as a pandas DataFrame.
        """
        self.logger.debug('Listing mails...')
        status, response = self.mail.search(None, 'ALL')
        self.logger.info('Requested mails, server responded with: %s', status)

        email_ids = response[0].split()
        emails_data = []

        for email_id in email_ids:
            _, msg_data = self.mail.fetch(email_id, '(RFC822)')
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    email_body = response_part[1]
                    email_message = email.message_from_bytes(email_body)

                    subject = decode_header(email_message['Subject'])[0][0]
                    if isinstance(subject, bytes):
                        subject = subject.decode()

                    sender = email_message['From']
                    date = email_message['Date']

                    # Get email body
                    if email_message.is_multipart():
                        for part in email_message.walk():
                            if part.get_content_type() == "text/plain":
                                body = part.get_payload(decode=True).decode()
                                break
                            elif part.get_content_type() == "text/html":
                                body = BeautifulSoup(part.get_payload(decode=True).decode(), 'html.parser').get_text()
                                break
                    else:
                        body = email_message.get_payload(decode=True).decode()

                    # Truncate body to a snippet
                    body_snippet = body[:100] + '...' if len(body) > 100 else body

                    emails_data.append({
                        'ID': email_id.decode(),
                        'Subject': subject,
                        'From': sender,
                        'Date': date,
                        'Body Snippet': body_snippet
                    })

        df = pd.DataFrame(emails_data)
        self.logger.info(f'Retrieved {len(df)} emails')
        return df

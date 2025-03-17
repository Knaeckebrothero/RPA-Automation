"""
This module holds a mock implementation of the imaplib.IMAP4_SSL class and is used to simulate an IMAP server

The credentials for the mock server are:
Host: right.host.com
Port: 993
User: right@example.com
Password: right_password
INBOX: right_mailbox
"""
import os
# import imaplib
import socket
import pickle


# class MockIMAP4_SSL(imaplib.IMAP4_SSL):
class MockIMAP4_SSL():
    def __init__(self, host, port):
        # Simulate connection failures for the wrong credentials
        if host != "right.host.com" and port != 993:
            raise socket.gaierror(11001, "getaddrinfo failed")

        self.host = host
        self.port = port
        self.state = 'NONAUTH'
        self.selected_mailbox = None
        # self.welcome = b"* OK IMAP4 ready"


    def _add_test_emails(self):
        """
        Add some test emails to the mock server
        """
        # TODO: Remove this and replace it with a folder that holds the recorded emails

        # Create sample test emails
        for i in range(1, 5):
            email_content = f"""
            From: test{i}@example.com
            Subject: Test Email {i}
            Date: Wed, 26 Feb 2025 12:0{i}:00 +0000
            Content-Type: multipart/mixed; boundary="boundary_{i}"
            
            --boundary_{i}
            Content-Type: text/plain
            
            This is test email {i}
            
            --boundary_{i}
            Content-Type: application/pdf; name="test{i}.pdf"
            Content-Disposition: attachment; filename="test{i}.pdf"
            Content-Transfer-Encoding: base64
            
            VGhpcyBpcyBhIHRlc3QgUERGIGZpbGUgY29udGVudCB7aX0=
            
            --boundary_{i}--
            """
            self._mock_emails.append({
                'id': str(i).encode(),
                'content': email_content.encode()
            })


    def login(self, user, password):
        """
        Mock login method

        :param user: The username
        :param password: The password
        :return: Tuple containing the status and response
        """
        if user != "right@example.com" or password != "right_password":
            return 'NO', [b'[AUTHENTICATIONFAILED] Invalid credentials (Failure)']
        else:
            self.state = 'AUTH'
            return 'OK', [b'right@email.com authenticated (Success)']


    def logout(self):
        """
        Mock logout method

        :return: Tuple containing the status and response
        """
        self.state = 'LOGOUT'
        return 'BYE', [b'Logout Requested']


    def select(self, mailbox):
        """
        Mock select method

        :param mailbox: The mailbox to select
        :return: Tuple containing the status and response
        """
        if mailbox != 'right_mailbox':
            return 'NO', [b'[NONEXISTENT] Unknown Mailbox: wrong_mailbox (now in authenticated state) (Failure)']

        self.selected_mailbox = mailbox
        self.state = 'SELECTED'
        # TODO: Add length of emails in mailbox to response
        return 'OK', [b'53']


    def list(self, directory='""', pattern='*'):
        """
        Mock list method - returns a list of mailboxes

        :param directory: The directory to list
        :param pattern: The pattern to match
        :return: Tuple containing the status and response
        """
        return 'OK', [
            b'(\\HasNoChildren) "/" "Drafts"',
            b'(\\HasNoChildren) "/" "right_mailbox"',
            b'(\\HasNoChildren) "/" "INBOX"',
            b'(\\HasNoChildren) "/" "Receipts"',
            b'(\\HasNoChildren) "/" "Sent"',
            b'(\\HasNoChildren) "/" "Trash"'
        ]


    def search(self, charset, *criteria):
        """
        Mock search method - returns all email IDs

        :param charset: The charset to use
        :param criteria: The search criteria
        :return: Tuple containing the status and response
        """
        # TODO: Return recorded search result ids
        # ids = b' '.join([str(i+1).encode() for i in range(len(self._mock_emails))])
        return 'OK', [b'1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 41 42 43 44 45 46 47 48 49 50 51 52 53']


    def fetch(self, message_id, message_parts):
        """
        Mock fetch method - returns email content based on ID

        :param message_id: The message ID to fetch
        :param message_parts: The parts to fetch
        :return: Tuple containing the status and response
        """
        try:
            # Convert the message_id to string for filename
            message_id_str = message_id.decode('iso-8859-1')

            if not "EXAMPLE_MAIL_PATH" in os.environ:
                from dotenv import load_dotenv
                load_dotenv()

            # Load the saved response
            with open(f"{os.getenv("EXAMPLE_MAIL_PATH")}/test_mail_{message_id_str}.pickle", 'rb') as f:
                msg_data = pickle.load(f)

            return 'OK', msg_data
        except (FileNotFoundError, pickle.PickleError):
            return 'OK', None


    def close(self):
        """
        Mock close method
        """
        self.selected_mailbox = None
        self.state = 'AUTH'
        return 'OK', [b'CLOSE completed']

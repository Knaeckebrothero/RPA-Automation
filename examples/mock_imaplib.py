"""
This module holds a custom implementation of the imaplib.IMAP4_SSL class for testing purposes.
"""
# import imaplib


# class MockIMAP4_SSL(imaplib.IMAP4_SSL):
class MockIMAP4_SSL():
    def __init__(self, host, port):
        if not host or not port:
            raise ValueError('Host and port must be provided')

        self.host = host
        self.port = port
        self.state = 'NONAUTH'
        self.mailboxes = {'INBOX': []}
        self.selected_mailbox = None
        self._mock_emails = []  # Will hold the test emails
        self._add_test_emails()


    def _add_test_emails(self):
        """
        Add some test emails to the mock server
        """
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
        if user and password:
            self.state = 'AUTH'
            return 'OK', [b'LOGIN completed']
        else:
            return 'NO', [b'LOGIN failed']


    def logout(self):
        """
        Mock logout method

        :return: Tuple containing the status and response
        """
        self.state = 'LOGOUT'
        return 'OK', [b'LOGOUT completed']


    def select(self, mailbox):
        """
        Mock select method

        :param mailbox: The mailbox to select
        :return: Tuple containing the status and response
        """
        if not mailbox:
            return 'NO', [b'SELECT failed']

        self.selected_mailbox = mailbox
        self.state = 'SELECTED'
        return 'OK', [str(len(self._mock_emails)).encode()]


    def list(self, directory='""', pattern='*'):
        """
        Mock list method - returns INBOX

        :param directory: The directory to list
        :param pattern: The pattern to match
        :return: Tuple containing the status and response
        """
        return 'OK', [b'(\\HasNoChildren) "/" "INBOX"']


    def search(self, charset, *criteria):
        """
        Mock search method - returns all email IDs

        :param charset: The charset to use
        :param criteria: The search criteria
        :return: Tuple containing the status and response
        """
        ids = b' '.join([email['id'] for email in self._mock_emails])
        return 'OK', [ids]


    def fetch(self, message_set, message_parts):
        """
        Mock fetch method - returns email content based on ID

        :param message_set: The message set to fetch
        :param message_parts: The message parts to fetch
        :return: Tuple containing the status and response
        """
        results = []

        # Convert message_set to a list of IDs
        if b':' in message_set:
            start, end = message_set.split(b':')
            ids = range(int(start), int(end) + 1)
        else:
            ids = [int(id_) for id_ in message_set.split(b' ')]

        for id_ in ids:
            if 1 <= id_ <= len(self._mock_emails):
                email = self._mock_emails[id_ - 1]
                results.append((f"{id_} (RFC822 {{size}})".encode(), email['content']))

        return 'OK', results

    def close(self):
        """
        Mock close method
        """
        self.selected_mailbox = None
        self.state = 'AUTH'
        return 'OK', [b'CLOSE completed']

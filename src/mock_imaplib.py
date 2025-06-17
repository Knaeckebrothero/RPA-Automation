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
        """
        Simulates the initialization of a connectivity object to a host and port with
        required validations. This constructor specifically validates the host and port
        inputs to ensure connection succeeds only with correct credentials. Upon
        initialization, the object's state is set to `NONAUTH` and no mailbox is
        selected.

        :param host: The hostname or IP address of the server to connect.
        :type host: str
        :param port: The port number to use for the connection.
        :type port: int

        :raises socket.gaierror: If the provided host and port values are incorrect
            (i.e., not the expected valid combination).
        """
        if host != "right.host.com" and port != 993:
            raise socket.gaierror(11001, "getaddrinfo failed")

        self.host = host
        self.port = port
        self.state = 'NONAUTH'
        self.selected_mailbox = None
        # self.welcome = b"* OK IMAP4 ready"
    def _add_test_emails(self):
        """
        Adds a set of test emails to the mock email list for testing purposes. The emails are
        constructed with predefined attributes including sender, subject, date, content, and
        an attached test PDF file. This method is intended for testing and should be replaced
        by an alternative mechanism for managing test data in the future.

        :raises NotImplementedError: if the method is used in a production environment without
        proper modification. The method is currently designed for testing only.
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
        Authenticate a user by checking the provided credentials.

        This method compares the given user email and password with
        pre-defined valid credentials. If the credentials match,
        authentication will be successful, and the user's state will
        be updated. Otherwise, it will return a failure message.

        :param user: The email address of the user attempting to log in.
        :type user: str
        :param password: The password associated with the user attempting
            to log in.
        :type password: str
        :return: A tuple where the first element is a status string
            ('OK' for successful authentication and 'NO' for failure) and
            the second element is a list containing a response message in
            byte format providing further details on the result.
        :rtype: tuple
        """
        if user != "right@example.com" or password != "right_password":
            return 'NO', [b'[AUTHENTICATIONFAILED] Invalid credentials (Failure)']
        else:
            self.state = 'AUTH'
            return 'OK', [b'right@email.com authenticated (Success)']

    def logout(self):
        """
        Logs the user out by updating the internal state and returning a logout response.

        This method sets the state of the object to 'LOGOUT' and generates a
        logout response message. It is used to signal the termination of the
        user's session or interaction.

        :return: A tuple where the first element is a string response ('BYE')
            and the second element is a list containing a single byte-string
            message indicating a logout request.
        :rtype: tuple[str, list[bytes]]
        """
        self.state = 'LOGOUT'
        return 'BYE', [b'Logout Requested']

    def select(self, mailbox):
        """
        Selects and sets the specified mailbox for subsequent commands. The operation changes
        the current state to 'SELECTED' if the mailbox exists and is valid. If the mailbox does
        not exist, the operation will not change the state and will return an error message.

        :param mailbox: The name of the mailbox to be selected.
        :type mailbox: str
        :return: A tuple containing the response status ('OK' or 'NO') and a list of response
                 messages. If the mailbox exists, the status is 'OK' and the response includes
                 the mailbox information. If the mailbox does not exist, the status is 'NO' and
                 the response contains an error message.
        :rtype: tuple[str, list[bytes]]
        """
        if mailbox != 'right_mailbox':
            return 'NO', [b'[NONEXISTENT] Unknown Mailbox: wrong_mailbox (now in authenticated state) (Failure)']

        self.selected_mailbox = mailbox
        self.state = 'SELECTED'
        # TODO: Add length of emails in mailbox to response
        return 'OK', [b'53']

    def list(self, directory='""', pattern='*'):
        """
        Lists directories and their patterns according to the specified parameters.

        This method retrieves a list of directories matching the given directory and
        pattern. The response includes the status and a list of tuples detailing
        hierarchies and directory names.

        :param directory: The parent directory to start listing from.
        :type directory: str
        :param pattern: The pattern to filter directory names.
        :type pattern: str
        :return: A tuple containing the status and a list of directory metadata.
                 The directory metadata consists of attributes, hierarchy deliminators,
                 and directory names in bytestring format.
        :rtype: tuple[str, list[bytes]]
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
        Search for messages that match the given criteria within the specified character set.
        The function simulates the behavior of an email server by returning a status string
        and a list of matching message identifiers.

        :param charset: Character set used for the search query.
        :type charset: str
        :param criteria: Search criteria specifying the desired messages to locate.
        :type criteria: tuple
        :return: A tuple containing the search status and a list of matching message IDs.
        :rtype: tuple[str, list[bytes]]
        """
        # TODO: Return recorded search result ids
        # ids = b' '.join([str(i+1).encode() for i in range(len(self._mock_emails))])
        return 'OK', [b'1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 41 42 43 44 45 46 47 48 49 50 51 52 53']

    def fetch(self, message_id, message_parts):
        """
        Fetches the email message data for a given message ID and its parts from a predefined
        directory. If the message ID is in bytes, it converts it into a string to construct the
        file path. The function attempts to load the message data from a pickle file stored in
        the directory specified by an environment variable. If the environment variable is not
        set, it loads it from a `.env` file. The function returns the loaded message data or
        `None` if the file is missing or cannot be loaded.

        :param message_id: The unique identifier of the email message. Could be in bytes or string.
        :param message_parts: Specific parts of the message to retrieve. Acts as a filter for
            extraction.

        :return: A tuple containing a status ('OK') and the loaded message data. The message
            data will be `None` if there is an error during loading (e.g., file not found or
            deserialization issue).
        :rtype: tuple
        """
        try:
            # Convert the message_id to string for filename if it's bytes
            if isinstance(message_id, bytes):
                message_id_str = message_id.decode('iso-8859-1')
            else:
                message_id_str = message_id

            if not "EXAMPLE_MAIL_PATH" in os.environ:
                from dotenv import load_dotenv
                load_dotenv()

            # Load the saved response
            with open(f"{os.getenv('EXAMPLE_MAIL_PATH')}/test_mail_{message_id_str}.pickle", 'rb') as f:
                msg_data = pickle.load(f)

            return 'OK', msg_data
        except (FileNotFoundError, pickle.PickleError):
            return 'OK', None


    def close(self):
        """
        Closes the currently selected mailbox and resets the state to 'AUTH'.

        :return: A tuple containing a status string and a list with a completion
                 message in bytes.
        :rtype: tuple[str, list[bytes]]
        """
        self.selected_mailbox = None
        self.state = 'AUTH'
        return 'OK', [b'CLOSE completed']

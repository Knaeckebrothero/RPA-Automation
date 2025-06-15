"""
This module holds the mail.Client class.
"""
import os
import logging
import email
import re
import smtplib
import pandas as pd
from email.header import decode_header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.base import MIMEBase
from email import encoders
from typing import Dict, List, Union
from html.parser import HTMLParser


# Custom imports
from cls.singleton import Singleton
from cls.document import Document, PDF


# Set up logging
log = logging.getLogger(__name__)


# Check if the script is running in development mode
if not os.getenv('DEV_MODE'):
    import dotenv
    dotenv.load_dotenv(dotenv.find_dotenv())

# Check if the environment variable is set to 'test'
if os.getenv('DEV_MODE') == 'true':
    # Import the mock IMAP4_SSL class for testing
    from mock_imaplib import MockIMAP4_SSL as IMAP4_SSL

    # Replace the email environment variables with the credentials for the mock imap server
    os.environ['IMAP_HOST'] = 'right.host.com'
    os.environ['IMAP_PORT'] = '993'
    os.environ['IMAP_USER'] = 'right@example.com'
    os.environ['IMAP_PASSWORD'] = 'right_password'
    os.environ['INBOX'] = 'right_mailbox'

else:
    log.debug('DEV_MODE flag not set, starting in production mode...')

    # Otherwise, use the real IMAP4_SSL class
    from imaplib import IMAP4_SSL


class HTMLTextExtractor(HTMLParser):
    """
    A utility class for extracting and processing plain text from HTML content.

    This class extends the `HTMLParser` class to allow parsing of HTML while
    selectively handling specific HTML elements. It removes script and style
    content, cleans up whitespace, and formats block elements to include
    structured newlines. It is particularly useful for extracting readable
    text from HTML documents.

    :ivar text_parts: List of accumulated text parts during parsing.
    :type text_parts: list[str]
    :ivar skip_data: Counter used to determine whether to skip adding text
       (e.g., when within <script> or <style> tags).
    :type skip_data: int
    """
    def __init__(self):
        """
        Manages the initialization of an object with text-related attributes.

        This initializer sets up the necessary attributes for managing and processing
        text data. It initializes an empty list to hold parts of text and a counter
        to handle skip-related operations.
        """
        super().__init__()
        self.text_parts = []
        self.skip_data = 0

    def handle_starttag(self, tag, attrs):
        """
        Handles the start of an HTML or XML tag encountered during parsing. If the tag
        is either 'script' or 'style', it increments the counter to skip their content.

        :param tag: The name of the tag encountered.
        :type tag: str
        :param attrs: A list of attributes of the tag, where each attribute is a tuple
            consisting of the attribute name and its value.
        :type attrs: list[tuple[str, str | None]]
        """
        if tag in ('script', 'style'):
            self.skip_data += 1

    def handle_endtag(self, tag):
        """
        Handles the closing HTML tags during parsing and performs actions based on the tag type.

        This function processes end tags encountered in HTML content. For script and
        style tags, it adjusts an internal counter to properly skip the data associated
        with these tags. For block elements such as paragraphs or headers, it appends
        a newline to the collected text data to reflect the proper structure of the
        HTML content.

        :param tag: The end tag that is being processed.
        :type tag: str
        """
        if tag in ('script', 'style'):
            self.skip_data -= 1
        # Add newline for block elements
        elif tag in ('p', 'div', 'br', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li'):
            self.text_parts.append('\n')

    def handle_data(self, data):
        """
        Handles input data by cleaning it and appending to internal storage.

        This method processes the given data by stripping whitespace from the
        input. If the cleaned text is not empty and the skip_data attribute
        is 0, it appends the processed text and a space to the internal list
        text_parts.

        :param data: Input string data to be processed.
        :type data: str
        """
        if self.skip_data == 0:
            # Clean up whitespace
            text = data.strip()
            if text:
                self.text_parts.append(text)
                self.text_parts.append(' ')

    def get_text(self):
        """
        Joins text parts into a single formatted string by removing extra whitespace
        and normalizing spacing. This method combines the text segments provided in
        `self.text_parts` while ensuring that excessive whitespace and newlines are
        cleaned up for consistent formatting.

        :raises AttributeError: If `self.text_parts` is not defined or is of an
            incompatible type.

        :return: A cleaned, formatted string combining all text parts.
        :rtype: str
        """
        text = ''.join(self.text_parts)
        # Replace multiple spaces with single space
        text = re.sub(r'\s+', ' ', text)
        # Replace multiple newlines with double newline
        text = re.sub(r'\n\s*\n', '\n\n', text)
        return text.strip()

    @classmethod
    def extract_text_from_html(cls, html_content):
        """
        Extracts text content from an HTML string using an HTML parser. In case of an
        error during the parsing process, it falls back to a simple regex-based
        approach to strip HTML tags.

        :param html_content: A string containing HTML content to extract text from.
        :type html_content: str
        :return: The extracted text content with HTML tags removed.
        :rtype: str
        """
        parser = cls()
        try:
            parser.feed(html_content)
            return parser.get_text()
        except Exception as e:
            log.warning(f"Error parsing HTML: {e}. Falling back to simple tag stripping.")
            # Fallback: simple regex-based tag stripping
            text = re.sub('<[^<]+?>', '', html_content)
            return text.strip()


class Mailclient(Singleton):
    """
    A mail client designed to handle operations like connecting to mail servers,
    logging in, fetching emails, sending emails via SMTP, managing inboxes,
    and maintaining secure connections. The class uses environment variables as
    default sources for credentials and server information, allowing for
    flexibility in deployment and configuration. It also incorporates connection
    reuse and cleanup mechanisms to manage resources efficiently.

    Usage of this class assumes familiarity with basic email protocols
    (IMAP and SMTP) and requires the presence of the necessary credentials for
    authentication.

    :ivar _connection: Connection object representing the IMAP server connection.
    :type _connection: Optional[IMAP4_SSL]
    :ivar _decoding_format: Format used to decode email content. Default is
        `iso-8859-1`, but can be set to `utf-8` or other formats as needed.
    :type _decoding_format: str
    :ivar _smtp_connection: Connection object for the SMTP server, used for sending
        emails. Defaults to None until a connection is established.
    :type _smtp_connection: Optional[smtplib.SMTP]
    :ivar _imap_server: IMAP server address, provided during instantiation or
        fetched from environment variables.
    :type _imap_server: Optional[str]
    :ivar _imap_port: IMAP server port, provided during instantiation or fetched
        from environment variables.
    :type _imap_port: Optional[int]
    :ivar _smtp_port: SMTP server port, provided during instantiation or fetched
        from environment variables. Defaults to 587 if not specified.
    :type _smtp_port: Optional[int]
    :ivar _username: Username used for authenticating with the mail servers.
    :type _username: Optional[str]
    :ivar _password: Password used for authenticating with the mail servers.
    :type _password: Optional[str]
    :ivar _inbox: Name of the currently selected inbox. Defaults to 'INBOX' or
        can be modified using environment variables.
    :type _inbox: Optional[str]
    """
    _connection = None  # Connection to the mail server
    _decoding_format = 'iso-8859-1'  # 'utf-8'

    def __init__(self, imap_server: str = None, imap_port: int = None, smtp_port: int = None,
                 username: str = None, password: str = None, inbox: str = None, *args, **kwargs):
        """
        Initialize the mail client with the provided server and credential details. The instance
        can connect to the IMAP server, log in using the specified credentials, select the
        desired inbox, and optionally connect to the SMTP server.

        :param imap_server: The IMAP server host. If not provided, the value is fetched from
            the 'IMAP_HOST' environment variable.
        :type imap_server: str, optional
        :param imap_port: The port for the IMAP server. If not specified, it is retrieved
            from the 'IMAP_PORT' environment variable.
        :type imap_port: int, optional
        :param smtp_port: The port for the SMTP server. Defaults to 587 if not provided,
            or if the 'SMTP_PORT' environment variable is not set.
        :type smtp_port: int, optional
        :param username: The username for authentication with the IMAP server. If not provided,
            it is fetched from the 'IMAP_USER' environment variable.
        :type username: str, optional
        :param password: The password for authentication with the IMAP server. If not provided,
            it is fetched from the 'IMAP_PASSWORD' environment variable.
        :type password: str, optional
        :param inbox: The name of the inbox to be selected. Defaults to 'INBOX' if not
            provided or if the 'INBOX' environment variable is not set.
        :type inbox: str, optional
        :param args: Additional positional arguments passed as is.
        :type args: tuple
        :param kwargs: Additional keyword arguments passed as is.
        :type kwargs: dict
        """
        # Initialize instance attributes
        self._smtp_connection = None

        if not imap_server:
            if os.getenv('IMAP_HOST'):
                imap_server = os.getenv('IMAP_HOST')
            else:
                log.error('No IMAP server provided and no IMAP_HOST environment variable set!')

        if not imap_port:
            if os.getenv('IMAP_PORT'):
                imap_port = int(os.getenv('IMAP_PORT'))
            else:
                log.error('No IMAP port provided and no IMAP_PORT environment variable set!')

        if not smtp_port:
            if os.getenv('SMTP_PORT'):
                smtp_port = int(os.getenv('SMTP_PORT'))
            else:
                log.warning('No SMTP port provided and no SMTP_PORT environment variable set! Using default 587.')
                smtp_port = 587

        if not username:
            if os.getenv('IMAP_USER'):
                username = os.getenv('IMAP_USER')
            else:
                log.error('No username provided and no IMAP_USER environment variable set!')

        if not password:
            if os.getenv('IMAP_PASSWORD'):
                password = os.getenv('IMAP_PASSWORD')
            else:
                log.error('No password provided and no IMAP_PASSWORD environment variable set!')

        if not inbox:
            try:
                if os.getenv('INBOX'):
                    inbox = os.getenv('INBOX')
            except Exception as e:
                log.info(f'No inbox provided and no INBOX environment variable set, defaulting to "INBOX", '
                         f'error: {e}')

        # Store credentials for later use
        self._imap_server = imap_server
        self._imap_port = imap_port
        self._smtp_port = smtp_port
        self._username = username
        self._password = password

        # Connect to the mail server if not connected already
        if not self._connection:
            self.connect(imap_server, imap_port)
            self.login(username, password)
        else:
            log.debug('Instance already connected, skipping connection and login.')

        # Select the inbox
        self._inbox = inbox
        self.select_inbox(inbox)

        log.debug('Mail client initialized')

    def __del__(self):
        """
        Destroy the mail client instance by ensuring that any established
        connections are properly closed before the object is garbage collected.

        The destructor method is triggered automatically when the instance is
        deleted. It ensures that open resources, such as connections to servers,
        are properly handled and released to avoid resource leaks.

        :return: None
        :rtype: None
        """
        if self._connection:
            self.close()

        if self._smtp_connection:
            self.close_smtp()

        log.debug('Mail client destroyed')

    def get_connection(self):
        """
        Retrieves the current connection instance that the object is utilizing.

        This method provides access to the underlying connection object managed by
        the enclosing class.

        :return: The connection instance being used.
        """
        return self._connection

    def get_inbox(self):
        """
        Retrieves the private `_inbox` attribute of the instance.

        This method provides access to the `_inbox` attribute, which is
        expected to store inbox-related data for the instance.

        :return: The current value of the instance's `_inbox` attribute.
        """
        return self._inbox

    def get__decoding_format(self):
        """
        Retrieves the decoding format used by the instance.

        :return: The decoding format.
        :rtype: str
        """
        return self._decoding_format

    def set_decoding_format(self, decoding_format: str):
        """
        Updates the decoding format used by the instance.

        This method allows the user to specify a new decoding format by
        setting the corresponding attribute. The decoding format determines
        how the instance processes and interprets data.

        :param decoding_format: The new decoding format to be set.
        :type decoding_format: str
        """
        self._decoding_format = decoding_format

    def connect(self, imap_server: str, imap_port: int):
        """
        Connects to the IMAP server using the provided server address and port. This method
        initializes a connection to the IMAP server and logs its status. In case of any
        exception during the connection process, an error is logged.

        :param imap_server: The hostname or IP address of the IMAP server.
        :type imap_server: str
        :param imap_port: The port number to connect to the IMAP server.
        :type imap_port: int
        """
        try:
            # Use the mock IMAP4_SSL class for testing
            self._connection = IMAP4_SSL(host=imap_server, port=imap_port)
            log.debug(f'Successfully connected to mailbox at {imap_server}:{imap_port}')

        except Exception as e:
            log.error(f'Error connecting to the mail server: {e}')

    def login(self, username: str, password: str):
        """
        Logs into the connected mail server using the provided credentials.

        This method attempts to log in to the mail server using a given username and
        password. It is required that the mail server is successfully connected before
        calling this method. If the connection is not established, the method will
        log an error and will not proceed with the login operation.

        :param username: The username required for authentication on the mail server.
        :type username: str
        :param password: The password associated with the provided username.
        :type password: str
        """
        if not self._connection:
            log.error('Not connected to any mail server at the moment, cannot login!')
            return

        self._connection.login(user=username, password=password)
        log.debug(f'Successfully logged in to the mail server using {username[:3]}, password {password[0]}')

    def close(self):
        """
        Closes the connection to the mail server and cleans up the connection object.

        This method ensures that the connection to the mail server is properly
        terminated by logging out and setting the internal connection attribute
        to None. It is important to call this method to release resources
        associated with the mail server.
        """
        log.debug('Closing the connection to the mail server...')

        self._connection.logout()
        self._connection = None

        log.debug('Connection server closed, mail set to none.')

    def connect_smtp(self, smtp_server: str = None, smtp_port: int = None):
        """
        Establishes an SMTP connection to the specified server and port. If server or
        port is not provided, it falls back to the default server and port values.
        The connection is secured using STARTTLS and authenticates with the provided
        username and password.

        :param smtp_server: The hostname of the SMTP server. Defaults to the configured
            IMAP server if not specified.
        :type smtp_server: str, optional
        :param smtp_port: The port number of the SMTP server. Defaults to 587 if not
            specified and if no alternative default is provided.
        :type smtp_port: int, optional
        :return: None
        :rtype: None
        :raises Exception: If there is an error connecting to or authenticating
            with the SMTP server.
        """
        try:
            if not smtp_server:
                smtp_server = self._imap_server
            if not smtp_port:
                smtp_port = self._smtp_port or 587

            self._smtp_connection = smtplib.SMTP(smtp_server, smtp_port)
            self._smtp_connection.starttls()  # Enable encryption
            self._smtp_connection.login(self._username, self._password)
            log.debug(f'Successfully connected to SMTP server at {smtp_server}:{smtp_port}')

        except Exception as e:
            log.error(f'Error connecting to SMTP server: {e}')
            self._smtp_connection = None
            raise

    def close_smtp(self):
        """
        Closes the currently active SMTP connection.

        This method ensures that the SMTP connection is properly terminated. If the
        connection exists, it attempts to execute the `quit` method to gracefully
        close it. Errors during this process are logged, and the connection is
        set to None in all cases. This is critical to prevent potential resource
        leaks when dealing with SMTP communications.

        :raises Exception: Any errors encountered during the closure of the SMTP
            connection are caught and logged, though the process is designed to
            continue with cleanup regardless of these errors.
        """
        if self._smtp_connection:
            try:
                self._smtp_connection.quit()
                log.debug('SMTP connection closed')
            except Exception as e:
                log.error(f'Error closing SMTP connection: {e}')
            finally:
                self._smtp_connection = None

    def select_inbox(self, inbox: str = None):
        """
        Selects the inbox to interact with on the mail server. If no inbox is provided, it defaults to the
        previously selected inbox stored in the instance or the default "INBOX". This method ensures that the
        connection to the mail server exists before attempting to select an inbox.

        :param inbox: The name of the inbox to be selected. Optional, defaults to None.
        :type inbox: str
        """
        if not self._connection:
            log.error('Not connected to any mail server at the moment, cannot select inbox!')
            return

        log.debug('Selecting inbox...')
        if not inbox and not self._inbox:
            self._connection.select('INBOX')
            self._inbox = 'INBOX'
            log.debug('No inbox provided, defaulting to "INBOX"')
        elif not inbox and self._inbox:
            self._connection.select(self._inbox)
            log.debug(f'No inbox provided, defaulting to {self._inbox}')
        else:
            self._connection.select(inbox)
            self._inbox = f'"{inbox}"'  # TODO: Check if quotation marks are necessary
            log.debug(f'Selected inbox: {inbox}')

    def list_inboxes(self):
        """
        Lists all inboxes available for the current connection.

        This function communicates with the email server through the
        current connection and retrieves a list of inbox directories.

        :return: A list of inboxes returned by the email server connection.
        :rtype: list
        """
        log.debug('Listing inboxes...')
        return self._connection.list()[1]

    def list_mails(self):
        """
        Lists all mails on the server for the connected user.

        This method sends a search request to the server to retrieve all available
        mails. The function uses the 'ALL' search criterion, which returns every mail
        available in the user's mailbox. It logs both the request initiation and the
        server's response status to provide clear traceability and debugging details.

        :return: A server response containing mail data or relevant information.
        :rtype: Any
        """
        log.debug('Listing mails...')
        status, response = self._connection.search(None, 'ALL')
        log.info('Requested mails, server responded with: %s', status)
        return response

    def get_mails(self, excluded_ids: list[int] = None) -> pd.DataFrame:
        """
        Fetches emails from the server, excluding those with IDs specified in the excluded_ids list. The
        function processes email messages, extracts their metadata, and returns a summary of the emails
        in a pandas DataFrame format. The metadata includes the email ID, subject, sender, date, and a
        truncated snippet of the email body. Email bodies are parsed and decoded based on content type
        (text or html). Exclusion of emails is optimized using a set for faster lookups.

        :param excluded_ids: A list of email IDs to be excluded from processing. If None, no exclusion is applied.
        :type excluded_ids: list[int] | None
        :return: A pandas DataFrame containing the processed email metadata: ID, Subject, From, Date, and Body Snippet.
        :rtype: pd.DataFrame
        """
        response = self.list_mails()
        email_ids = response[0].split()
        emails_data = []
        decoding_format = 'iso-8859-1'  # 'utf-8' 'iso-8859-1'

        # Convert excluded_ids to a set for faster lookup
        excluded_ids_set = set(excluded_ids) if excluded_ids else set()
        log.debug(f'Excluded ids set: {excluded_ids_set}')

        # Loop through email ids
        for email_id in email_ids:
            # Skip the email if its ID is in the excluded_ids set
            if int(email_id.decode(decoding_format)) in excluded_ids_set:
                log.debug(f'Skipping email {email_id} as it is in the excluded_ids list')
                continue

            # Fetch the email
            _, msg_data = self._connection.fetch(email_id, '(RFC822)')

            # Loop through the parts of the email
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

                    # Get email body
                    if email_message.is_multipart():
                        for part in email_message.walk():

                            # If the email part is text/plain, extract the body
                            if part.get_content_type() == "text/plain":
                                body = part.get_payload(decode=True).decode(decoding_format)
                                break

                            # If the email part is html, extract text using our HTML parser
                            elif part.get_content_type() == "text/html":
                                html_content = part.get_payload(decode=True).decode(decoding_format)
                                body = HTMLTextExtractor.extract_text_from_html(html_content)
                                break
                    else:
                        # If the email is not multipart, extract the body
                        body = email_message.get_payload(decode=True).decode(decoding_format)

                    # Truncate body to a snippet
                    body_snippet = body[:100] + '...' if len(body) > 100 else body

                    # Append the email data to the list
                    emails_data.append({
                        'ID': email_id.decode(decoding_format),
                        'Subject': subject,
                        'From': sender,
                        'Date': date,
                        'Body Snippet': body_snippet
                    })

        # Return the emails in a pandas DataFrame
        df = pd.DataFrame(emails_data)
        log.info(f'Retrieved {len(df)} emails')
        return df

    def get_attachments(self, email_id, content_type: str | None = 'application/pdf') -> list[Document]:
        """
        Extract and return a list of attachments from a given email, based on the specified content type.
        The method retrieves an email using its identifier, processes its content, and collects all
        attachments matching the specified content type. If no content type is provided, all attachments
        are retrieved. Attachments are returned as instances of classes `PDF` or `Document`.

        :param email_id: The unique identifier of the email to extract attachments from.
        :type email_id: str
        :param content_type: The MIME type of attachments to filter. By default, it is set to
                             'application/pdf'. If set to None, all content types are included.
        :type content_type: str | None
        :return: A list of attachments filtered and categorized as either `PDF` or `Document` objects.
        :rtype: list[Document]
        """
        log.debug(f'Downloading attachments from email {email_id}')
        try:
            # Fetch the email
            _, msg_data = self._connection.fetch(email_id, '(RFC822)')
            raw_email = msg_data[0][1]

            # Parse the email
            email_message = email.message_from_bytes(raw_email)

            # List to store attachments in
            attachments = []

            # Walk through the email parts and look for attachments
            for part in email_message.walk():
                if part.get_content_maintype() == 'multipart':
                    continue
                elif part.get('Content-Disposition') is None:
                    continue
                elif part.get_content_type() == content_type or content_type is None:
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
                    if content_type == 'application/pdf':
                        attachments.append(PDF(
                            content=attachment_data,
                            email_id=email_id,
                            attributes={
                                'filename': filename,
                                'content_type': part.get_content_type(),
                                'email_id': email_id,  # TODO: Using the attributes is deprecated,
                                #  use the 'email_id' directly in the PDF class
                                'sender': email_message['From'],
                                'date': email_message['Date']
                            }
                        ))
                    else:
                        attachments.append(Document(
                            content=attachment_data,
                            attributes={
                                'filename': filename,
                                'email_id': email_id,
                                'content_type': part.get_content_type(),
                                'sender': email_message['From'],
                                'date': email_message['Date']
                            }
                        ))
                else:
                    log.debug(f'Skipping attachment with content type {part.get_content_type()}')

            if attachments:
                log.info(f'Found {len(attachments)} attachments in email {email_id}')
            else:
                log.info(f'No attachments found in mail {email_id}')

            # Return the attachments, if non are found list will be empty
            return attachments

        except Exception as e:
            print(email_id)
            log.error(f"Error processing email {email_id}: {str(e)}")
            return []

    def send_email(self, to_email: Union[str, List[str]], subject: str, body: str = None,
                   html_body: str = None, attachments: Dict[str, bytes] = None,
                   cc: Union[str, List[str]] = None, bcc: Union[str, List[str]] = None,
                   reply_to: str = None) -> bool:
        """
        Sends an email with optional text body, HTML body, attachments, CC, BCC, and reply-to address.

        This function facilitates sending an email using a configured SMTP connection. It supports
        sending to multiple recipients, adding CC and BCC recipients, and attaching files. Both
        plain text and HTML content can be included in the email. If the connection is not
        established, it ensures the SMTP connection is created before sending the message.

        Parameters should be correctly formatted to support optional features such as attachments
        and carbon copy lists.

        :param to_email: The primary recipient(s) of the email. Can be a single email address or a list
            of addresses.
        :type to_email: Union[str, List[str]]
        :param subject: The subject line of the email.
        :type subject: str
        :param body: The plain text body of the email. Optional.
        :type body: str
        :param html_body: The HTML body of the email for rich formatting. Optional.
        :type html_body: str
        :param attachments: A dictionary of file names mapped to their binary content, for adding
            file attachments. Optional.
        :type attachments: Dict[str, bytes]
        :param cc: Carbon copy recipient(s). Can be a single address or a list of addresses. Optional.
        :type cc: Union[str, List[str]]
        :param bcc: Blind carbon copy recipient(s). Can be a single address or a list of addresses.
            Optional.
        :type bcc: Union[str, List[str]]
        :param reply_to: The reply-to address for responses to the email. Optional.
        :type reply_to: str
        :return: Returns True if the email was successfully sent, else False.
        :rtype: bool
        """
        try:
            # Create message
            msg = MIMEMultipart('alternative') if html_body else MIMEMultipart()
            msg['From'] = self._username
            msg['Subject'] = subject

            # Handle multiple recipients
            if isinstance(to_email, list):
                msg['To'] = ', '.join(to_email)
            else:
                msg['To'] = to_email

            if cc:
                if isinstance(cc, list):
                    msg['Cc'] = ', '.join(cc)
                else:
                    msg['Cc'] = cc

            if reply_to:
                msg['Reply-To'] = reply_to

            # Add text body
            if body:
                msg.attach(MIMEText(body, 'plain'))

            # Add HTML body
            if html_body:
                msg.attach(MIMEText(html_body, 'html'))

            # Add attachments
            if attachments:
                for filename, file_data in attachments.items():
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(file_data)
                    encoders.encode_base64(part)
                    part.add_header('Content-Disposition', f'attachment; filename= {filename}')
                    msg.attach(part)

            # Connect to SMTP if not already connected
            if not self._smtp_connection:
                self.connect_smtp()

            # Collect all recipients
            all_recipients = []
            if isinstance(to_email, list):
                all_recipients.extend(to_email)
            else:
                all_recipients.append(to_email)

            if cc:
                if isinstance(cc, list):
                    all_recipients.extend(cc)
                else:
                    all_recipients.append(cc)

            if bcc:
                if isinstance(bcc, list):
                    all_recipients.extend(bcc)
                else:
                    all_recipients.append(bcc)

            # Send the email
            self._smtp_connection.send_message(msg, to_addrs=all_recipients)
            log.info(f'Email sent successfully to {to_email} with subject: {subject}')
            return True

        except Exception as e:
            log.error(f'Error sending email: {e}')
            return False

    def send_email_from_template(self, to_email: Union[str, List[str]], subject: str,
                                 template_path: str, template_vars: Dict[str, str] = None,
                                 attachments: Dict[str, bytes] = None,
                                 inline_images: Dict[str, str] = None) -> bool:
        """
        Sends an email using a pre-defined HTML template while substituting variables, attaching files, and optionally adding inline images.

        This method reads an email template from the file system, substitutes placeholders with the provided template variables, attaches files
        to the email, and includes inline images if specified. It connects to an SMTP server if not already connected and sends the email to
        the specified recipients. The function handles single or multiple recipients.

        :param to_email: Recipient email address or a list of email addresses.
        :type to_email: Union[str, List[str]
        :param subject: Subject line of the email.
        :type subject: str
        :param template_path: File path to the email template.
        :type template_path: str
        :param template_vars: Dictionary of variables to substitute in the template, where keys correspond to placeholders in the template
            and values are the replacement strings.
        :type template_vars: Dict[str, str], optional
        :param attachments: Dictionary of file names and their corresponding content in binary format (bytes) to be attached to the email.
        :type attachments: Dict[str, bytes], optional
        :param inline_images: Dictionary mapping content IDs (used in the email template) to the file paths of the inline images.
        :type inline_images: Dict[str, str], optional
        :return: Whether the email was successfully sent.
        :rtype: bool
        """
        try:
            # Read template
            if not os.path.exists(template_path):
                log.error(f'Template file not found: {template_path}')
                return False

            with open(template_path, 'r', encoding='utf-8') as file:
                html_content = file.read()

            # Replace template variables
            if template_vars:
                for key, value in template_vars.items():
                    html_content = html_content.replace(f'{{{{{key}}}}}', str(value))

            # Create message with inline images support
            msg = MIMEMultipart('related')
            msg['From'] = self._username
            msg['Subject'] = subject

            # Handle multiple recipients
            if isinstance(to_email, list):
                msg['To'] = ', '.join(to_email)
            else:
                msg['To'] = to_email

            # Create the HTML part
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)

            # Add inline images
            if inline_images:
                for cid, image_path in inline_images.items():
                    if os.path.exists(image_path):
                        with open(image_path, 'rb') as img_file:
                            img = MIMEImage(img_file.read())
                            img.add_header('Content-ID', f'<{cid}>')
                            msg.attach(img)
                    else:
                        log.warning(f'Inline image not found: {image_path}')

            # Add attachments
            if attachments:
                for filename, file_data in attachments.items():
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(file_data)
                    encoders.encode_base64(part)
                    part.add_header('Content-Disposition', f'attachment; filename= {filename}')
                    msg.attach(part)

            # Connect to SMTP if not already connected
            if not self._smtp_connection:
                self.connect_smtp()

            # Send the email
            self._smtp_connection.send_message(msg)
            log.info(f'Template email sent successfully to {to_email} with subject: {subject}')
            return True

        except Exception as e:
            log.error(f'Error sending template email: {e}')
            return False

    def send_reminder_email(self, to_email: str, client_name: str, bafin_id: str,
                            days_overdue: int = None, custom_message: str = None,
                            template_path: str = None) -> bool:
        """
        Sends a reminder email to a client about outstanding documents using a template.

        This method allows sending a customized reminder email about overdue documents
        to a given email address. It uses template-based email generation, with optional
        inputs such as days overdue, a custom message, and the path to the email template.
        If no template path is provided, a default template path is used. The method also
        checks for the existence of a logo file in the template directory and includes
        it as an inline image if present.

        :param to_email: Recipient's email address.
        :type to_email: str
        :param client_name: Name of the client.
        :type client_name: str
        :param bafin_id: Reference identifier for the client within the system.
        :type bafin_id: str
        :param days_overdue: Number of days the documents are overdue (optional).
        :type days_overdue: int, optional
        :param custom_message: Additional custom message to include in the email (optional).
        :type custom_message: str, optional
        :param template_path: Path to the email template file (optional).
        :type template_path: str, optional
        :return: Boolean indicating whether the email was successfully sent.
        :rtype: bool
        """
        # Use provided template or default template path
        if not template_path:
            # Default template location - in filesystem directory
            filesystem_path = os.getenv('FILESYSTEM_PATH', './.filesystem')
            template_path = os.path.join(filesystem_path, 'email_templates', 'reminder_template.html')

        # Create subject
        subject = f"Reminder: Outstanding Documents (Reference: {bafin_id})"

        # Prepare template variables
        template_vars = {
            'client_name': client_name,
            'bafin_id': bafin_id,
            'days_overdue_text': '',
            'custom_message_text': ''
        }

        # Add optional overdue days text
        if days_overdue:
            template_vars['days_overdue_text'] = f'<p style="color: #cc0000;"><strong>The documents are {days_overdue} days overdue.</strong></p>'

        # Add optional custom message
        if custom_message:
            template_vars['custom_message_text'] = f'<p><em>{custom_message}</em></p>'

        # Check for logo in the same directory
        template_dir = os.path.dirname(template_path)
        logo_path = os.path.join(template_dir, 'logo.png')
        inline_images = {'logo': logo_path} if os.path.exists(logo_path) else None

        # Send using template
        return self.send_email_from_template(
            to_email=to_email,
            subject=subject,
            template_path=template_path,
            template_vars=template_vars,
            inline_images=inline_images
        )

    def send_confirmation_email(self, to_email: str, client_name: str, bafin_id: str,
                                case_id: int, template_path: str = None) -> bool:
        """
        Sends a confirmation email using a specified or default HTML template. Also includes functionality
        to handle missing templates by logging a warning and falling back to a basic template if necessary.
        The email includes embedded variable content (e.g., client name, case ID) and may optionally attach
        inline images such as a logo.

        :param to_email: Recipient email address.
        :type to_email: str
        :param client_name: Name of the client to personalize the email content.
        :type client_name: str
        :param bafin_id: A unique identifier related to BaFin (Federal Financial Supervisory Authority).
        :type bafin_id: str
        :param case_id: Numeric identifier for the case or reference.
        :type case_id: int
        :param template_path: Path to the email template file. Default template is used if not provided.
        :type template_path: str, optional
        :return: Whether the email was successfully sent.
        :rtype: bool
        """
        # Use provided template or default template path
        if not template_path:
            # Default template location - in filesystem directory
            filesystem_path = os.getenv('FILESYSTEM_PATH', './.filesystem')
            template_path = os.path.join(filesystem_path, 'email_templates', 'response_template.html')

        # Check if template exists, if not log warning
        if not os.path.exists(template_path):
            log.warning(f'Template file not found at {template_path}, falling back to basic template')
            # You could either return False here or use a very basic fallback
            # For now, let's try a basic fallback
            return self._send_basic_confirmation_email(to_email, client_name, bafin_id, case_id)

        # Prepare template variables
        template_vars = {
            'client_name': client_name,
            'bafin_id': bafin_id,
            'case_id': case_id
        }

        # Check if we need inline images (like logo)
        template_dir = os.path.dirname(template_path)
        logo_path = os.path.join(template_dir, 'logo.png')
        inline_images = {'logo': logo_path} if os.path.exists(logo_path) else None

        return self.send_email_from_template(
            to_email=to_email,
            subject=f"Confirmation: Documents Received (Reference: {bafin_id})",
            template_path=template_path,
            template_vars=template_vars,
            inline_images=inline_images
        )


    def _send_basic_confirmation_email(self, to_email: str, client_name: str, bafin_id: str, case_id: int) -> bool:
        """
        Send a basic confirmation email to confirm receipt of submitted documents.

        This method prepares and sends a plain text email to the client, confirming the
        receipt of documents and providing reference information about the submission.
        The email includes details such as the client's name, BaFin ID, and the case ID
        assigned to the submission. A generic automated message disclaimer is also
        included for clarity.

        :param to_email: The recipient's email address.
        :type to_email: str
        :param client_name: The name of the client whose documents are being confirmed.
        :type client_name: str
        :param bafin_id: A unique identifier (BaFin ID) associated with the client's submission.
        :type bafin_id: str
        :param case_id: An integer representing the case number assigned to the submission.
        :type case_id: int
        :return: A boolean indicating whether the email was sent successfully.
        :rtype: bool
        """
        subject = f"Confirmation: Documents Received (Reference: {bafin_id})"

        # Basic plain text email as fallback
        body = f"""
            Dear Sir/Madam,

            Thank you for submitting your documents.
            
            We confirm receipt of the documents for {client_name} (Reference ID: {bafin_id}).
            Your submission is now being processed (Case Number: {case_id}).
            
            We will notify you once the review is complete.
            You will receive a confirmation copy for your records.
            
            Best regards,
            Audit Team
            
            ---
            This is an automated message. Please do not reply to this email.
            For questions, please contact your designated representative.
            """

        return self.send_email(
            to_email=to_email,
            subject=subject,
            body=body
        )

    def mark_email_as_read(self, email_id: str) -> bool:
        """
        Marks the specified email as read by adding the '\\Seen' flag to the email.

        This method interacts with an email server connection object to mark an email
        as read. The provided email identification is processed and converted to a
        byte object if it is initially passed as a string. If the operation succeeds,
        the function logs the success and returns True; otherwise, it logs an error
        and returns False.

        :param email_id: The unique identification of the email to mark as read.
        :type email_id: str
        :return: True if the email was successfully marked as read; False otherwise.
        :rtype: bool
        """
        try:
            # Convert string ID to bytes if necessary
            if isinstance(email_id, str):
                email_id = email_id.encode()

            self._connection.store(email_id, '+FLAGS', '\\Seen')
            log.debug(f"Marked email {email_id} as read")
            return True
        except Exception as e:
            log.error(f"Error marking email as read: {e}")
            return False

    def mark_email_as_answered(self, email_id: str) -> bool:
        """
        Marks an email as answered by updating its flags on the server.

        This method interacts with the email server to mark the specified email
        as answered by adding the '\\Answered' flag to it. It logs the action
        for auditing purposes and handles any errors that may occur during the
        operation. An email ID is used as input for this operation, and a boolean
        status is returned to indicate success or failure of the operation.

        :param email_id: The unique identifier of the email to be marked as answered.
        :type email_id: str
        :return: True if the email was successfully marked as answered; otherwise, False.
        :rtype: bool
        """
        try:
            # Convert string ID to bytes if necessary
            if isinstance(email_id, str):
                email_id = email_id.encode()

            self._connection.store(email_id, '+FLAGS', '\\Answered')
            log.debug(f"Marked email {email_id} as answered")
            return True
        except Exception as e:
            log.error(f"Error marking email as answered: {e}")
            return False

    @staticmethod
    def get_template_directory():
        """
        Retrieves the directory path for email templates. This method constructs
        the path by fetching the base filesystem directory from the `FILESYSTEM_PATH`
        environment variable. If the environment variable is not set, it defaults
        to `./.filesystem`. The function then appends the subdirectory
        `email_templates` to this base path.

        :return: The full path to the email template directory.
        :rtype: str
        """
        filesystem_path = os.getenv('FILESYSTEM_PATH', './.filesystem')
        return os.path.join(filesystem_path, 'email_templates')

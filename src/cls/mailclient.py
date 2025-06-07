"""
This module holds the mail.Client class.
"""
import os
import logging
import email
from email.header import decode_header
from bs4 import BeautifulSoup
import pandas as pd
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.base import MIMEBase
from email import encoders
import smtplib
from typing import Dict, List, Union

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


# TODO: Refactor this class to use pythons email library instead of BeautifulSoup
class Mailclient(Singleton):
    """
    This class is used to connect and interact with the mail server.
    It uses the custom singleton class to ensure only one instance of the class is created.

    The class uses the imaplib library to connect to the mail server and offers
    a bunch of methods to interact with the mailbox.
    """
    _connection = None  # Connection to the mail server
    _decoding_format = 'iso-8859-1'  # 'utf-8'

    def __init__(self, imap_server: str = None, imap_port: int = None, smtp_port: int = None,
                 username: str = None, password: str = None, inbox: str = None, *args, **kwargs):
        """
        Automatically connects to the mailclient, using the provided credentials,
        once the class is instantiated.

        Parameters are optional and will be fetched from the environment variables if not specified.
        If no inbox is provided, it will default to the 'INBOX'.
        It also defines a custom logger for the class.

        :param imap_server: The imap server to connect to.
        :param imap_port: The port of the imap server.
        :param smtp_port: The port of the smtp server.
        :param username: The username/mail to connect to.
        :param password: The user's password.
        :param inbox: Inbox to connect to. Defaults to None.
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
        Destructor for the mailbox class.
        Automatically closes the connection to the server when the class is destroyed.
        """
        if self._connection:
            self.close()

        if self._smtp_connection:
            self.close_smtp()

        log.debug('Mail client destroyed')

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
            # Use the mock IMAP4_SSL class for testing
            self._connection = IMAP4_SSL(host=imap_server, port=imap_port)
            log.debug(f'Successfully connected to mailbox at {imap_server}:{imap_port}')

        except Exception as e:
            log.error(f'Error connecting to the mail server: {e}')

    def login(self, username: str, password: str):
        """
        Method to login to the mail server.

        :param username: The username to login with.
        :param password: The password to login with.
        """
        if not self._connection:
            log.error('Not connected to any mail server at the moment, cannot login!')
            return

        self._connection.login(user=username, password=password)
        log.debug(f'Successfully logged in to the mail server using {username[:3]}, password {password[0]}')

    def close(self):
        """
        Closes the mailclient and logs out of the server.
        Sets the mail attribute to None.
        """
        log.debug('Closing the connection to the mail server...')

        self._connection.logout()
        self._connection = None

        log.debug('Connection server closed, mail set to none.')

    def connect_smtp(self, smtp_server: str = None, smtp_port: int = None):
        """
        Connect to SMTP server for sending emails.

        :param smtp_server: SMTP server address (uses IMAP server if not provided)
        :param smtp_port: SMTP port (uses stored port or defaults to 587)
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
        Close the SMTP connection.
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
        Method to select an inbox.

        :param inbox: The inbox to select.
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
        Method to get a list of possible inboxes.
        """
        log.debug('Listing inboxes...')
        return self._connection.list()[1]

    def list_mails(self):
        """
        Method to list the mails in the selected inbox.
        """
        log.debug('Listing mails...')
        status, response = self._connection.search(None, 'ALL')
        log.info('Requested mails, server responded with: %s', status)
        return response

    def get_mails(self, excluded_ids: list[int] = None) -> pd.DataFrame:
        """
        Method to list the mails in the selected inbox and return them as a pandas DataFrame.
        Excludes the emails with IDs present in the excluded_ids list.

        :param excluded_ids: A list of email IDs to exclude from the result.
        :return: A pandas DataFrame containing the emails.
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

                            # If the email part is html, use BeautifulSoup to extract text
                            elif part.get_content_type() == "text/html":
                                body = BeautifulSoup(part.get_payload(decode=True).decode(decoding_format),
                                                     'html.parser').get_text()
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
        Method to get the attachments of an email.

        :param email_id: The id of the email to get the attachments from.
        :param content_type: The content type of the attachments to look for.
        :return: A list of attachments or an empty list if no attachments are found.
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
        Send an email using SMTP.

        :param to_email: Recipient email address(es)
        :param subject: Email subject
        :param body: Plain text body (optional)
        :param html_body: HTML body (optional)
        :param attachments: Dictionary of {filename: file_bytes} (optional)
        :param cc: CC recipients (optional)
        :param bcc: BCC recipients (optional)
        :param reply_to: Reply-to address (optional)
        :return: True if email was sent successfully, False otherwise
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
        Send an email using an HTML template.

        :param to_email: Recipient email address(es)
        :param subject: Email subject
        :param template_path: Path to HTML template file
        :param template_vars: Dictionary of variables to replace in template
        :param attachments: Dictionary of {filename: file_bytes} (optional)
        :param inline_images: Dictionary of {cid: image_path} for inline images (optional)
        :return: True if email was sent successfully, False otherwise
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
        Send a reminder email to a client about missing documents.

        :param to_email: Client email address
        :param client_name: Client organization name
        :param bafin_id: Client reference ID
        :param days_overdue: Number of days overdue (optional)
        :param custom_message: Custom message to include (optional)
        :param template_path: Path to custom template file (optional)
        :return: True if email was sent successfully, False otherwise
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
        Send a confirmation email after documents have been received.

        :param to_email: Client email address
        :param client_name: Client institute name
        :param bafin_id: Client BaFin ID
        :param case_id: Audit case ID
        :param template_path: Optional path to custom template
        :return: True if email was sent successfully, False otherwise
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
        def _send_basic_confirmation_email(self, to_email: str, client_name: str, bafin_id: str, case_id: int) -> bool:
            """
            Send a basic confirmation email without a template file.
            This is a fallback method when the template file is not found.

            :param to_email: Client email address
            :param client_name: Client institute name
            :param bafin_id: Client reference ID
            :param case_id: Audit case ID
            :return: True if email was sent successfully, False otherwise
            """
            subject = f"Confirmation: Documents Received (Reference: {bafin_id})"

            # Basic plain text email as fallback
            body = f"""Dear Sir/Madam,

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
        Mark an email as read.

        :param email_id: The ID of the email to mark as read
        :return: True if successful, False otherwise
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
        Mark an email as answered/replied.

        :param email_id: The ID of the email to mark as answered
        :return: True if successful, False otherwise
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
        Get the default directory for email templates.
        Templates are stored in the filesystem directory alongside certificate templates

        :return: Path to the template directory
        """
        filesystem_path = os.getenv('FILESYSTEM_PATH', './.filesystem')
        return os.path.join(filesystem_path, 'email_templates')

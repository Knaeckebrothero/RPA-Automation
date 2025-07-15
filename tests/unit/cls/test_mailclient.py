"""
Unit tests for the Mailclient class.

This module contains tests for the Mailclient class functionality, including
initialization, connection management, email retrieval, and email sending.
"""
import os
import pytest
import email
from unittest.mock import patch, MagicMock, mock_open, ANY
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from cls.mailclient import Mailclient, HTMLTextExtractor


class TestHTMLTextExtractor:
    """Test suite for the HTMLTextExtractor class."""

    def test_extract_text_from_html_simple(self):
        """Test extracting text from a simple HTML string."""
        html = "<html><body><p>Test paragraph</p><div>Test div</div></body></html>"
        text = HTMLTextExtractor.extract_text_from_html(html)
        
        assert "Test paragraph" in text
        assert "Test div" in text

    def test_extract_text_from_html_with_script(self):
        """Test extracting text from HTML with script tags."""
        html = """
        <html>
            <body>
                <p>Visible text</p>
                <script>
                    var hidden = 'This should not be visible';
                </script>
                <div>More visible text</div>
            </body>
        </html>
        """
        text = HTMLTextExtractor.extract_text_from_html(html)
        
        assert "Visible text" in text
        assert "More visible text" in text
        assert "This should not be visible" not in text

    def test_extract_text_from_html_with_style(self):
        """Test extracting text from HTML with style tags."""
        html = """
        <html>
            <head>
                <style>
                    body { font-family: Arial; }
                </style>
            </head>
            <body>
                <p>Visible text</p>
                <div>More visible text</div>
            </body>
        </html>
        """
        text = HTMLTextExtractor.extract_text_from_html(html)
        
        assert "Visible text" in text
        assert "More visible text" in text
        assert "font-family" not in text

    def test_extract_text_from_html_with_nested_tags(self):
        """Test extracting text from HTML with nested tags."""
        html = """
        <html>
            <body>
                <div>
                    <h1>Header</h1>
                    <p>Paragraph <strong>with bold text</strong> and <em>italic text</em>.</p>
                    <ul>
                        <li>Item 1</li>
                        <li>Item 2</li>
                    </ul>
                </div>
            </body>
        </html>
        """
        text = HTMLTextExtractor.extract_text_from_html(html)
        
        assert "Header" in text
        assert "Paragraph with bold text and italic text" in text
        assert "Item 1" in text
        assert "Item 2" in text


class TestMailclient:
    """Test suite for the Mailclient class."""

    @patch.dict(os.environ, {
        'IMAP_HOST': 'test.mail.server',
        'IMAP_PORT': '993',
        'IMAP_USER': 'test@example.com',
        'IMAP_PASSWORD': 'test_password',
        'INBOX': 'INBOX',
        'SMTP_HOST': 'test.smtp.server',
        'SMTP_PORT': '587'
    })
    @patch('cls.mailclient.IMAP4_SSL')
    def test_mailclient_initialization(self, mock_imap_class):
        """Test Mailclient initialization with environment variables."""
        # Set up the mock
        mock_imap = MagicMock()
        mock_imap_class.return_value = mock_imap
        
        # Create a Mailclient instance
        client = Mailclient()
        
        # Verify that the instance was initialized correctly
        assert client._imap_server == 'test.mail.server'
        assert client._imap_port == 993
        assert client._username == 'test@example.com'
        assert client._password == 'test_password'
        
        # Verify that connect and login were called
        mock_imap_class.assert_called_once_with(host='test.mail.server', port=993)
        mock_imap.login.assert_called_once_with(user='test@example.com', password='test_password')
        mock_imap.select.assert_called_once()

    @patch('cls.mailclient.IMAP4_SSL')
    def test_mailclient_initialization_with_parameters(self, mock_imap_class):
        """Test Mailclient initialization with explicit parameters."""
        # Set up the mock
        mock_imap = MagicMock()
        mock_imap_class.return_value = mock_imap
        
        # Create a Mailclient instance with explicit parameters
        client = Mailclient(
            imap_server='custom.mail.server',
            imap_port=1234,
            username='custom@example.com',
            password='custom_password',
            inbox='CUSTOM_INBOX'
        )
        
        # Verify that the instance was initialized correctly
        assert client._imap_server == 'custom.mail.server'
        assert client._imap_port == 1234
        assert client._username == 'custom@example.com'
        assert client._password == 'custom_password'
        
        # Verify that connect and login were called with the correct parameters
        mock_imap_class.assert_called_once_with(host='custom.mail.server', port=1234)
        mock_imap.login.assert_called_once_with(user='custom@example.com', password='custom_password')
        mock_imap.select.assert_called_once()

    @patch('cls.mailclient.IMAP4_SSL')
    def test_connect(self, mock_imap_class):
        """Test the connect method."""
        # Set up the mock
        mock_imap = MagicMock()
        mock_imap_class.return_value = mock_imap
        
        # Create a Mailclient instance without auto-connecting
        client = Mailclient.__new__(Mailclient)
        client._connection = None
        
        # Call the connect method
        client.connect('test.mail.server', 993)
        
        # Verify that the connection was established
        mock_imap_class.assert_called_once_with(host='test.mail.server', port=993)
        assert client._connection is not None

    @patch('cls.mailclient.IMAP4_SSL')
    def test_login(self, mock_imap_class):
        """Test the login method."""
        # Set up the mock
        mock_imap = MagicMock()
        mock_imap_class.return_value = mock_imap
        
        # Create a Mailclient instance without auto-connecting
        client = Mailclient.__new__(Mailclient)
        client._connection = mock_imap
        
        # Call the login method
        client.login('test@example.com', 'test_password')
        
        # Verify that login was called
        mock_imap.login.assert_called_once_with(user='test@example.com', password='test_password')

    @patch('cls.mailclient.IMAP4_SSL')
    def test_close(self, mock_imap_class):
        """Test the close method."""
        # Set up the mock
        mock_imap = MagicMock()
        mock_imap_class.return_value = mock_imap
        
        # Create a Mailclient instance
        client = Mailclient.__new__(Mailclient)
        client._connection = mock_imap
        
        # Call the close method
        client.close()
        
        # Verify that logout was called and connection was set to None
        mock_imap.logout.assert_called_once()
        assert client._connection is None

    @patch('smtplib.SMTP')
    def test_connect_smtp(self, mock_smtp_class):
        """Test the connect_smtp method."""
        # Set up the mock
        mock_smtp = MagicMock()
        mock_smtp_class.return_value = mock_smtp
        
        # Create a Mailclient instance
        client = Mailclient.__new__(Mailclient)
        client._imap_server = 'test.mail.server'
        client._smtp_port = 587
        client._username = 'test@example.com'
        client._password = 'test_password'
        client._smtp_connection = None
        
        # Call the connect_smtp method
        client.connect_smtp()
        
        # Verify that the SMTP connection was established
        mock_smtp_class.assert_called_once_with('test.mail.server', 587)
        mock_smtp.starttls.assert_called_once()
        mock_smtp.login.assert_called_once_with('test@example.com', 'test_password')
        assert client._smtp_connection is not None

    @patch('smtplib.SMTP')
    def test_close_smtp(self, mock_smtp_class):
        """Test the close_smtp method."""
        # Set up the mock
        mock_smtp = MagicMock()
        mock_smtp_class.return_value = mock_smtp
        
        # Create a Mailclient instance
        client = Mailclient.__new__(Mailclient)
        client._smtp_connection = mock_smtp
        
        # Call the close_smtp method
        client.close_smtp()
        
        # Verify that quit was called and connection was set to None
        mock_smtp.quit.assert_called_once()
        assert client._smtp_connection is None

    @patch('cls.mailclient.IMAP4_SSL')
    def test_select_inbox(self, mock_imap_class):
        """Test the select_inbox method."""
        # Set up the mock
        mock_imap = MagicMock()
        mock_imap_class.return_value = mock_imap
        mock_imap.select.return_value = ('OK', [b'1'])
        
        # Create a Mailclient instance
        client = Mailclient.__new__(Mailclient)
        client._connection = mock_imap
        
        # Call the select_inbox method
        client.select_inbox('INBOX')
        
        # Verify that select was called
        mock_imap.select.assert_called_once_with('INBOX')

    @patch('cls.mailclient.IMAP4_SSL')
    def test_list_inboxes(self, mock_imap_class):
        """Test the list_inboxes method."""
        # Set up the mock
        mock_imap = MagicMock()
        mock_imap_class.return_value = mock_imap
        mock_imap.list.return_value = ('OK', [b'(\\HasNoChildren) "/" "INBOX"', b'(\\HasNoChildren) "/" "Sent"'])
        
        # Create a Mailclient instance
        client = Mailclient.__new__(Mailclient)
        client._connection = mock_imap
        
        # Call the list_inboxes method
        response = client.list_inboxes()
        
        # Verify that list was called and the response is correct
        mock_imap.list.assert_called_once()
        assert response == ('OK', [b'(\\HasNoChildren) "/" "INBOX"', b'(\\HasNoChildren) "/" "Sent"'])

    @patch('cls.mailclient.IMAP4_SSL')
    def test_list_mails(self, mock_imap_class):
        """Test the list_mails method."""
        # Set up the mock
        mock_imap = MagicMock()
        mock_imap_class.return_value = mock_imap
        mock_imap.search.return_value = ('OK', [b'1 2 3'])
        
        # Create a Mailclient instance
        client = Mailclient.__new__(Mailclient)
        client._connection = mock_imap
        
        # Call the list_mails method
        response = client.list_mails()
        
        # Verify that search was called and the response is correct
        mock_imap.search.assert_called_once_with(None, 'ALL')
        assert response == [b'1 2 3']

    @patch('cls.mailclient.IMAP4_SSL')
    @patch('email.message_from_bytes')
    @patch('cls.mailclient.HTMLTextExtractor.extract_text_from_html')
    def test_get_mails(self, mock_extract_text, mock_message_from_bytes, mock_imap_class):
        """Test the get_mails method."""
        # Set up the mocks
        mock_imap = MagicMock()
        mock_imap_class.return_value = mock_imap
        mock_imap.search.return_value = ('OK', [b'1 2 3'])
        
        # Mock the fetch response
        mock_fetch_response = [(b'1', b'EMAIL_DATA')]
        mock_imap.fetch.return_value = ('OK', mock_fetch_response)
        
        # Mock the email message
        mock_email = MagicMock()
        mock_message_from_bytes.return_value = mock_email
        mock_email.__getitem__.side_effect = lambda key: {
            'Subject': 'Test Subject',
            'From': 'sender@example.com',
            'Date': '2023-01-01'
        }[key]
        mock_email.is_multipart.return_value = False
        mock_email.get_payload.return_value = b'Test email body'
        
        # Mock the HTML text extraction
        mock_extract_text.return_value = 'Extracted HTML text'
        
        # Create a Mailclient instance
        client = Mailclient.__new__(Mailclient)
        client._connection = mock_imap
        
        # Call the get_mails method
        result = client.get_mails()
        
        # Verify the result
        assert len(result) == 3  # Should have 3 emails
        assert 'ID' in result.columns
        assert 'Subject' in result.columns
        assert 'From' in result.columns
        assert 'Date' in result.columns
        assert 'Body Snippet' in result.columns

    @patch('cls.mailclient.IMAP4_SSL')
    def test_get_attachments(self, mock_imap_class):
        """Test the get_attachments method."""
        # Set up the mock
        mock_imap = MagicMock()
        mock_imap_class.return_value = mock_imap
        
        # Mock the fetch response
        mock_fetch_response = [(b'1', b'EMAIL_DATA')]
        mock_imap.fetch.return_value = ('OK', mock_fetch_response)
        
        # Mock the email message
        mock_email = MagicMock()
        with patch('email.message_from_bytes', return_value=mock_email):
            # Set up the email parts
            part1 = MagicMock()
            part1.get_content_maintype.return_value = 'multipart'
            
            part2 = MagicMock()
            part2.get_content_maintype.return_value = 'application'
            part2.get_content_type.return_value = 'application/pdf'
            part2.get_filename.return_value = 'test.pdf'
            part2.get_payload.return_value = 'PDF_CONTENT'
            
            # Set up the email walk method to return the parts
            mock_email.walk.return_value = [part1, part2]
            
            # Create a Mailclient instance
            client = Mailclient.__new__(Mailclient)
            client._connection = mock_imap
            
            # Call the get_attachments method
            with patch('cls.document.PDF') as mock_pdf:
                mock_pdf_instance = MagicMock()
                mock_pdf.return_value = mock_pdf_instance
                
                attachments = client.get_attachments('1')
                
                # Verify that fetch was called and PDF was created
                mock_imap.fetch.assert_called_once_with('1', '(RFC822)')
                assert len(attachments) == 1
                mock_pdf.assert_called_once()

    @patch('smtplib.SMTP')
    def test_send_email(self, mock_smtp_class):
        """Test the send_email method."""
        # Set up the mock
        mock_smtp = MagicMock()
        mock_smtp_class.return_value = mock_smtp
        
        # Create a Mailclient instance
        client = Mailclient.__new__(Mailclient)
        client._smtp_connection = mock_smtp
        client._username = 'sender@example.com'
        
        # Call the send_email method
        result = client.send_email(
            to_email='recipient@example.com',
            subject='Test Subject',
            body='Test body',
            html_body='<p>Test HTML body</p>'
        )
        
        # Verify that send_message was called and the result is True
        mock_smtp.send_message.assert_called_once()
        assert result is True

    @patch('smtplib.SMTP')
    def test_send_email_with_attachments(self, mock_smtp_class):
        """Test the send_email method with attachments."""
        # Set up the mock
        mock_smtp = MagicMock()
        mock_smtp_class.return_value = mock_smtp
        
        # Create a Mailclient instance
        client = Mailclient.__new__(Mailclient)
        client._smtp_connection = mock_smtp
        client._username = 'sender@example.com'
        
        # Call the send_email method with attachments
        attachments = {'test.pdf': b'PDF_CONTENT'}
        result = client.send_email(
            to_email='recipient@example.com',
            subject='Test Subject',
            body='Test body',
            attachments=attachments
        )
        
        # Verify that send_message was called and the result is True
        mock_smtp.send_message.assert_called_once()
        assert result is True

    @patch('smtplib.SMTP')
    def test_send_email_with_cc_bcc(self, mock_smtp_class):
        """Test the send_email method with CC and BCC recipients."""
        # Set up the mock
        mock_smtp = MagicMock()
        mock_smtp_class.return_value = mock_smtp
        
        # Create a Mailclient instance
        client = Mailclient.__new__(Mailclient)
        client._smtp_connection = mock_smtp
        client._username = 'sender@example.com'
        
        # Call the send_email method with CC and BCC
        result = client.send_email(
            to_email='recipient@example.com',
            subject='Test Subject',
            body='Test body',
            cc='cc@example.com',
            bcc='bcc@example.com'
        )
        
        # Verify that send_message was called with all recipients and the result is True
        mock_smtp.send_message.assert_called_once()
        # Check that all recipients were included
        call_args = mock_smtp.send_message.call_args
        assert 'recipient@example.com' in call_args[1]['to_addrs']
        assert 'cc@example.com' in call_args[1]['to_addrs']
        assert 'bcc@example.com' in call_args[1]['to_addrs']
        assert result is True

    @patch('smtplib.SMTP')
    def test_send_email_error_handling(self, mock_smtp_class):
        """Test error handling in the send_email method."""
        # Set up the mock to raise an exception
        mock_smtp = MagicMock()
        mock_smtp.send_message.side_effect = Exception("SMTP error")
        mock_smtp_class.return_value = mock_smtp
        
        # Create a Mailclient instance
        client = Mailclient.__new__(Mailclient)
        client._smtp_connection = mock_smtp
        client._username = 'sender@example.com'
        
        # Call the send_email method
        result = client.send_email(
            to_email='recipient@example.com',
            subject='Test Subject',
            body='Test body'
        )
        
        # Verify that the result is False due to the exception
        assert result is False

    @patch('cls.mailclient.IMAP4_SSL')
    def test_mark_email_as_read(self, mock_imap_class):
        """Test the mark_email_as_read method."""
        # Set up the mock
        mock_imap = MagicMock()
        mock_imap_class.return_value = mock_imap
        
        # Create a Mailclient instance
        client = Mailclient.__new__(Mailclient)
        client._connection = mock_imap
        
        # Call the mark_email_as_read method
        client.mark_email_as_read('1')
        
        # Verify that store was called with the correct flags
        mock_imap.store.assert_called_once_with('1', '+FLAGS', '\\Seen')

    @patch('cls.mailclient.IMAP4_SSL')
    def test_mark_email_as_answered(self, mock_imap_class):
        """Test the mark_email_as_answered method."""
        # Set up the mock
        mock_imap = MagicMock()
        mock_imap_class.return_value = mock_imap
        
        # Create a Mailclient instance
        client = Mailclient.__new__(Mailclient)
        client._connection = mock_imap
        
        # Call the mark_email_as_answered method
        client.mark_email_as_answered('1')
        
        # Verify that store was called with the correct flags
        mock_imap.store.assert_called_once_with('1', '+FLAGS', '\\Answered')
"""
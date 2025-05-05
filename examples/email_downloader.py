"""
email_downloader.py - Tool to download emails for offline development

This script connects to an email server using credentials from a .env file
and downloads emails to be used for offline development of the Document Fetcher.
"""
import os
import sys
import argparse
import imaplib
import email
import pickle
from pathlib import Path
from dotenv import load_dotenv, find_dotenv


def parse_arguments():
    """
    Parse command line arguments.
    """
    parser = argparse.ArgumentParser(
        description="Download emails from a mail server for offline development."
    )
    parser.add_argument(
        "-n", "--num-emails",
        type=int,
        default=10,
        help="Number of most recent emails to download (default: 10)"
    )
    parser.add_argument(
        "-o", "--output-dir",
        type=str,
        help="Directory to save emails (default: ./.filesystem/test_emails)"
    )
    parser.add_argument(
        "-s", "--search",
        type=str,
        default="ALL",
        help="IMAP search criteria (default: ALL)"
    )
    parser.add_argument(
        "-f", "--force",
        action="store_true",
        help="Force download even if emails already exist"
    )
    parser.add_argument(
        "--list-mailboxes",
        action="store_true",
        help="List available mailboxes and exit"
    )
    return parser.parse_args()


def main():
    """
    Main function to download emails.
    """
    args = parse_arguments()

    # Load environment variables
    load_dotenv(find_dotenv())

    # Verify required environment variables
    required_vars = ["IMAP_HOST", "IMAP_PORT", "IMAP_USER", "IMAP_PASSWORD"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
        print("Please check your .env file and ensure all email configuration is set.")
        return 1

    # Set up storage directory
    storage_path = args.output_dir or os.path.join(
        os.getenv("FILESYSTEM_PATH", "../.filesystem/"),
        "test_emails"
    )
    storage_dir = Path(storage_path)
    storage_dir.mkdir(parents=True, exist_ok=True)
    print(f"Email storage directory: {storage_path}")

    # Check if directory already has emails
    existing_emails = list(storage_dir.glob("test_mail_*.pickle"))
    if existing_emails and not args.force:
        print(f"Found {len(existing_emails)} existing emails in the directory.")
        confirm = input("Download additional emails? [y/N]: ").lower()
        if confirm != 'y':
            print("Operation cancelled by user.")
            return 0

    # Connect to the email server
    print(f"Connecting to {os.getenv('IMAP_HOST')}:{os.getenv('IMAP_PORT')}...")
    try:
        imap = imaplib.IMAP4_SSL(os.getenv("IMAP_HOST"), int(os.getenv("IMAP_PORT")))
        print("Connection established")
    except Exception as e:
        print(f"Connection error: {e}")
        return 1

    # Login to the email server
    try:
        status, data = imap.login(os.getenv("IMAP_USER"), os.getenv("IMAP_PASSWORD"))
        print(f"Login status: {status}")
        if status != 'OK':
            print(f"Login failed: {data}")
            return 1
    except Exception as e:
        print(f"Login error: {e}")
        return 1

    # List mailboxes if requested
    if args.list_mailboxes:
        print("Available mailboxes:")
        status, mailboxes = imap.list()
        if status == 'OK':
            for mailbox in mailboxes:
                mailbox_str = mailbox.decode() if isinstance(mailbox, bytes) else str(mailbox)
                print(f"  {mailbox_str}")
            return 0
        else:
            print(f"Failed to list mailboxes: {status}")
            return 1

    # Select mailbox
    mailbox = os.getenv("INBOX", "INBOX")
    print(f"Selecting mailbox: {mailbox}")
    status, data = imap.select(mailbox)
    if status != 'OK':
        print(f"Failed to select mailbox: {data}")
        print("Use --list-mailboxes to see available mailboxes")
        imap.logout()
        return 1

    # Search for emails
    print(f"Searching for emails with criteria: {args.search}")
    status, data = imap.search(None, args.search)
    if status != 'OK':
        print(f"Search failed: {data}")
        imap.logout()
        return 1

    # Get number of emails to download
    email_ids = data[0].split()
    num_emails = len(email_ids)
    print(f"Found {num_emails} emails")

    if num_emails == 0:
        print("No emails found matching the search criteria.")
        imap.logout()
        return 0

    # Limit the number of emails to download
    max_emails = min(args.num_emails, num_emails) if args.num_emails > 0 else num_emails
    if max_emails < num_emails:
        print(f"Limiting to {max_emails} most recent emails")
        # Take the most recent emails (last ones in the list)
        email_ids = email_ids[-max_emails:]

    # Process each email ID
    print(f"Downloading {len(email_ids)} emails...")
    success_count = 0

    for i, email_id in enumerate(email_ids):
        email_id_str = email_id.decode('utf-8') if isinstance(email_id, bytes) else str(email_id)

        print(f"Fetching email {i + 1}/{len(email_ids)} (ID: {email_id_str})...", end="")
        sys.stdout.flush()

        # Fetch the email
        status, msg_data = imap.fetch(email_id, '(RFC822)')

        if status != 'OK':
            print(f" Failed to fetch email ID: {email_id_str}")
            continue

        # Save the raw fetch response using pickle (to preserve exact structure)
        filename = f"test_mail_{email_id_str}.pickle"
        filepath = os.path.join(storage_path, filename)

        with open(filepath, 'wb') as f:
            pickle.dump(msg_data, f)

        # Parse the email to display subject
        try:
            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)
            subject = msg.get("Subject", "No Subject")
            print(f" Done\n  Subject: {subject}")
            success_count += 1
        except Exception as e:
            print(f" Error parsing email: {e}")

    print(f"\nCompleted! {success_count}/{len(email_ids)} emails saved to {storage_path}")

    # Logout
    imap.logout()
    print("Logged out from mail server")

    # Verify the saved emails
    saved_files = list(Path(storage_path).glob("test_mail_*.pickle"))
    print(f"\nVerification: {len(saved_files)} email files found in storage directory")

    # Instructions for using the saved emails
    print("\nTo use these emails for offline development:")
    print("1. Set DEV_MODE=true in your .env file")
    print(f"2. Set EXAMPLE_MAIL_PATH={storage_path}")
    print("3. Restart your application")

    return 0


if __name__ == "__main__":
    sys.exit(main())

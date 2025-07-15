"""
email_downloader.py - Tool to download emails for offline development and testing

This script connects to an email server using credentials from environment variables
or .env file and downloads emails for offline development and CI/CD testing.
"""
import os
import sys
import json
import argparse
import imaplib
import email
import pickle
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv, find_dotenv


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Download emails from a mail server for offline development and testing."
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
        default="example_mails",
        help="Directory to save emails (default: example_mails)"
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
    parser.add_argument(
        "--limit",
        type=int,
        help="Alias for --num-emails (for CI compatibility)"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Alias for --output-dir (for CI compatibility)"
    )
    parser.add_argument(
        "--format",
        choices=["pickle", "eml", "both"],
        default="pickle",
        help="Output format: pickle (for mock_imaplib), eml (standard email), or both"
    )
    parser.add_argument(
        "--manifest",
        action="store_true",
        help="Create a manifest.json file with email metadata"
    )
    parser.add_argument(
        "--ci",
        action="store_true",
        help="CI mode: suppress interactive prompts, use environment variables"
    )
    return parser.parse_args()


def save_email_pickle(filepath, msg_data):
    """Save email in pickle format (for mock_imaplib)."""
    with open(filepath, 'wb') as f:
        pickle.dump(msg_data, f)


def save_email_eml(filepath, raw_email):
    """Save email in standard .eml format."""
    with open(filepath, 'wb') as f:
        f.write(raw_email)


def get_credentials(ci_mode=False):
    """Get email credentials from environment or .env file."""
    # In CI mode, only use environment variables
    if not ci_mode:
        load_dotenv(find_dotenv())

    # Check required variables
    required_vars = ["IMAP_HOST", "IMAP_USER", "IMAP_PASSWORD"]
    credentials = {
        "host": os.environ.get("IMAP_HOST"),
        "port": int(os.environ.get("IMAP_PORT", "993")),
        "user": os.environ.get("IMAP_USER"),
        "password": os.environ.get("IMAP_PASSWORD"),
        "mailbox": os.environ.get("INBOX", "INBOX")
    }

    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    if missing_vars:
        if ci_mode:
            # In CI, missing credentials is not an error
            return None
        else:
            print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
            print("Please check your .env file or environment variables.")
            sys.exit(1)

    return credentials


def main():
    """Main function to download emails."""
    args = parse_arguments()

    # Handle CI compatibility aliases
    if args.limit is not None:
        args.num_emails = args.limit
    if args.output is not None:
        args.output_dir = args.output

    # Get credentials
    credentials = get_credentials(ci_mode=args.ci)
    if not credentials:
        print("No IMAP credentials available, exiting.")
        return 0 if args.ci else 1

    # Set up storage directory
    storage_dir = Path(args.output_dir)
    storage_dir.mkdir(parents=True, exist_ok=True)
    print(f"Email storage directory: {storage_dir}")

    # Check existing emails
    existing_pickles = list(storage_dir.glob("test_mail_*.pickle"))
    existing_emls = list(storage_dir.glob("email_*.eml"))
    if (existing_pickles or existing_emls) and not args.force and not args.ci:
        total_existing = len(existing_pickles) + len(existing_emls)
        print(f"Found {total_existing} existing emails in the directory.")
        confirm = input("Download additional emails? [y/N]: ").lower()
        if confirm != 'y':
            print("Operation cancelled by user.")
            return 0

    # Connect to email server
    print(f"Connecting to {credentials['host']}:{credentials['port']}...")
    try:
        imap = imaplib.IMAP4_SSL(credentials['host'], credentials['port'])
        print("Connection established")
    except Exception as e:
        print(f"Connection error: {e}")
        return 1

    # Login
    try:
        status, data = imap.login(credentials['user'], credentials['password'])
        if status != 'OK':
            print(f"Login failed: {data}")
            return 1
        print("Login successful")
    except Exception as e:
        print(f"Login error: {e}")
        return 1

    # List mailboxes if requested
    if args.list_mailboxes:
        print("\nAvailable mailboxes:")
        status, mailboxes = imap.list()
        if status == 'OK':
            for mailbox in mailboxes:
                mailbox_str = mailbox.decode() if isinstance(mailbox, bytes) else str(mailbox)
                print(f"  {mailbox_str}")
        imap.logout()
        return 0

    # Select mailbox
    print(f"Selecting mailbox: {credentials['mailbox']}")
    status, data = imap.select(credentials['mailbox'])
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

    # Get email IDs
    email_ids = data[0].split()
    num_emails = len(email_ids)
    print(f"Found {num_emails} emails")

    if num_emails == 0:
        print("No emails found matching the search criteria.")
        imap.logout()
        return 0

    # Limit number of emails
    max_emails = min(args.num_emails, num_emails) if args.num_emails > 0 else num_emails
    if max_emails < num_emails:
        print(f"Limiting to {max_emails} most recent emails")
        email_ids = email_ids[-max_emails:]

    # Prepare manifest if requested
    manifest = {
        "downloaded_at": datetime.now().isoformat(),
        "search_criteria": args.search,
        "mailbox": credentials['mailbox'],
        "emails": []
    } if args.manifest else None

    # Download emails
    print(f"\nDownloading {len(email_ids)} emails...")
    success_count = 0

    for i, email_id in enumerate(email_ids):
        email_id_str = email_id.decode('utf-8') if isinstance(email_id, bytes) else str(email_id)
        print(f"Fetching email {i + 1}/{len(email_ids)} (ID: {email_id_str})...", end="")
        sys.stdout.flush()

        # Fetch email
        status, msg_data = imap.fetch(email_id, '(RFC822)')
        if status != 'OK':
            print(f" Failed")
            continue

        try:
            # Save in requested format(s)
            if args.format in ["pickle", "both"]:
                pickle_file = storage_dir / f"test_mail_{email_id_str}.pickle"
                save_email_pickle(pickle_file, msg_data)

            # Parse email for additional formats or manifest
            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)
            subject = msg.get("Subject", "No Subject")

            if args.format in ["eml", "both"]:
                # Create more descriptive filename for .eml
                safe_subject = "".join(c for c in subject if c.isalnum() or c in (' ', '-', '_'))[:50]
                eml_file = storage_dir / f"email_{i+1}_{safe_subject}.eml"
                save_email_eml(eml_file, raw_email)

            # Add to manifest
            if manifest:
                manifest["emails"].append({
                    "id": email_id_str,
                    "subject": subject,
                    "from": msg.get("From", ""),
                    "date": msg.get("Date", ""),
                    "has_attachments": any(
                        part.get_content_disposition() == 'attachment'
                        for part in msg.walk()
                    ),
                    "pickle_file": f"test_mail_{email_id_str}.pickle" if args.format in ["pickle", "both"] else None,
                    "eml_file": f"email_{i+1}_{safe_subject}.eml" if args.format in ["eml", "both"] else None
                })

            print(f" Done\n  Subject: {subject}")
            success_count += 1

        except Exception as e:
            print(f" Error: {e}")

    # Save manifest
    if manifest:
        manifest_path = storage_dir / "manifest.json"
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        print(f"\nManifest saved to: {manifest_path}")

    print(f"\nCompleted! {success_count}/{len(email_ids)} emails downloaded to {storage_dir}")

    # Logout
    imap.logout()
    print("Logged out from mail server")

    # Verification
    saved_files = list(storage_dir.glob("test_mail_*.pickle")) + list(storage_dir.glob("email_*.eml"))
    print(f"\nVerification: {len(saved_files)} email files in storage directory")

    # Usage instructions
    if not args.ci:
        print("\nTo use these emails for offline development:")
        print("1. Set DEV_MODE=true in your .env file")
        print(f"2. Set MOCK_EMAIL_DIR={storage_dir}")
        print("3. Restart your application")

    return 0


if __name__ == "__main__":
    sys.exit(main())

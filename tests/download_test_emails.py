#!/usr/bin/env python3
"""
Wrapper script for tests that calls the main email_downloader.py
with appropriate settings for CI/CD testing.
"""
import sys
import os
import subprocess

# Add parent directory to path to import the main downloader
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Just call the main email_downloader with CI-appropriate defaults
args = [
    sys.executable,
    "email_downloader.py",
    "--output-dir", "example_mails",
    "--num-emails", "5",
    "--ci",  # CI mode (no prompts)
    "--manifest",  # Create manifest for tracking
    "--format", "pickle"  # Use pickle format for mock_imaplib
]

# Pass through any additional arguments
args.extend(sys.argv[1:])

# Execute
sys.exit(subprocess.call(args))

# Document Fetcher

This is a tool to fetch and process documents from emails, particularly balance sheets. It utilizes OCR technology to extract text from PDFs so they can be automatically compared against database records for financial auditing purposes.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
    - [Prerequisites](#prerequisites)
    - [Virtual Environment Setup](#virtual-environment-setup)
    - [Environment Configuration](#environment-configuration)
    - [App Initialization](#app-initialization)
    - [Capture Emails](#capture-emails)
    - [Database Setup](#database-setup)
- [Usage](#usage)
    - [Starting the Application](#starting-the-application)
    - [Using the Web Interface](#using-the-web-interface)
    - [Processing Workflow](#processing-workflow)
- [Configuration](#configuration)
- [Docker Deployment](#docker-deployment)
- [Troubleshooting](#troubleshooting)
- [Development](#development)
    - [Project Structure](#project-structure)
    - [Module Overview](#module-overview)
- [License](#license)
- [Contact](#contact)

## Overview

Document Fetcher automates the yearly auditing process that requires auditors to verify balance sheets. The application connects to email inboxes, retrieves PDF documents, uses OCR to extract text and tabular data, and automatically compares the extracted values against database records.

## Features

- Email inbox integration
- PDF document extraction and parsing
- OCR processing with EasyOCR and Tesseract
- Automated data verification against database records
- Web-based user interface with Streamlit
- Workflow management for document processing
- Certificate generation for verified documents
- **Access Control System**: Role-based (admin, auditor, inspector) and resource-based permissions
- **Excel Import**: Bulk initialization of audit seasons from Excel files
- **Configuration Management**: Dynamic application settings via config files
- **User-Client Access Management**: Granular control over which users can access which clients
- **Email Response Templates**: Automated email response generation
- **Session Management**: Secure session handling with expiration
- **Login Security**: Login attempt tracking and IP-based monitoring
- **Audit Logging**: Comprehensive logging of all user actions

## Installation

### Prerequisites

Before installation, ensure you have the following installed:
- Python 3.11 or higher
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) (optional, for OCR text extraction)
- System libraries for OpenCV and PDF processing

**Note**: The application uses PyMuPDF instead of Poppler for PDF processing.

Additional Python libraries required:
- **PyMuPDF**: PDF processing and manipulation
- **python-docx** and **docx2pdf**: Certificate generation
- **reportlab**: Advanced PDF manipulation
- **openpyxl**: Excel file support
- **PyTorch** (optional): GPU-accelerated OCR

#### Installing Prerequisites on Different Operating Systems:

**Windows:**
```bash
# Install Tesseract OCR via chocolatey (https://chocolatey.org/)
choco install tesseract

# Install system libraries for OpenCV
# These are typically included with Python packages on Windows
```

**macOS:**
```bash
# Install Tesseract OCR via Homebrew
brew install tesseract

# Install system libraries for OpenCV
brew install opencv
```

**Linux (Ubuntu/Debian):**
```bash
# Install Tesseract OCR
sudo apt-get update
sudo apt-get install tesseract-ocr
sudo apt-get install tesseract-ocr-deu  # German language support

# Install system libraries for OpenCV and PDF processing
sudo apt-get install libgl1-mesa-glx libglib2.0-0 libsm6 libxrender1 libxext6
```

### Virtual Environment Setup

It's recommended to install the application in a virtual environment:

1. Clone the repository:
```bash
git clone https://github.com/Knaeckebrothero/RPA-Automation.git
cd rpa-document-fetcher
```

2. Create a virtual environment:
```bash
# Using venv
python -m venv venv

# Using conda (alternative)
conda create -n document-fetcher python=3.11
```

3. Activate the virtual environment:
```bash
# On Windows
venv\Scripts\activate

# On macOS/Linux
source venv/bin/activate

# Using conda
conda activate document-fetcher
```

4. Install required packages:
```bash
pip install -r requirements.txt

# Optional: Install PyTorch with CUDA support for GPU-accelerated OCR
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### Environment Configuration

Create a `.env` file in the root directory with the following variables:
```
# Logging configuration
LOG_LEVEL_CONSOLE=20
LOG_LEVEL_FILE=10
LOG_PATH=./.filesystem/logs/

# Filesystem paths
FILESYSTEM_PATH=./.filesystem/
CERTIFICATE_TEMPLATE_PATH=./.filesystem/certificate_template.docx
CERTIFICATE_TOS_PATH=./.filesystem/terms_conditions.pdf

# Development mode flag
DEV_MODE=true
  
# OCR configuration
OCR_USE_GPU=false

# Email server configuration
IMAP_HOST=your.mail.server.com
IMAP_PORT=993
IMAP_USER=your_username
IMAP_PASSWORD=your_password
INBOX=your_inbox_name

# For development testing with mock emails
EXAMPLE_MAIL_PATH=./example_mails/
```
**Tip:** You can use the [environment example](./.env.example) for this.

### App Initialization

The easiest way to set up the application is to use the provided initialization script:
```bash
python app_init.py
```

This script performs the following tasks:
- Creates the necessary directory structure
- Sets up a default environment file
- Initializes the database with example data
- Creates default configuration files
- Sets up certificate templates
- Verifies that all components are ready

#### Initialization Options

The script supports several command-line options:

```bash
# Initialize with default settings
python app_init.py
```
```bash
# Force reset everything (warning: deletes existing data)
python app_init.py --force-reset
```
```bash
# Download test emails during initialization
python app_init.py --download-emails --num-emails 20
```
```bash
# Only set up the filesystem structure without initializing components
python app_init.py --setup-only
```
```bash
# Skip database initialization
python app_init.py --skip-db-init
```
```bash
# Show all available options
python app_init.py --help
```

After successful initialization, you'll receive login credentials and instructions to start the application.

### Capture Emails

This project requires access to an email inbox to fetch documents. For development purposes, you can capture sample emails to work offline using the provided email downloader script.

#### Using the Email Downloader

1. Ensure your `.env` file is properly configured with your email credentials:
   ```
   IMAP_HOST=your.mail.server.com
   IMAP_PORT=993
   IMAP_USER=your_username
   IMAP_PASSWORD=your_password
   INBOX=your_inbox_name
   FILESYSTEM_PATH=./.filesystem/
   ```

2. Run the email downloader script:
   ```bash
   # Ensure your virtual environment is activated
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   
   # Run the email downloader script
   python examples/email_downloader.py
   ```

3. By default, the script will:
    - Connect to your configured email server
    - Download the 10 most recent emails
    - Save them to `./example_mails/`

4. The script supports several command-line options:
   ```bash
   # Download 20 emails instead of the default 10
   python examples/email_downloader.py --num-emails 20
   
   # Save emails to a custom directory
   python examples/email_downloader.py --output-dir ./example_mails
   
   # List available mailboxes and exit
   python examples/email_downloader.py --list-mailboxes
   
   # Use a specific search query
   python examples/email_downloader.py --search "SUBJECT pdf"
   
   # Show help information
   python examples/email_downloader.py --help
   ```

5. For offline development, after downloading the emails, configure these environment variables:
   ```
   DEV_MODE=true
   EXAMPLE_MAIL_PATH=./example_mails/
   ```

The downloaded emails will be used automatically when the application runs in development mode, allowing you to test document processing without connecting to the mail server.

#### Troubleshooting Email Capture

- If you encounter connection issues, verify your email server credentials
- For Gmail accounts, you may need to create an [App Password](https://support.google.com/accounts/answer/185833)
- Ensure your email provider allows IMAP access
- Check that the output directory exists and is writable

### Database Setup

This application uses SQLite for data storage. The directory structure for the database is:

```
./
├── examples/
│   ├── db_init.py                  # Database initialization script
│   ├── email_downloader.py         # Email download utility
│   ├── insert_example_data.sql     # Example data for testing
│   └── email_templates/            # Email response templates
│       └── response_template.html
├── src/                            # Source code directory
│   └── schema.sql                  # Database schema definition
└── .filesystem/                    # Data storage directory
    └── database.db                 # SQLite database file (created by initialization script)
```

Run the initialization script to create the database and populate it with example data:
```bash
python examples/db_init.py
```

The script will:
1. Create the database file if it doesn't exist
2. Create the required tables (including new access control tables)
3. Insert example data if the database is empty
4. Set up indexes and triggers for performance

The script supports several command-line arguments to customize the database initialization process:
```bash
python examples/db_init.py --help
```

To reset the database and remove all data:
```bash
python examples/db_init.py --force-reset
```

#### Database Schema

The database includes the following main tables:
- **client**: Client information and financial data
- **audit_case**: Active audit cases and their stages
- **document**: Document tracking and processing status
- **user**: User accounts and authentication
- **session_key**: Active user sessions
- **user_client_access**: User-to-client access permissions
- **login_attempts**: Security tracking for login attempts

## Usage

### Starting the Application

After completing the installation and configuration steps, start the application using Streamlit:

```bash
# Make sure you're in the project root directory
cd rpa-document-fetcher

# Activate your virtual environment if not already activated
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Start the application
streamlit run src/main.py
```

The application will be available at http://localhost:8501 in your web browser.

### Using the Web Interface

1. **Login**: Use the demo accounts provided on the login screen:
    - Admin: `admin@example.com` / `admin123`
    - Auditor: `auditor@example.com` / `auditor123`
    - Inspector: `inspector@example.com` / `inspector123`

2. **Navigation**: Use the sidebar to navigate between different sections:
    - Home/Document Fetcher: Main interface for processing emails
    - Active Cases: View and manage audit cases
    - Settings: Configure application settings
    - About: View application information and logs

3. **Home Page**:
    - View incoming emails with attachments
    - Select individual documents or process all documents
    - Monitor document submission ratio in the pie chart
    - Process selected emails to extract balance sheet data

4. **Active Cases Page**:
    - View all active audit cases in a table format
    - Select individual cases to view details
    - Monitor the progress of each case through the audit workflow
    - Add comments to cases for internal documentation
    - Download processed documents and certificates
    - Access is filtered based on user permissions (non-admin users only see their assigned cases)

5. **Settings Page** (Admin only):
    - **Application Settings**: Configure certificate templates and archive settings
    - **Audit Settings**: Initialize annual audit processes from Excel files
    - **User Management**: Create and manage user accounts
    - **Access Control**: Manage user-client permissions

6. **About Page**:
    - View application information
    - Access application logs for troubleshooting
    - Report issues or bugs

### User Roles and Permissions

The application implements a comprehensive role-based access control system:

#### Admin Role
- Full access to all features and clients
- Can manage users and permissions
- Initialize audit seasons from Excel
- Archive completed cases
- Configure application settings

#### Inspector Role
- View and edit assigned cases
- Generate certificates
- View application logs
- Limited to assigned clients only

#### Auditor Role
- View and edit assigned cases
- Limited to assigned clients only
- Basic case management

### Processing Workflow

The document processing workflow consists of these main stages:

1. **Document Reception (Stage 1)**:
    - The application connects to the configured email inbox and fetches emails with PDF attachments
    - Documents are identified by their BaFin ID and linked to the corresponding client
    - If no matching client is found, the document remains in Stage 1

2. **Data Verification (Stage 2)**:
    - OCR extracts text and tabular data from the PDF documents
    - The system identifies key financial figures and position numbers
    - Extracted values are compared against the database records
    - A comparison table is generated showing matches and mismatches
    - If all required values match, the case advances to Stage 3

3. **Certificate Generation (Stage 3)**:
    - Once verified, a certificate is generated confirming the data matches
    - The certificate includes client information, validation date, and audit reference
    - The certificate is combined with the first page of the submitted document
    - The complete certificate package can be downloaded from the Active Cases page

4. **Process Completion (Stage 4)**:
    - All documents and the certificate are available for download
    - The process is marked as complete
    - The case can be archived from the Settings page

5. **Archiving (Stage 5)**:
    - Completed cases are archived for record-keeping
    - Archived cases no longer appear in the Active Cases view

#### Excel Import for Audit Season

Administrators can initialize audit seasons by uploading Excel files:
- Upload Excel files containing client data and auditor assignments
- The system validates Excel structure and required columns
- Creates or updates client records based on BaFin IDs
- Automatically creates user accounts for auditors/inspectors if needed
- Grants appropriate access permissions based on assignments
- Generates detailed import reports with success/error counts

To process documents:
1. Navigate to the Home/Document Fetcher page
2. View the list of available emails
3. Select emails to process or click "Process all documents"
4. Track the progress in the Active Cases section
5. Review extracted data and comparison results
6. Generate certificates for verified documents
7. Complete and archive cases

## Configuration

The application uses multiple configuration methods:

1. **Environment Variables** (`.env` file)
2. **Configuration File** (`src/config.cfg`)
3. **Dynamic Settings** via the web interface

### Configuration File (config.cfg)

The application automatically creates a configuration file with default settings:

```ini
[APP_SETTINGS]
certificate_template_path = ./.filesystem/certificate_template.docx
terms_conditions_path = ./.filesystem/terms_conditions.pdf
archive_file_prefix = audit_archive
```

These settings can be modified through the Settings page in the web interface.

## Docker Deployment

The application includes a Dockerfile for containerized deployment:

```bash
# Build the Docker image
docker build -f deployment/Dockerfile -t rpa-document-fetcher .

# Run the container
docker run -p 8501:8501 \
  -e IMAP_HOST=your.mail.server.com \
  -e IMAP_PORT=993 \
  -e IMAP_USER=your_username \
  -e IMAP_PASSWORD=your_password \
  -e INBOX=your_inbox_name \
  -e DEV_MODE=false \
  rpa-document-fetcher
```

The Docker image includes:
- Python 3.11 base
- Tesseract OCR with German language support
- All required system libraries for OpenCV
- PyTorch with CUDA support for GPU acceleration
- Automatic database initialization on startup

For production deployment with persistent data:

```bash
# Create volumes for persistent data
docker volume create rpa-filesystem
docker volume create rpa-logs

# Run with volumes
docker run -p 8501:8501 \
  -v rpa-filesystem:/app/.filesystem \
  -v rpa-logs:/app/.filesystem/logs \
  -e IMAP_HOST=your.mail.server.com \
  -e IMAP_PORT=993 \
  -e IMAP_USER=your_username \
  -e IMAP_PASSWORD=your_password \
  -e INBOX=your_inbox_name \
  -e DEV_MODE=false \
  rpa-document-fetcher
```

## Troubleshooting

### Common Issues

**OCR Not Working Correctly**:
- Ensure Tesseract is properly installed and in your system PATH
- Verify the German language pack for Tesseract is installed (tesseract-ocr-deu)
- Check that the PDF documents are not scanned at too low a resolution
- For GPU acceleration, ensure CUDA is properly installed and set `OCR_USE_GPU=true`

**Email Connection Issues**:
- Verify your email server credentials in the .env file
- Ensure your email server allows IMAP connections
- If using Google, you may need an app password instead of your regular password
- Check firewall settings for port 993 (IMAP SSL)

**Database Errors**:
- Run `python examples/db_init.py --force-reset` to reset the database
- Make sure the .filesystem directory exists and is writable
- Check that the SQLite database is not locked by another process
- Verify file permissions on the database file

**Web Interface Not Loading**:
- Ensure Streamlit is properly installed: `pip install streamlit`
- Check if another process is using port 8501
- Try running with explicit host and port: `streamlit run src/main.py --server.port=8501 --server.address=0.0.0.0`

**Access Control Issues**:
- Verify user permissions in the database
- Check the user_client_access table for proper assignments
- Ensure the user role is correctly set

### Logging

The application generates logs to help troubleshoot issues:
- Check the log file at `./.filesystem/logs/application.log`
- Increase log verbosity by setting `LOG_LEVEL_CONSOLE=10` and `LOG_LEVEL_FILE=10` in your .env file
- Log levels: DEBUG=10, INFO=20, WARNING=30, ERROR=40, CRITICAL=50
- Login attempts are tracked in the database for security monitoring

## Development

### Project Structure

```
RPA-Document-Fetcher/
    |-- .devcontainer/
    |   └── devcontainer.json
    |-- deployment/
    |   └── Dockerfile
    |-- examples/
    |   |-- email_templates/
    |   |   └── response_template.html
    |   |-- db_init.py
    |   |-- email_downloader.py
    |   └── insert_example_data.sql
    |-- src/
    |   |-- cls/
    |   |   |-- __init__.py
    |   |   |-- accesscontrol.py    # Access control management
    |   |   |-- config.py           # Configuration handler
    |   |   |-- database.py         # Database interface
    |   |   |-- document.py         # Document processing
    |   |   |-- mailclient.py       # Email client interface
    |   |   └── singleton.py        # Singleton pattern implementation
    |   |-- processing/
    |   |   |-- __init__.py
    |   |   |-- detect.py           # Table and text detection
    |   |   |-- files.py            # File operations
    |   |   └── ocr.py              # OCR text extraction
    |   |-- ui/
    |   |   |-- __init__.py
    |   |   |-- expander_stages.py  # UI for different stages
    |   |   |-- navbar.py           # Navigation sidebar
    |   |   |-- pages.py            # Main page definitions
    |   |   └── visuals.py          # Visualizations and UI elements
    |   |-- workflow/
    |   |   |-- __init__.py
    |   |   |-- audit.py            # Audit workflow logic
    |   |   |-- excel_import.py     # Excel import for audit season
    |   |   └── security.py         # Authentication and security
    |   |-- config.cfg              # Configuration file
    |   |-- custom_logger.py        # Logging setup
    |   |-- main.py                 # Application entry point
    |   |-- mock_imaplib.py         # Mock email client for testing
    |   |-- regex_patterns.json     # Patterns for text extraction
    |   |-- schema.sql              # Database schema
    |   └── table_detection.py      # Table detection test script
    |-- .env.example                # Example environment variables
    |-- app_init.py                 # Application initialization script
    |-- README.md                   # This file
    └── requirements.txt            # Python dependencies
```

### Module Overview

- **cls/**: Core classes for database, document, and email handling
    - **accesscontrol.py**: Manages both role-based and resource-based permissions
    - **config.py**: Configuration file management and settings persistence
    - **database.py**: SQLite database connection and operations
    - **document.py**: Document representation and processing
    - **mailclient.py**: Email client for fetching attachments
    - **singleton.py**: Utility for creating singleton instances

- **processing/**: Document processing utilities
    - **detect.py**: Algorithms for detecting tables and data
    - **files.py**: File system operations for documents
    - **ocr.py**: OCR integration with EasyOCR/Tesseract

- **ui/**: Streamlit user interface components
    - **expander_stages.py**: UI elements for workflow stages
    - **navbar.py**: Navigation sidebar
    - **pages.py**: Main page definitions and layouts
    - **visuals.py**: Charts, badges, and visual elements

- **workflow/**: Business logic
    - **audit.py**: Core audit process workflow
    - **excel_import.py**: Handles bulk import of audit data from Excel files
    - **security.py**: Authentication, session management, and access control

## License

This project is licensed under the terms of the Creative Commons Attribution 4.0 International License (CC BY 4.0) and the All Rights Reserved License. See the [LICENSE](LICENSE.txt) file for details.

## Contact
[Github](https://github.com/Knaeckebrothero) <br>
[Mail](mailto:OverlyGenericAddress@pm.me) <br>

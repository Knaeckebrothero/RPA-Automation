# Document Fetcher

This is a simple tool to fetch documents from emails and store them in a local directory.
It utilizes the ocr tool tessaract to extract text from pdfs so that they can be processed.

## Table of Contents

- [Installation](#installation)
- [Usage](#usage)
- [License](#license)
- [Contact](#contact)
- [Acknowledgements](#acknowledgements)

## Installation
### Database Setup
This document explains how to set up and maintain the database for the FinDAG document processing application.

#### Directory Structure
```
./
├── example/
│   ├── db_init.py                  # Database initialization script
│   └── insert_example_data.sql     # Example data for testing
├── src                             # Source code directory
│   └── cfg                         # Configuration directory
│       └── schema.sql              # Database schema definition
└── .filesystem/                    # Data storage directory
    └── database.db                 # SQLite database file (created by initialization script)
```

#### Setup Instructions
Run the initialization script to create the database and populate it with example data.
```bash
python .\examples\db_init.py
```
The script will:
1. Create the database file if it doesn't exist
2. Create the required tables
3. Insert example data if the database is empty

The script supports several command-line arguments to customize the database initialization process.
```bash
python db_init.py --help
```

Use the following command to reset the database and remove all data.
```bash
python db_init.py --force-reset
``` 

## Usage

## License

This project is licensed under the terms of the Creative Commons Attribution 4.0 International License (CC BY 4.0) and the All Rights Reserved License. See the [LICENSE](LICENSE.txt) file for details.

## Contact
[Github](https://github.com/Knaeckebrothero) <br>
[Mail](mailto:OverlyGenericAddress@pm.me) <br>

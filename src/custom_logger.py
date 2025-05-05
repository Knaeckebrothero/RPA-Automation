"""
This is a custom logger configuration snippet that can be used to configure a custom logger for your application.
https://docs.python.org/3/library/logging.html?highlight=logger#module-logging
"""
import os
import datetime
import logging
import inspect
import streamlit as st
from functools import wraps


def add_audit_log_parameter(func) -> callable:
    """
    Decorator to add an audit_log parameter to logging methods.
    This decorator modifies the logging methods of the Logger class to accept an additional audit_log parameter.

    :param func: The function to decorate.
    :return: The decorated function.
    """
    @wraps(func)
    def wrapper(self, msg, *args, **kwargs) -> callable:
        """
        Wrapper function to add audit_log parameter to logging methods.
        This function checks if the audit_log parameter is set to True and if a case_id is provided.

        :param self: The instance of the logger class.
        :param msg: The message to log.
        :param args: Additional arguments to pass to the logging method.
        :param kwargs: Additional keyword arguments to pass to the logging method.
        :return: The result of the logging method.
        """
        audit_log = kwargs.pop('audit_log', False)
        case_id = kwargs.pop('case_id', None)

        # Call the original logging function
        result = func(self, msg, *args, **kwargs)

        # If audit_log is True and case_id is provided, log to the audit case log
        if audit_log and case_id is not None:
            # Get audit case logger and log the message
            audit_logger = get_audit_case_logger(case_id)

            # Use the same level as the original call
            level_name = func.__name__.upper()
            level = getattr(logging, level_name)

            # Log the message
            audit_logger.log(level, msg, *args)
        elif audit_log and case_id is None:
            # Try to determine case_id from the calling context or warn about missing case_id
            frame = inspect.currentframe().f_back

            while frame:
                # Check if case_id is in the current frame's local variables
                if 'case_id' in frame.f_locals:
                    case_id = frame.f_locals['case_id']
                    audit_logger = get_audit_case_logger(case_id)
                    level_name = func.__name__.upper()
                    level = getattr(logging, level_name)
                    audit_logger.log(level, msg, *args)
                    break

                # Move to the next frame
                frame = frame.f_back
            else:
                # If case_id couldn't be determined, log a warning
                logging.getLogger().warning(
                    "Audit logging requested but case_id not provided and couldn't be determined from context")

        return result

    return wrapper


# Patch the Logger class to add the audit_log parameter
class AuditableLogger(logging.Logger):
    @add_audit_log_parameter
    def debug(self, msg, *args, **kwargs):
        return super().debug(msg, *args, **kwargs)

    @add_audit_log_parameter
    def info(self, msg, *args, **kwargs):
        return super().info(msg, *args, **kwargs)

    @add_audit_log_parameter
    def warning(self, msg, *args, **kwargs):
        return super().warning(msg, *args, **kwargs)

    @add_audit_log_parameter
    def error(self, msg, *args, **kwargs):
        return super().error(msg, *args, **kwargs)

    @add_audit_log_parameter
    def critical(self, msg, *args, **kwargs):
        return super().critical(msg, *args, **kwargs)

# Register the custom logger class
logging.setLoggerClass(AuditableLogger)


@st.cache_resource
def configure_global_logger(
        console_level: int = 20,
        file_level: int = 20,
        logging_format: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        logging_directory: str = './logs/',
):
    """
    This function configures a custom logger for printing and saving logs in a logfile.

    :param console_level: The logging level for logging in the console.
    :param file_level: The logging level for logging in the logfile.
    :param logging_format: Format used for logging.
    :param logging_directory: Path for the directory where the log files should be saved to.
    """
    # Configure the root logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(logging_format)

    # Set and create the logging directory if it does not exist
    if not os.path.exists(logging_directory):
        os.makedirs(logging_directory)

    # File handler for writing logs to a file
    # TODO: Implement some kind of log file rotation (perhaps daily)
    file_handler = logging.FileHandler(logging_directory + 'application.log')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(file_level)
    logger.addHandler(file_handler)

    # Console (stream) handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(console_level)
    logger.addHandler(console_handler)


def get_audit_case_logger(case_id):
    """
    Get or create a logger dedicated to a specific audit case.
    If the logger is being created for the first time, it will be initialized
    with historical events.
    
    :param case_id: The ID of the audit case.
    :param db: Optional database connection.
    :return: A Logger instance for the audit case.
    """
    logger_name = f"audit_case_{case_id}"
    logger = logging.getLogger(logger_name)
    
    # Check if this logger already has handlers
    if not logger.handlers:
        # Create case log directory if it doesn't exist
        case_log_path = os.path.join(
            os.getenv('FILESYSTEM_PATH', './.filesystem'),
            "documents",
            str(case_id),
            "audit_log.txt"
        )
        
        # Check if the log file already exists
        log_file_exists = os.path.exists(case_log_path)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(case_log_path), exist_ok=True)
        
        # Set up case-specific file handler
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler = logging.FileHandler(case_log_path)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # Set level to INFO for audit logs
        logger.setLevel(logging.INFO)
        
        # Prevent propagation to avoid duplicate logs in the main log file
        logger.propagate = False
        
        # If this is a new log file, initialize it with historical events - 
        # BUT DO NOT do it from here to avoid circular imports
        if not log_file_exists or os.path.getsize(case_log_path) == 0:
            # Create a simple initial entry
            logger.info(f"Audit log created for case {case_id}")
            
            # Schedule initialization to happen outside the logger creation
            # Using a delayed initialization approach
            global _pending_log_initializations
            if '_pending_log_initializations' not in globals():
                _pending_log_initializations = []
            
            # Add this case to the list of logs that need initialization
            _pending_log_initializations.append(case_id)
    
    return logger


@st.cache_resource
def configure_custom_logger(logger: logging.Logger, log_file: str):
    """
    Configure a custom logger with a specific log file.

    :param logger: The logger to configure.
    :param log_file: The log file path.
    """
    if not logger.hasHandlers():
        logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)


def initialize_audit_log(case_id, db=None):
    """
    Initialize an audit log for a case with historical information.
    This should be called when we first create the audit log file.
    
    :param case_id: The ID of the audit case.
    :param db: Optional database connection.
    """
    if db is None:
        from cls.database import Database
        db = Database.get_instance()

    # Get the audit logger
    audit_logger = get_audit_case_logger(case_id)

    # Get case log file path
    case_log_path = os.path.join(
        os.getenv('FILESYSTEM_PATH', './.filesystem'),
        "documents",
        str(case_id),
        "audit_log.txt"
    )

    # Check if log file already exists and has content
    if os.path.exists(case_log_path) and os.path.getsize(case_log_path) > 0:
        # Log file already exists and has content
        return

    # Get case information
    case_info = db.query("""
                         SELECT ac.client_id,
                                ac.email_id,
                                ac.stage,
                                ac.created_at,
                                c.bafin_id,
                                c.institute
                         FROM audit_case ac
                                  JOIN client c ON ac.client_id = c.id
                         WHERE ac.id = ?
    """, (case_id,))

    if not case_info:
        # No case found
        return

    client_id, email_id, stage, created_date, bafin_id, institute = case_info[0]

    # Log case creation
    created_timestamp = created_date if created_date else datetime.datetime.now()
    audit_logger.info(f"Audit case created for {institute} (BaFin ID: {bafin_id})")

    # If there's an email_id, log document receipt
    if email_id:
        # Get document information
        doc_info = db.query("""
                            SELECT document_filename,
                                   processing_date
                            FROM document
                            WHERE audit_case_id = ?
                              AND email_id = ?
                            ORDER BY processing_date ASC
        """, (case_id, email_id))

        if doc_info:
            # Log each document 
            for doc_filename, proc_date in doc_info:
                # Use processing date if available, otherwise use a timestamp slightly after case creation
                doc_timestamp = proc_date if proc_date else created_timestamp + datetime.timedelta(minutes=5)
                audit_logger.info(f"Email received with document '{doc_filename}'")

    # Log stage transitions based on current stage
    if stage >= 2:
        # If we're at stage 2 or higher, log document verification
        audit_logger.info(f"Document verification process started")

    if stage >= 3:
        # If we're at stage 3 or higher, log successful verification
        # Get document match information if available
        doc_info = db.query("""
                            SELECT document_filename,
                                   document_path
                            FROM document
                            WHERE audit_case_id = ?
                            ORDER BY processing_date DESC
                            LIMIT 1
        """, (case_id,))

        if doc_info:
            try:
                from cls.document import PDF
                document_pdf = PDF.from_json(doc_info[0][1])
                comparison_df = document_pdf.get_value_comparison_table()

                if not comparison_df.empty:
                    matches = comparison_df['Match status'].value_counts().get('✅', 0)
                    total = len(comparison_df)
                    match_percentage = (matches / total) * 100 if total > 0 else 0

                    audit_logger.info(
                        f"Document verification completed with {match_percentage:.1f}% match ({matches}/{total} fields)")
                else:
                    audit_logger.info("Document verification completed successfully")
            except Exception:
                # If we can't load the document, just log that verification was completed
                audit_logger.info("Document verification completed successfully")
        else:
            audit_logger.info("Document verification completed successfully")

    # Check if certificate exists
    cert_path = os.path.join(
        os.getenv('FILESYSTEM_PATH', './.filesystem'),
        "documents",
        str(case_id),
        f"certificate_complete_{case_id}.pdf"
    )

    if os.path.exists(cert_path):
        # Get file creation/modification time
        cert_time = os.path.getmtime(cert_path)
        cert_datetime = datetime.datetime.fromtimestamp(cert_time)

        # Log certificate generation
        audit_logger.info("Certificate generated successfully")

    # If we're at stage 4 or higher, log process completion
    if stage >= 4:
        audit_logger.info("Audit process completed")

    # If we're at stage 5, log archiving
    if stage >= 5:
        audit_logger.info("Case archived")


def process_pending_log_initializations(db=None):
    """
    Process any pending log initializations that were deferred to avoid circular imports.
    This should be called from a safe context (e.g., at the end of an audit workflow).
    
    :param db: Optional database connection.
    """
    global _pending_log_initializations
    
    if '_pending_log_initializations' not in globals():
        return
    
    if not _pending_log_initializations:
        return
    
    # Get a database connection if needed
    if db is None:
        from cls.database import Database
        db = Database.get_instance()
    
    # Process each pending initialization
    for case_id in _pending_log_initializations:
        try:
            initialize_audit_log(case_id, db)
        except Exception as e:
            # Log the error but continue with other initializations
            logging.getLogger().error(f"Error initializing audit log for case {case_id}: {str(e)}")
    
    # Clear the list
    _pending_log_initializations = []

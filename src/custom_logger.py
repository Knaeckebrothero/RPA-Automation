"""
This is a custom logger configuration snippet that can be used to configure a custom logger for your application.

It includes a decorator to add an audit log parameter to the logging methods. 
It also includes a function to configure the global logger and 
a function to get or create a logger dedicated to a specific audit case, and a function to initialize an audit log. 
"""
import os
import datetime
import logging
import streamlit as st
from functools import wraps


def add_audit_log_parameter(func) -> callable:
    """
    Decorator function that modifies a logging function to include additional features
    such as attaching a username, user role, and handling audit logging based on `case_id`.
    The decorator facilitates enhanced logging capabilities while maintaining backward
    compatibility.

    :param func: The original logging function to be wrapped.
    :return: The wrapped logging function with additional functionality.
    :rtype: callable
    """
    @wraps(func)
    def wrapper(self, msg, *args, **kwargs) -> callable:
        """
        Wrapper function to handle audit logging based on case_id.
        This function checks if a case_id is provided to determine if audit logging is needed.
        It also adds the current username to the log message when available.

        :param self: The instance of the logger class.
        :param msg: The message to log.
        :param args: Additional arguments to pass to the logging method.
        :param kwargs: Additional keyword arguments to pass to the logging method.
        :return: The result of the logging method.
        """
        # Remove the redundant audit_log parameter (maintain backward compatibility)
        audit_log = kwargs.pop('audit_log', True)  # Default to True but ignore it
        case_id = kwargs.pop('case_id', None)

        # Try to get the username and role from Streamlit session state
        username = None
        user_role = None
        try:
            import streamlit as st
            if 'user_id' in st.session_state and st.session_state['user_id'] is not None:
                username = st.session_state['user_id']
                if 'user_role' in st.session_state:
                    user_role = st.session_state['user_role']
        except (ImportError, Exception):
            pass

        # Prepend username and role to message if available
        original_msg = msg
        if username:
            prefix = f"User: {username}"
            if user_role:
                prefix += f", Role: {user_role}"
            prefix += " - "
            msg = f"{prefix}{msg}"

        # Call the original logging function with the possibly modified message
        result = func(self, msg, *args, **kwargs)

        # If case_id is provided, log to the audit case log (regardless of audit_log parameter)
        if case_id is not None:
            # Get audit case logger
            audit_logger = get_audit_case_logger(case_id)

            # Use the same level as the original call
            level_name = func.__name__.upper()
            level = getattr(logging, level_name)

            # Log the message ensuring it has the username
            audit_logger.log(level, msg, *args)

        return result

    return wrapper


# Patch the Logger class to add the audit_log parameter
class AuditableLogger(logging.Logger):
    @add_audit_log_parameter
    def debug(self, msg, *args, **kwargs):
        """
        Logs a debug message along with any additional arguments and keyword arguments
        using the underlying logging mechanism.

        This method extends the standard debug log functionality by allowing
        added customization or operations through the `add_audit_log_parameter`
        decorator. It forwards the provided message (`msg`) and optional
        arguments (`args` and `kwargs`) to its superclass implementation
        to handle the actual logging.

        :param msg: The debug message to be logged.
        :param args: Additional positional arguments to be passed to the
            superclass's logging method.
        :param kwargs: Additional keyword arguments to be passed to the
            superclass's logging method.
        :return: The result of the superclass's debug logging call.
        """
        return super().debug(msg, *args, **kwargs)

    @add_audit_log_parameter
    def info(self, msg, *args, **kwargs):
        """
        Logs a message with the INFO level. This method is a wrapper for the logging functionality,
        invoking the parent class's `info` method while allowing addition of audit log parameters
        if the decorator modifies or processes such parameters.

        :param msg: The log message to record.
        :param args: Additional positional arguments passed to the logger.
        :param kwargs: Additional keyword arguments passed to the logger.
        :return: The result returned by the parent class's `info` method.
        """
        return super().info(msg, *args, **kwargs)

    @add_audit_log_parameter
    def warning(self, msg, *args, **kwargs):
        """
        Logs a warning message with the provided parameters. This method allows
        the inclusion of additional arguments and keyword arguments that can
        customize the log message or provide supplementary information.

        This method wraps around the parent class's `warning` method to leverage
        its functionality while allowing additional control through the
        `@add_audit_log_parameter` decorator.

        :param msg: The warning message to log.
        :param args: Additional positional arguments passed to the overridden
            `warning` method.
        :param kwargs: Additional keyword arguments passed to the overridden
            `warning` method.
        :return: The result of the parent class's `warning` method.
        """
        return super().warning(msg, *args, **kwargs)

    @add_audit_log_parameter
    def error(self, msg, *args, **kwargs):
        """
        Logs an error message along with any additional arguments or keyword arguments.

        Delegates the logging functionality to the parent class's `error` method, passing
        all provided arguments and keyword arguments. This method is typically used to
        record error-level log messages in an audit trail.

        :param msg: The error message to log.
        :type msg: str
        :param args: Additional positional arguments to include in the log entry.
        :type args: tuple
        :param kwargs: Additional keyword arguments to include in the log entry.
        :type kwargs: dict
        :return: The result of the parent class's `error` method.
        """
        return super().error(msg, *args, **kwargs)

    @add_audit_log_parameter
    def critical(self, msg, *args, **kwargs):
        """
        Logs a critical message, typically indicating a serious failure,
        error, or an exceptional condition that requires immediate
        attention. This method delegates the actual logging behavior
        to the parent class's `critical` method, ensuring consistent
        handling of message formatting and any additional audit log
        parameter functionality.

        :param msg: The message to be logged. Can include formatting placeholders.
        :type msg: str
        :param args: Additional positional arguments to format the message, if any.
        :type args: tuple
        :param kwargs: Additional keyword arguments for customization or compatibility purposes.
        :type kwargs: dict
        :return: The result of calling the parent class's critical method.
        """
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
    Configures the global logger to log messages to both the console and a file.
    The function sets up the logging directory, creates file and console handlers,
    initializes a formatter with the specified format, and applies logging levels
    to both the file and console handlers. The logger is configured for global use.

    :param console_level: Logging level for the console handler.
    :type console_level: int
    :param file_level: Logging level for the file handler.
    :type file_level: int
    :param logging_format: The logging format string used by the formatter.
    :type logging_format: str
    :param logging_directory: The directory path where log files will be written.
    :type logging_directory: str
    :return: The globally configured logger instance.
    :rtype: logging.Logger
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
    Creates or retrieves a logger specific to an audit case. The logger is set up
    to handle file-based logging for the particular case. If the logger does not
    already exist, it creates and configures it, ensuring the necessary logging
    directory and files exist. Additionally, it prevents propagation to parent
    loggers and schedules initialization if the log file is new.

    :param case_id: The unique identifier of the audit case for which the logger
        is created or retrieved.
    :type case_id: int
    :return: A logger instance that writes audit logs for the specific case.
    :rtype: logging.Logger
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
    Configures a custom logger by attaching handlers if not already present. The logger will log
    messages to both a specified file and the console. The logging format includes timestamp,
    logger name, log level, and the message, and is applied to all handlers.

    :param logger: The logger instance to be configured
    :type logger: logging.Logger
    :param log_file: The file path where log messages will be written
    :type log_file: str
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
    Initializes the audit log for a specific case by recording various stages of the audit case
    workflow, such as case creation, document processing, verification, certificate generation,
    process completion, and archiving. The function interacts with the database to retrieve
    necessary case and document information and writes these details into an audit log file.

    :param case_id: The identifier of the audit case for which the audit log is to be initialized.
    :type case_id: int
    :param db: An optional database instance to be used for querying case and document information.
                If not provided, a default database instance will be used.
    :type db: Database, optional
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
        # TODO: Get back to this

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
    Processes pending log initializations. This function is responsible for iterating
    through the global `_pending_log_initializations` list, initializing audit logs
    for the respective cases. If the database connection is not provided, it fetches
    an instance of the database. Any errors during the log initialization are logged
    without halting the processing of subsequent cases. After successful processing,
    the pending log initialization list is cleared.

    :param db: Database connection instance.
    :type db: Optional[Database]
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

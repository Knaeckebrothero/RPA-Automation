"""
This is a custom logger configuration snippet that can be used to configure a custom logger for your application.
https://docs.python.org/3/library/logging.html?highlight=logger#module-logging
"""
import os
import logging


def configure_custom_logger(
        module_name: str,  # = __name__,
        console_level: int = 20,
        file_level: int = 20,
        logging_format: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        logging_directory: str | None = None,
        separate_log_file: bool = False
        ) -> logging.Logger:
    """
    This function configures a custom logger for printing and saving logs in a logfile.

    :param module_name: Name for the logging module, could be __name__ or a custom name.
    :param console_level: The logging level for logging in the console.
    :param file_level: The logging level for logging in the logfile.
    :param logging_format: Format used for logging.
    :param logging_directory: Path for the directory where the log files should be saved to.
    :param separate_log_file: If True, a separate log file will be created for this logger.

    :return: A configured logger object.
    """
    logger = logging.getLogger(logging.getLoggerClass().root.name + "." + module_name)
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(logging_format)

    # Set and create the logging directory if it does not exist
    if logging_directory is None:
        logging_directory = './logs/'
    if not os.path.exists(logging_directory):
        os.makedirs(logging_directory)

    # File handler for writing logs to a file
    if separate_log_file:
        file_handler = logging.FileHandler(logging_directory + module_name + '.log')
    else:
        file_handler = logging.FileHandler(logging_directory + 'log.log')

    file_handler.setFormatter(formatter)
    file_handler.setLevel(file_level)
    logger.addHandler(file_handler)

    # TODO: Store logs in database log level

    # Console (stream) handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(console_level)
    logger.addHandler(console_handler)

    return logger

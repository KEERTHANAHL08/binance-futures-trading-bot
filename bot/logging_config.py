import logging
import os

def setup_logging():
    """Configures the logging system for the trading bot."""
    log_file = "trading_bot.log"
    
    logger = logging.getLogger("trading_bot")
    logger.setLevel(logging.DEBUG)
    
    # Check if handlers already exist to prevent duplicate logging
    if logger.handlers:
        return logger

    # Formatter for file logging - includes line numbers, funcNames, and exact timestamp
    file_formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s [%(name)s:%(funcName)s:%(lineno)d] %(message)s"
    )
    
    # Formatter for console logging - simple and clear
    console_formatter = logging.Formatter(
        "[%(levelname)s] %(message)s"
    )

    # File handler (logs all details, down to DEBUG level)
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)

    # Console handler (logs only INFO and above to avoid cluttering stdout)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)

    # Add handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

# Expose a pre-configured logger instance
logger = setup_logging()

import logging
import sys
from logging.handlers import RotatingFileHandler
from config import LOG_LEVEL, LOG_FILE

def setup_logger(name='crypto_trading_bot'):
    """Configure and return a logger instance with both file and console handlers."""
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)
    
    # Prevent duplicate handlers
    if logger.handlers:
        return logger
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )
    
    try:
        # File handler (with rotation)
        file_handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setFormatter(detailed_formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"Warning: Could not set up file logging: {e}")
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # Set logging level
    try:
        numeric_level = getattr(logging, LOG_LEVEL.upper())
        logger.setLevel(numeric_level)
    except (AttributeError, TypeError) as e:
        print(f"Warning: Invalid log level {LOG_LEVEL}, defaulting to INFO")
        logger.setLevel(logging.INFO)
    
    return logger

# Create a default logger instance
logger = setup_logger()

def get_logger(name=None):
    """Get a logger instance with the specified name."""
    if name:
        return setup_logger(name)
    return logger
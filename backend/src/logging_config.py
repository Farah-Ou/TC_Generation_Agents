import logging

# Configure the logging module
logging.basicConfig(
    level=logging.INFO,  # Set log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",  # Log format
)

logger = logging.getLogger(__name__)  # Create a logger instance

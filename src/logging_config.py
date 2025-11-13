"""
Logging configuration for Context-Aware Research Assistant.

Provides centralized logging setup with:
- Colored console output (development)
- File logging with rotation
- Structured logging for services
- Debug logging for data ingestion pipeline
"""

import logging
import logging.handlers
from pathlib import Path
import sys
from typing import Optional

# Create logs directory if it doesn't exist
LOGS_DIR = Path(__file__).parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output."""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[41m', # Red background
    }
    RESET = '\033[0m'
    
    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.msg = f"{log_color}{record.msg}{self.RESET}"
        return super().format(record)


def configure_logging(
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    use_colors: bool = True
) -> logging.Logger:
    """
    Configure root logger with console and file handlers.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path. If None, uses default in logs/ directory
        use_colors: Whether to use colored output for console
        
    Returns:
        Configured root logger
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    
    if use_colors:
        console_formatter = ColoredFormatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    else:
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler with rotation
    if log_file is None:
        log_file = LOGS_DIR / "app.log"
    else:
        log_file = Path(log_file)
    
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(level)
    
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


# Module-level logger setup
# This runs when the module is imported
_logger = get_logger(__name__)


# Pre-configured loggers for key modules
def get_data_ingestion_logger() -> logging.Logger:
    """Get logger for data ingestion pipeline."""
    return get_logger("data_ingestion")


def get_parser_logger() -> logging.Logger:
    """Get logger for TensorLake parser."""
    return get_logger("data_ingestion.parser")


def get_embedder_logger() -> logging.Logger:
    """Get logger for Gemini embedder."""
    return get_logger("data_ingestion.embedder")


def get_milvus_logger() -> logging.Logger:
    """Get logger for Milvus loader."""
    return get_logger("data_ingestion.milvus")


def get_orchestrator_logger() -> logging.Logger:
    """Get logger for crew orchestrator."""
    return get_logger("orchestrator")


def get_service_logger(service_name: str) -> logging.Logger:
    """Get logger for a specific service."""
    return get_logger(f"services.{service_name}")

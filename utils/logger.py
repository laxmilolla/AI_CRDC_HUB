"""
Centralized logging configuration for AI_CRDC_HUB
"""
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logger(name: str = "ai_crdc_hub", log_level: str = "INFO") -> logging.Logger:
    """
    Set up and configure logger with file rotation
    
    Args:
        name: Logger name
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    
    Returns:
        Configured logger instance
    """
    # Configure root logger to ensure all child loggers propagate
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Set root to DEBUG to capture all levels
    
    # Only add handlers to root logger if not already configured
    if not root_logger.handlers:
        # Create logs directory if it doesn't exist
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # File handler with rotation
        log_file = log_dir / "app.log"
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=30,  # Keep 30 days of logs
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Add handlers to root logger
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
    
    # Get named logger and set its level
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    logger.propagate = True  # Ensure propagation to root logger
    
    return logger


def get_logger(name: str = "ai_crdc_hub") -> logging.Logger:
    """
    Get existing logger or create new one
    
    Args:
        name: Logger name
    
    Returns:
        Logger instance
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        log_level = os.getenv("LOG_LEVEL", "INFO")
        logger = setup_logger(name, log_level)
    return logger


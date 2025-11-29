"""Logging module for the AI Agent."""
import logging
import os
from datetime import datetime
from pathlib import Path
from config import Config


class AgentLogger:
    """Logger for agent actions and events."""
    
    def __init__(self):
        """Initialize the logger."""
        self.logger = logging.getLogger("AIAgent")
        self.logger.setLevel(getattr(logging, Config.LOG_LEVEL))
        
        # Create logs directory if it doesn't exist
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # File handler
        log_file = log_dir / Config.LOG_FILE
        file_handler = logging.FileHandler(log_file)
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
        
        # Add handlers
        if not self.logger.handlers:
            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)
    
    def log_action(self, action: str, details: dict = None):
        """Log an action taken by the agent."""
        message = f"ACTION: {action}"
        if details:
            message += f" | Details: {details}"
        self.logger.info(message)
    
    def log_error(self, error: str, exception: Exception = None):
        """Log an error."""
        message = f"ERROR: {error}"
        if exception:
            message += f" | Exception: {str(exception)}"
        self.logger.error(message, exc_info=exception)
    
    def log_llm_request(self, prompt: str, provider: str):
        """Log an LLM request."""
        self.logger.debug(f"LLM Request to {provider}: {prompt[:100]}...")
    
    def log_llm_response(self, response: str, provider: str):
        """Log an LLM response."""
        self.logger.debug(f"LLM Response from {provider}: {response[:100]}...")
    
    def log_safety_check(self, check_type: str, passed: bool, details: str = None):
        """Log a safety check."""
        status = "PASSED" if passed else "FAILED"
        message = f"SAFETY CHECK ({check_type}): {status}"
        if details:
            message += f" | {details}"
        self.logger.warning(message)


# Global logger instance
logger = AgentLogger()


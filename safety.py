"""Safety checks and validation for the AI Agent."""
import re
from typing import Optional, Tuple
from logger import logger


class SafetyChecker:
    """Safety checks for LLM outputs and actions."""
    
    # Dangerous patterns that should trigger confirmation
    DANGEROUS_PATTERNS = [
        r'rm\s+-rf',  # Dangerous file deletion
        r'del\s+/[fs]',  # Windows dangerous deletion
        r'format\s+',  # Disk formatting
        r'shutdown\s+',  # System shutdown
        r'reboot\s+',  # System reboot
        r'kill\s+',  # Process killing
        r'drop\s+database',  # Database deletion
        r'truncate\s+table',  # Table truncation
        r'delete\s+from\s+\w+\s+where\s+1\s*=\s*1',  # Delete all rows
    ]
    
    # File operations that might be destructive
    DESTRUCTIVE_FILE_OPS = [
        'delete', 'remove', 'truncate', 'overwrite', 'format'
    ]
    
    @classmethod
    def validate_action(cls, action_type: str, action_details: dict) -> Tuple[bool, Optional[str]]:
        """
        Validate an action before execution.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check for dangerous patterns in command strings
        if 'command' in action_details:
            command = str(action_details['command']).lower()
            for pattern in cls.DANGEROUS_PATTERNS:
                if re.search(pattern, command):
                    return False, f"Dangerous pattern detected: {pattern}"
        
        # Validate file operations
        if action_type == 'file_operation':
            operation = action_details.get('operation', '').lower()
            if operation in cls.DESTRUCTIVE_FILE_OPS:
                # This will require confirmation, but is still valid
                logger.log_safety_check(
                    "destructive_file_operation",
                    True,
                    f"Destructive operation '{operation}' requires confirmation"
                )
        
        return True, None
    
    @classmethod
    def requires_confirmation(cls, action_type: str, action_details: dict) -> bool:
        """Check if an action requires user confirmation."""
        # Destructive file operations
        if action_type == 'file_operation':
            operation = action_details.get('operation', '').lower()
            if operation in cls.DESTRUCTIVE_FILE_OPS:
                return True
        
        # System commands
        if action_type == 'system_command':
            command = str(action_details.get('command', '')).lower()
            dangerous_keywords = ['rm', 'del', 'format', 'shutdown', 'reboot', 'kill']
            if any(keyword in command for keyword in dangerous_keywords):
                return True
        
        # Database operations
        if action_type == 'database_operation':
            operation = action_details.get('operation', '').lower()
            if operation in ['delete', 'drop', 'truncate']:
                return True
        
        # API calls that modify data
        if action_type == 'api_call':
            method = action_details.get('method', '').upper()
            if method in ['DELETE', 'PUT', 'PATCH']:
                return True
        
        return False
    
    @classmethod
    def sanitize_command(cls, command: str) -> str:
        """Sanitize a command string to prevent injection attacks."""
        # Remove potentially dangerous characters
        dangerous_chars = [';', '&&', '||', '`', '$(']
        sanitized = command
        for char in dangerous_chars:
            if char in sanitized:
                logger.log_safety_check(
                    "command_sanitization",
                    False,
                    f"Removed dangerous character: {char}"
                )
                sanitized = sanitized.replace(char, '')
        
        return sanitized.strip()


"""Action Interpreter and Executor for the AI Agent."""
import json
import subprocess
import os
import requests
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from logger import logger
from safety import SafetyChecker


class ActionExecutor:
    """Interprets LLM outputs and executes actions."""
    
    def __init__(self):
        """Initialize the action executor."""
        self.safety_checker = SafetyChecker()
    
    def parse_llm_response(self, response: str) -> Optional[Dict[str, Any]]:
        """
        Parse LLM response to extract action information.
        
        Args:
            response: The raw LLM response
            
        Returns:
            Parsed action dictionary or None if parsing fails
        """
        try:
            # Try to extract JSON from the response
            # Look for JSON block in markdown code fences
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
            elif "```" in response:
                json_start = response.find("```") + 3
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
            else:
                # Try to find JSON object in the response
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = response[json_start:json_end]
                else:
                    # If no JSON found, treat as information response
                    return {
                        "action_type": "information",
                        "action_details": {
                            "message": response
                        },
                        "explanation": "LLM provided information without structured action"
                    }
            
            action = json.loads(json_str)
            return action
            
        except json.JSONDecodeError as e:
            logger.log_error("Failed to parse LLM response as JSON", e)
            # Fallback: treat as information
            return {
                "action_type": "information",
                "action_details": {
                    "message": response
                },
                "explanation": "Could not parse as structured action"
            }
        except Exception as e:
            logger.log_error("Error parsing LLM response", e)
            return None
    
    def execute_action(self, action: Dict[str, Any], require_confirmation: bool = True) -> Tuple[bool, str]:
        """
        Execute an action based on the parsed LLM response.
        
        Args:
            action: The parsed action dictionary
            require_confirmation: Whether to require confirmation for dangerous operations
            
        Returns:
            Tuple of (success, message)
        """
        action_type = action.get("action_type", "unknown")
        action_details = action.get("action_details", {})
        explanation = action.get("explanation", "No explanation provided")
        
        logger.log_action(action_type, action_details)
        
        # Validate action
        is_valid, error_msg = self.safety_checker.validate_action(action_type, action_details)
        if not is_valid:
            return False, f"Action validation failed: {error_msg}"
        
        # Check if confirmation is required
        needs_confirmation = self.safety_checker.requires_confirmation(action_type, action_details)
        if needs_confirmation and require_confirmation:
            return None, "CONFIRMATION_REQUIRED"  # Special return value
        
        # Execute based on action type
        try:
            if action_type == "file_operation":
                return self._execute_file_operation(action_details)
            elif action_type == "system_command":
                return self._execute_system_command(action_details)
            elif action_type == "api_call":
                return self._execute_api_call(action_details)
            elif action_type == "database_operation":
                return self._execute_database_operation(action_details)
            elif action_type == "information":
                return self._execute_information(action_details)
            else:
                return False, f"Unknown action type: {action_type}"
                
        except Exception as e:
            logger.log_error(f"Error executing {action_type}", e)
            return False, f"Execution error: {str(e)}"
    
    def _execute_file_operation(self, details: Dict[str, Any]) -> Tuple[bool, str]:
        """Execute a file operation."""
        operation = details.get("operation", "").lower()
        path = details.get("path", "")
        
        if not path:
            return False, "No file path provided"
        
        file_path = Path(path)
        
        try:
            if operation == "read":
                if not file_path.exists():
                    return False, f"File not found: {path}"
                content = file_path.read_text(encoding='utf-8')
                return True, f"File content:\n{content}"
                
            elif operation == "write":
                content = details.get("content", "")
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(content, encoding='utf-8')
                return True, f"Successfully wrote to {path}"
                
            elif operation == "create":
                content = details.get("content", "")
                if file_path.exists():
                    return False, f"File already exists: {path}"
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(content, encoding='utf-8')
                return True, f"Successfully created {path}"
                
            elif operation == "delete":
                if not file_path.exists():
                    return False, f"File not found: {path}"
                file_path.unlink()
                return True, f"Successfully deleted {path}"
                
            elif operation == "list":
                if not file_path.exists():
                    return False, f"Path not found: {path}"
                if file_path.is_dir():
                    files = [f.name for f in file_path.iterdir()]
                    return True, f"Directory contents:\n" + "\n".join(files)
                else:
                    return False, f"Path is not a directory: {path}"
            else:
                return False, f"Unknown file operation: {operation}"
                
        except Exception as e:
            return False, f"File operation error: {str(e)}"
    
    def _execute_system_command(self, details: Dict[str, Any]) -> Tuple[bool, str]:
        """Execute a system command."""
        command = details.get("command", "")
        if not command:
            return False, "No command provided"
        
        # Sanitize command
        command = self.safety_checker.sanitize_command(command)
        
        try:
            # Execute command
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                output = result.stdout if result.stdout else "Command executed successfully"
                return True, output
            else:
                error = result.stderr if result.stderr else "Command failed"
                return False, f"Command error: {error}"
                
        except subprocess.TimeoutExpired:
            return False, "Command timed out after 30 seconds"
        except Exception as e:
            return False, f"Command execution error: {str(e)}"
    
    def _execute_api_call(self, details: Dict[str, Any]) -> Tuple[bool, str]:
        """Execute an API call."""
        method = details.get("method", "GET").upper()
        url = details.get("url", "")
        data = details.get("data", {})
        headers = details.get("headers", {"Content-Type": "application/json"})
        
        if not url:
            return False, "No URL provided"
        
        try:
            if method == "GET":
                response = requests.get(url, headers=headers, timeout=10)
            elif method == "POST":
                response = requests.post(url, json=data, headers=headers, timeout=10)
            elif method == "PUT":
                response = requests.put(url, json=data, headers=headers, timeout=10)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers, timeout=10)
            else:
                return False, f"Unsupported HTTP method: {method}"
            
            response.raise_for_status()
            return True, f"API call successful: {response.text[:500]}"
            
        except requests.exceptions.RequestException as e:
            return False, f"API call error: {str(e)}"
    
    def _execute_database_operation(self, details: Dict[str, Any]) -> Tuple[bool, str]:
        """Execute a database operation."""
        # Note: This is a placeholder. In a real implementation, you would
        # connect to a database and execute the query.
        operation = details.get("operation", "")
        query = details.get("query", "")
        
        return False, f"Database operations are not fully implemented. Operation: {operation}, Query: {query}"
    
    def _execute_information(self, details: Dict[str, Any]) -> Tuple[bool, str]:
        """Handle information-only responses."""
        message = details.get("message", "No message provided")
        return True, message


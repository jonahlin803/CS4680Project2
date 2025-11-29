"""LLM Integration Module for connecting to various LLM providers."""
import time
from typing import Optional, Dict, Any
from config import Config
from logger import logger


class LLMIntegration:
    """Integration with various LLM providers."""
    
    def __init__(self):
        """Initialize the LLM integration."""
        self.provider = Config.LLM_PROVIDER
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the appropriate LLM client based on provider."""
        try:
            if self.provider == "openai":
                from openai import OpenAI
                if not Config.OPENAI_API_KEY:
                    raise ValueError("OPENAI_API_KEY not set")
                self.client = OpenAI(api_key=Config.OPENAI_API_KEY)
                self.model = Config.OPENAI_MODEL
                
            elif self.provider == "anthropic":
                from anthropic import Anthropic
                if not Config.ANTHROPIC_API_KEY:
                    raise ValueError("ANTHROPIC_API_KEY not set")
                self.client = Anthropic(api_key=Config.ANTHROPIC_API_KEY)
                self.model = Config.ANTHROPIC_MODEL
                
            elif self.provider == "google":
                import google.generativeai as genai
                if not Config.GOOGLE_API_KEY:
                    raise ValueError("GOOGLE_API_KEY not set")
                genai.configure(api_key=Config.GOOGLE_API_KEY)
                self.client = genai
                self.model = Config.GOOGLE_MODEL
                
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")
                
        except ImportError as e:
            raise ImportError(f"Required package not installed for {self.provider}: {e}")
    
    def send_prompt(self, prompt: str, max_retries: int = 3, system_prompt: Optional[str] = None) -> str:
        """
        Send a prompt to the LLM and get a response.
        
        Args:
            prompt: The prompt to send
            max_retries: Maximum number of retry attempts
            system_prompt: Optional custom system prompt (uses default if not provided)
            
        Returns:
            The LLM response text
        """
        logger.log_llm_request(prompt, self.provider)
        
        # Use custom system prompt if provided, otherwise use default
        system = system_prompt if system_prompt is not None else self._get_system_prompt()
        
        for attempt in range(max_retries):
            try:
                if self.provider == "openai":
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": system},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.7
                    )
                    result = response.choices[0].message.content
                    
                elif self.provider == "anthropic":
                    response = self.client.messages.create(
                        model=self.model,
                        max_tokens=4096,
                        system=system,
                        messages=[
                            {"role": "user", "content": prompt}
                        ]
                    )
                    result = response.content[0].text
                    
                elif self.provider == "google":
                    model = self.client.GenerativeModel(self.model)
                    full_prompt = f"{system}\n\nUser: {prompt}\n\nAssistant:"
                    response = model.generate_content(full_prompt)
                    result = response.text
                
                logger.log_llm_response(result, self.provider)
                return result
                
            except Exception as e:
                error_msg = str(e)
                
                # Handle rate limiting
                if "rate limit" in error_msg.lower() or "429" in error_msg:
                    wait_time = (attempt + 1) * 2  # Exponential backoff
                    logger.log_error(f"Rate limit hit, waiting {wait_time}s", e)
                    time.sleep(wait_time)
                    continue
                
                # Handle other API errors
                if attempt < max_retries - 1:
                    logger.log_error(f"API error (attempt {attempt + 1}/{max_retries})", e)
                    time.sleep(1)
                else:
                    logger.log_error("Failed to get LLM response after retries", e)
                    raise
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt that instructs the LLM on how to format responses."""
        return """You are an AI assistant that helps users by performing actions based on their requests.

When a user asks you to do something, respond in the following JSON format:
{
    "action_type": "file_operation|system_command|api_call|database_operation|information",
    "action_details": {
        "operation": "description of the operation",
        "parameters": {...}
    },
    "explanation": "brief explanation of what you're doing"
}

For file operations, use:
- "action_type": "file_operation"
- "operation": "read|write|create|delete|list"
- "path": "file path"
- "content": "content for write/create operations"

For system commands, use:
- "action_type": "system_command"
- "command": "the command to execute"

For API calls, use:
- "action_type": "api_call"
- "method": "GET|POST|PUT|DELETE"
- "url": "API endpoint"
- "data": {...}

For database operations, use:
- "action_type": "database_operation"
- "operation": "query|insert|update|delete"
- "query": "SQL query or description"

If you're just providing information without performing an action, use:
- "action_type": "information"
- "message": "the information to provide"

Always be clear and specific about what action you're taking."""


"""Configuration management for the AI Agent."""
import os
from dotenv import load_dotenv
from typing import Optional

# Load environment variables
load_dotenv()


class Config:
    """Configuration class for managing settings."""
    
    # LLM Provider settings
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai").lower()
    
    # OpenAI settings
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4")
    
    # Anthropic settings
    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-3-opus-20240229")
    
    # Google settings
    GOOGLE_API_KEY: Optional[str] = os.getenv("GOOGLE_API_KEY")
    GOOGLE_MODEL: str = os.getenv("GOOGLE_MODEL", "gemini-pro")
    
    # Logging settings
    LOG_FILE: str = os.getenv("LOG_FILE", "agent.log")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    @classmethod
    def validate(cls) -> tuple[bool, Optional[str]]:
        """Validate that required configuration is present."""
        if cls.LLM_PROVIDER == "openai":
            if not cls.OPENAI_API_KEY:
                return False, "OPENAI_API_KEY is required when using OpenAI provider"
        elif cls.LLM_PROVIDER == "anthropic":
            if not cls.ANTHROPIC_API_KEY:
                return False, "ANTHROPIC_API_KEY is required when using Anthropic provider"
        elif cls.LLM_PROVIDER == "google":
            if not cls.GOOGLE_API_KEY:
                return False, "GOOGLE_API_KEY is required when using Google provider"
        else:
            return False, f"Unknown LLM provider: {cls.LLM_PROVIDER}"
        
        return True, None


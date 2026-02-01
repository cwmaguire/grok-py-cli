"""Configuration and settings management."""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()


def get_api_key() -> Optional[str]:
    """Get Grok API key from environment variables."""
    return os.getenv("GROK_API_KEY") or os.getenv("XAI_API_KEY")


def get_tavily_api_key() -> Optional[str]:
    """Get Tavily API key for web search."""
    return os.getenv("TAVILY_API_KEY")


def get_morph_api_key() -> Optional[str]:
    """Get Morph API key for advanced editing."""
    return os.getenv("MORPH_API_KEY")


def get_config_dir() -> Path:
    """Get the configuration directory."""
    config_dir = Path.home() / ".config" / "grok-cli"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_config_path() -> Path:
    """Get the path to the configuration file."""
    return get_config_dir() / "config.json"


def get_custom_instructions_path() -> Path:
    """Get the path to custom instructions file."""
    return get_config_dir() / "custom_instructions.md"


def get_conversation_history_path() -> Path:
    """Get the path to conversation history file."""
    return get_config_dir() / "conversation_history.json"


def load_custom_instructions() -> Optional[str]:
    """Load custom instructions from file."""
    path = get_custom_instructions_path()
    if path.exists():
        return path.read_text().strip()
    return None


def save_custom_instructions(instructions: str) -> None:
    """Save custom instructions to file."""
    path = get_custom_instructions_path()
    path.write_text(instructions)


class SettingsManager:
    """Manager for application settings."""

    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or str(get_config_path())

    def load_settings(self) -> dict:
        """Load settings from file or return defaults."""
        # Dummy implementation
        return {
            'api_key': get_api_key(),
            'model': 'grok-beta',
            'tavily_api_key': get_tavily_api_key(),
            'morph_api_key': get_morph_api_key(),
        }

    def save_settings(self, settings: dict) -> None:
        """Save settings to file."""
        # Dummy implementation
        pass
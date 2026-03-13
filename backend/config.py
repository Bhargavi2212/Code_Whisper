"""Application configuration loaded from environment variables."""

from pathlib import Path

from pydantic_settings import BaseSettings

# Resolve .env from project root (matches docker-compose which uses root .env)
_env_path = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Gemini
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash-native-audio-preview-12-2025"

    # Audio
    send_sample_rate: int = 16000
    receive_sample_rate: int = 24000

    # Screen capture
    frame_rate: int = 1
    frame_size: int = 768

    # Server
    host: str = "0.0.0.0"
    backend_port: int = 8000
    frontend_port: int = 3000

    class Config:
        env_file = str(_env_path) if _env_path.exists() else ".env"
        env_file_encoding = "utf-8"


settings = Settings()

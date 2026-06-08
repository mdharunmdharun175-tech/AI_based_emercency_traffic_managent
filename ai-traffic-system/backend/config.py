"""
Application configuration — reads from environment / .env file.
All secrets and tunables go here; never hardcode them in service files.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "ai_traffic"

    # AI models
    MODEL_PATH: str = "./ml/weights/best.pt"
    SIREN_MODEL_PATH: str = "./ml/weights/siren_cnn.h5"
    CONFIDENCE_THRESHOLD: float = 0.55

    # Signal control
    ARDUINO_PORT: str = "/dev/ttyUSB0"
    ARDUINO_BAUD: int = 9600
    GREEN_CORRIDOR_DURATION: int = 30   # seconds
    WATCHDOG_TIMEOUT: int = 10          # seconds before safe-state

    # External APIs
    GOOGLE_MAPS_API_KEY: str = ""

    # Security
    SECRET_KEY: str = "change-this-secret-key-in-production"
    API_KEY_HEADER: str = "X-API-Key"
    REQUIRE_API_KEY: bool = False       # set True in production

    # CORS
    ALLOWED_ORIGINS: list = ["http://localhost:3000", "http://localhost:5173"]

    # Logging
    LOG_LEVEL: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Core application settings loaded from environment variables or .env file.
    Utilizes pydantic_settings for strict type validation of env vars.
    """
    # Alpaca API Credentials
    ALPACA_API_KEY: str = ""
    ALPACA_SECRET_KEY: str = ""
    ALPACA_PAPER: bool = True
    
    # LLM API Credentials
    OPENAI_API_KEY: str = ""
    
    # Event-Driven Engine Config
    POLL_INTERVAL_SECONDS: int = 180  # 3 minutes as per architecture

    # Hardcoded Thursday EOD Liquidation (Day 3 = Thursday, 15:30 ET)
    LIQUIDATION_DAY_OF_WEEK: int = 3
    LIQUIDATION_HOUR: int = 15
    LIQUIDATION_MINUTE: int = 30
    LIQUIDATION_TIMEZONE: str = "America/New_York"

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        extra="ignore"
    )

settings = Settings()

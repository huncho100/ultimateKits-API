from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application configuration.

    Values are loaded from environment variables
    and the .env file.
    """

    # ==========================================
    # Application
    # ==========================================

    APP_NAME: str = "Ultimate Kits API"

    APP_VERSION: str = "1.0.0"

    DEBUG: bool = True

    # ==========================================
    # Frontend
    # ==========================================

    FRONTEND_URL: str = "http://localhost:5173"

    # ==========================================
    # Database
    # ==========================================

    DATABASE_URL: str

    # ==========================================
    # Authentication / JWT
    # ==========================================

    JWT_SECRET_KEY: str

    JWT_ALGORITHM: str = "HS256"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # ==========================================
    # Pydantic Settings Configuration
    # ==========================================

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


settings = Settings()
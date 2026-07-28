from dotenv import load_dotenv
from fastapi.templating import Jinja2Templates
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()

# Settings class
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # ==== DATABASE ====
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str
    DB_PORT: int = 3306
    DB_NAME: str

    # ==== DEBUG ====
    DEBUG: bool = False

    # ==== SECURITY ====
    JWT_SECRET: str
    ALGORITHM: str = "HS256"
    TOKEN_EXPIRATION_MINS: int = 1440

    # ==== EXTERNAL APIs ====
    STRIPE_SECRET_KEY: str
    STRIPE_PUBLISHABLE_KEY: str
    STRIPE_WEBHOOK_SECRET: str

settings = Settings()

# Define path for .html templates folder
templates = Jinja2Templates(directory="app/templates")
import os
from pydantic_settings import BaseSettings, SettingsConfigDict

# Ensure we always load from backend/.env regardless of run location
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(BACKEND_DIR, ".env")

class Settings(BaseSettings):
    app_name: str = "BuyWise AI"
    environment: str = "development"
    serpapi_api_key: str = ""
    # We leave database_url as is, which assumes running from backend or project root depending on setup.
    # If run from backend, it targets backend/data/buywise.db
    database_url: str = "sqlite:///../data/buywise.db"

    model_config = SettingsConfigDict(env_file=ENV_PATH, env_file_encoding="utf-8")

settings = Settings()

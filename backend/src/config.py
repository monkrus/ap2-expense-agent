from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    google_api_key: Optional[str] = None
    google_cloud_project: Optional[str] = None
    google_cloud_location: str = "us-central1"
    google_genai_use_vertexai: bool = False
    database_url: str = "postgresql://ap2user:changeme@localhost:5432/expenses"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 60
    cors_origins: list = ["http://localhost:3000", "http://localhost:5173", "http://localhost"]
    environment: str = "development"
    debug: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()

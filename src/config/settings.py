import os
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # API Keys
    SERPAPI_API_KEY: str 
    
    # Model Configuration
    OLLAMA_MODEL: str = "mistral:latest"
    MEMORY_WINDOW: int = 5
    SAVE_HISTORY: bool = True
    
    # Spring Boot API
    SPRING_API_URL: str
    OLLAMA_BASE_URL: str = "http://ollama:11434"

    
    # Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    DATA_DIR: Path = BASE_DIR / "data" / "PDF"
    VECTORSTORE_PATH: Path = BASE_DIR / "data" / "vector_store_faiss"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()

# Ensure directories exist
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
settings.VECTORSTORE_PATH.mkdir(parents=True, exist_ok=True)
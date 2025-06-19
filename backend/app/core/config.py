"""
Configuration management for AI SEC Filing Analyzer.

This module follows SOLID principles for configuration management,
providing a clean interface for application settings.
"""

import os
from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """
    Application settings with environment variable support.
    
    This class demonstrates proper configuration management
    and environment variable handling for production applications.
    """
    
    # Application settings
    app_name: str = Field(default="AI SEC Filing Analyzer", env="APP_NAME")
    debug: bool = Field(default=False, env="DEBUG")
    version: str = Field(default="1.0.0", env="VERSION")
    
    # Google Gemini API configuration
    google_api_key: Optional[str] = Field(default=None, env="GOOGLE_API_KEY")
    gemini_model: str = Field(default="gemini-2.5-flash", env="GEMINI_MODEL")
    
    # Hugging Face configuration
    hf_model_name: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2", 
        env="HF_MODEL_NAME"
    )
    
    # Vector database settings
    vector_db_path: str = Field(default="./chroma_db", env="VECTOR_DB_PATH")
    collection_name: str = Field(default="sec_filings", env="COLLECTION_NAME")
    
    # Document processing settings
    chunk_size: int = Field(default=1000, env="CHUNK_SIZE")
    chunk_overlap: int = Field(default=200, env="CHUNK_OVERLAP")
    max_chunks: int = Field(default=100, env="MAX_CHUNKS")
    
    # API settings
    max_response_length: int = Field(default=4000, env="MAX_RESPONSE_LENGTH")
    request_timeout: int = Field(default=60, env="REQUEST_TIMEOUT")
    
    # Security settings  
    allowed_origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000",
        env="ALLOWED_ORIGINS"
    )
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Ignore extra environment variables
    
    def get_allowed_origins_list(self) -> list[str]:
        """Convert comma-separated origins string to list."""
        if not self.allowed_origins:
            return ["*"]
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


class DevelopmentSettings(Settings):
    """Development-specific settings."""
    debug: bool = True
    

class ProductionSettings(Settings):
    """Production-specific settings with enhanced security."""
    debug: bool = False
    allowed_origins: str = ""  # Must be explicitly set in production


@lru_cache()
def get_settings() -> Settings:
    """
    Get application settings with caching.
    
    This function uses LRU cache to ensure settings are loaded once
    and reused throughout the application lifecycle.
    
    Returns:
        Settings: Application configuration object
    """
    environment = os.getenv("ENVIRONMENT", "development").lower()
    
    if environment == "production":
        return ProductionSettings()
    else:
        return DevelopmentSettings()


def validate_settings(settings: Settings) -> None:
    """
    Validate critical settings for application startup.
    
    Args:
        settings: Application settings to validate
        
    Raises:
        ValueError: If critical settings are missing or invalid
    """
    if not settings.google_api_key:
        raise ValueError(
            "GOOGLE_API_KEY environment variable is required. "
            "Get your free API key at https://aistudio.google.com/"
        )
    
    if settings.chunk_size <= 0:
        raise ValueError("CHUNK_SIZE must be greater than 0")
    
    if settings.chunk_overlap >= settings.chunk_size:
        raise ValueError("CHUNK_OVERLAP must be less than CHUNK_SIZE")


# Global settings instance
settings = get_settings()

# Validate settings on import
try:
    validate_settings(settings)
except ValueError as e:
    print(f"⚠️  Configuration Warning: {e}")
    print("💡 The application may not function properly without proper configuration.") 
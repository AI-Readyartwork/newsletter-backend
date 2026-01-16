from pydantic_settings import BaseSettings
from typing import List, Optional

class Settings(BaseSettings):
    # API Configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    # OpenAI
    OPENAI_API_KEY: str = ""
    
    # OpenRouter (for Perplexity Sonar Pro)
    OPENROUTER_API_KEY: str = ""
    
    # Giphy API
    GIPHY_API_KEY: str = ""
    
    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    
    # ActiveCampaign
    ACTIVECAMPAIGN_URL: str = ""
    ACTIVECAMPAIGN_API_KEY: str = ""
    ACTIVECAMPAIGN_SENDER_NAME: str = "Ready Artwork"
    ACTIVECAMPAIGN_SENDER_EMAIL: str = "ai@readyartwork.com"
    
    # CORS - comma-separated string
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"
    
    # Environment
    ENVIRONMENT: str = "development"
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Convert CORS_ORIGINS string to list"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()

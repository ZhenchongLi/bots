from pydantic_settings import BaseSettings
from typing import Optional, Dict, List
from pydantic import Field, validator
import json


class ModelConfig(BaseSettings):
    name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    max_tokens: Optional[int] = None
    supports_streaming: bool = True
    supports_function_calling: bool = True
    cost_per_1k_input_tokens: Optional[float] = None
    cost_per_1k_output_tokens: Optional[float] = None


class Settings(BaseSettings):
    # API Configuration
    openai_api_key: str
    openai_base_url: str = "https://api.openai.com/v1"
    
    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "info"
    
    # Database Configuration
    database_url: str = "sqlite+aiosqlite:///./logs/proxy.db"
    
    # Qdrant Configuration
    qdrant_url: Optional[str] = None
    qdrant_api_key: Optional[str] = None
    
    # Logging Configuration
    log_file_path: str = "./logs/proxy.log"
    log_retention_days: int = 30
    
    # Model Configuration
    available_models: List[str] = Field(default=[
        "gpt-4",
        "gpt-4-turbo",
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-3.5-turbo",
        "gpt-3.5-turbo-16k",
        "text-embedding-ada-002",
        "text-embedding-3-small",
        "text-embedding-3-large",
        "whisper-1",
        "tts-1",
        "tts-1-hd",
        "dall-e-2",
        "dall-e-3"
    ])
    
    # Custom model mappings for API compatibility
    model_mappings: Dict[str, str] = Field(default={})
    
    # Model validation settings
    validate_models: bool = True
    allow_unknown_models: bool = False

    @validator('available_models', pre=True)
    def parse_available_models(cls, v):
        if isinstance(v, str):
            return [model.strip() for model in v.split(',') if model.strip()]
        return v

    @validator('model_mappings', pre=True)
    def parse_model_mappings(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v) if v.strip() else {}
            except json.JSONDecodeError:
                return {}
        return v

    class Config:
        env_file = ".env"


settings = Settings()
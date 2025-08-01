from pydantic_settings import BaseSettings
from typing import Optional, Dict, List, Any
from pydantic import Field, field_validator, ConfigDict
import orjson as json
from enum import Enum


class PlatformType(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    AZURE_OPENAI = "azure_openai"
    COHERE = "cohere"
    COZE = "coze"
    CUSTOM = "custom"


class Settings(BaseSettings):
    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "info"
    
    # Database Configuration
    database_url: str = "sqlite+aiosqlite:///./data/proxy.db"
    
    # Logging Configuration
    log_file_path: str = "./logs/proxy.log"
    log_retention_days: int = 30
    
    # Authentication Configuration
    enable_client_auth: bool = True
    allow_anonymous_access: bool = False
    
    # Single Model Configuration
    type: PlatformType = PlatformType.OPENAI
    api_key: str = ""
    base_url: str = "https://api.openai.com/v1"
    enabled: bool = True
    default_headers: Dict[str, str] = Field(default_factory=dict)
    timeout: int = 300
    
    # Model-specific settings
    actual_name: str = "gpt-3.5-turbo"
    display_name: Optional[str] = "officeai"
    description: Optional[str] = None
    max_tokens: Optional[int] = 4096
    supports_streaming: bool = True
    supports_function_calling: bool = True
    cost_per_1k_input_tokens: Optional[float] = None
    cost_per_1k_output_tokens: Optional[float] = None
    
    # Platform-specific settings (Coze Bot)
    bot_id: Optional[str] = None
    conversation_id: Optional[str] = None
    

    @field_validator('cost_per_1k_input_tokens', 'cost_per_1k_output_tokens', mode='before')
    def parse_cost_fields(cls, v):
        if v == '' or v is None:
            return None
        return float(v)

    model_config = ConfigDict(env_file=".env")


settings = Settings()
"""Application settings loaded from environment variables."""

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with validation."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # OpenAI Configuration
    openai_api_key: SecretStr = Field(..., description="OpenAI API Key")

    # Amadeus API Configuration
    amadeus_client_id: SecretStr = Field(..., description="Amadeus API Key")
    amadeus_client_secret: SecretStr = Field(..., description="Amadeus API Secret")
    amadeus_hostname: str = Field(
        default="test",
        description="Amadeus environment: 'test' for sandbox, 'production' for live",
    )

    # Server Configuration
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        description="Allowed CORS origins",
    )

    # Agent Configuration
    max_iterations: int = Field(default=25, description="Max agent loop iterations")
    temperature: float = Field(default=0.1, description="LLM temperature")
    model_name: str = Field(default="gpt-4o", description="OpenAI model name")

    # LangSmith Tracing (optional)
    langsmith_api_key: SecretStr | None = Field(default=None)
    langsmith_project: str = Field(default="travel-agent")
    langsmith_tracing: bool = Field(default=False)


# Singleton is created lazily in __init__.py to avoid import-time validation errors

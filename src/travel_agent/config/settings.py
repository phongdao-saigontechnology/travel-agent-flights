"""Application settings loaded from environment variables."""

from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with validation."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # LLM Provider Selection
    llm_provider: Literal["openai", "azure_openai"] = Field(
        default="openai",
        description="LLM provider: 'openai' or 'azure_openai'",
    )

    # OpenAI Configuration (required when llm_provider="openai")
    openai_api_key: SecretStr | None = Field(
        default=None, description="OpenAI API Key"
    )

    # Azure OpenAI Configuration (required when llm_provider="azure_openai")
    azure_openai_api_key: SecretStr | None = Field(
        default=None,
        description="Azure OpenAI API Key",
    )
    azure_openai_endpoint: str | None = Field(
        default=None,
        description="Azure OpenAI endpoint URL",
    )
    azure_openai_deployment_name: str | None = Field(
        default=None,
        description="Azure OpenAI deployment name",
    )
    azure_openai_api_version: str = Field(
        default="2025-04-01-preview",
        description="Azure OpenAI API version",
    )

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
    temperature: float = Field(default=1, description="LLM temperature")
    model_name: str = Field(default="gpt-5.1-mini", description="OpenAI model name")
    reasoning_effort: str = Field(default="low", description="Reasoning effort level")

    # LangSmith Tracing (optional)
    langsmith_api_key: SecretStr | None = Field(default=None)
    langsmith_project: str = Field(default="travel-agent")
    langsmith_tracing: bool = Field(default=False)

    @model_validator(mode="after")
    def validate_provider_config(self) -> "Settings":
        """Validate that required fields are set for the selected provider."""
        if self.llm_provider == "openai":
            if not self.openai_api_key:
                raise ValueError(
                    "OPENAI_API_KEY is required when LLM_PROVIDER is 'openai'"
                )
        elif self.llm_provider == "azure_openai":
            missing = []
            if not self.azure_openai_api_key:
                missing.append("AZURE_OPENAI_API_KEY")
            if not self.azure_openai_endpoint:
                missing.append("AZURE_OPENAI_ENDPOINT")
            if not self.azure_openai_deployment_name:
                missing.append("AZURE_OPENAI_DEPLOYMENT_NAME")
            if missing:
                raise ValueError(
                    f"The following are required when LLM_PROVIDER is 'azure_openai': "
                    f"{', '.join(missing)}"
                )
        return self


# Singleton is created lazily in __init__.py to avoid import-time validation errors

"""Configuration module."""

from travel_agent.config.settings import Settings

# Lazy-load settings to avoid validation errors at import time
_settings = None


def get_settings() -> Settings:
    """Get the settings singleton, loading from environment on first access."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


# For backward compatibility, create a lazy proxy
class _SettingsProxy:
    def __getattr__(self, name):
        return getattr(get_settings(), name)


settings = _SettingsProxy()

__all__ = ["Settings", "settings", "get_settings"]

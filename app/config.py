from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    line_channel_secret: str
    line_channel_access_token: str
    anthropic_api_key: str
    log_level: str = "INFO"
    max_audio_size_mb: int = 100
    claude_model: str = "claude-sonnet-4-5-20250929"
    claude_max_tokens: int = 4096

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


def get_settings() -> Settings:
    return Settings()

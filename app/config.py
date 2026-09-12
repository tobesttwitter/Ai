from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "AI Movie Studio"
    host: str = "0.0.0.0"
    port: int = 8000
    storage_root: Path = Path("./storage")
    max_upload_mb: int = 100
    mock_generation: bool = True
    mock_delay_seconds: float = 0.5
    ffmpeg_binary: str = "ffmpeg"
    comfyui_url: str | None = None
    comfyui_timeout_seconds: float = 30.0
    comfyui_poll_seconds: float = 2.0
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

settings = Settings()

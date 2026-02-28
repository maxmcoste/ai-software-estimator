from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    ANTHROPIC_API_KEY: str
    GITHUB_TOKEN: str = ""
    DEFAULT_MODEL_PATH: Path = Path("EstimateModel/Modello di Stima.md")
    REPORTS_DIR: Path = Path("reports")

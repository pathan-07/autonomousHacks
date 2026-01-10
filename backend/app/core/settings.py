from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    backend_api_key: str | None = None
    database_path: str = "./data/app.sqlite3"
    retention_ttl_seconds: int = 7 * 24 * 60 * 60
    rate_limit_rpm: int = 60

    gemini_api_key: str | None = None
    gemini_model: str = "gemini-1.5-flash"
    gemini_temperature: float = 0.2
    gemini_top_p: float = 0.9
    gemini_max_output_tokens: int = 300
    gemini_system_prompt_path: str = "./prompts/gemini_1_5_system.txt"
    gemini_system_prompt: str | None = None

    def get_gemini_system_prompt(self) -> str:
        if self.gemini_system_prompt and self.gemini_system_prompt.strip():
            return self.gemini_system_prompt.strip()

        p = Path(self.gemini_system_prompt_path)
        if not p.is_absolute():
            p = Path.cwd() / p

        try:
            return p.read_text(encoding="utf-8").strip()
        except FileNotFoundError:
            return ""


settings = Settings()

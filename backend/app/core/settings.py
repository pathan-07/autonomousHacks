from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    backend_api_key: str | None = None
    database_path: str = "./data/app.sqlite3"
    retention_ttl_seconds: int = 7 * 24 * 60 * 60
    rate_limit_rpm: int = 60

    # Optional: Google Safe Browsing URL reputation checks
    safe_browsing_api_key: str | None = None

    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    gemini_models: str | None = None
    gemini_max_models: int = 3
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

    def get_gemini_models(self) -> list[str]:
        """Returns a de-duplicated list of Gemini model ids to use for ensembling."""
        models: list[str] = []
        if self.gemini_models and self.gemini_models.strip():
            for part in self.gemini_models.split(","):
                m = part.strip()
                if m:
                    models.append(m)
        else:
            models.append(self.gemini_model)

        # de-dupe while preserving order
        seen: set[str] = set()
        deduped: list[str] = []
        for m in models:
            if m not in seen:
                seen.add(m)
                deduped.append(m)

        limit = max(1, int(self.gemini_max_models or 1))
        return deduped[:limit]


settings = Settings()

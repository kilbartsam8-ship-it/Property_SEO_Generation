from dataclasses import dataclass
import os
from dotenv import load_dotenv

DEFAULT_MODEL = "llama-3.3-70b-versatile"
DEFAULT_KEYWORDS = "real estate, apartments, new project"
SUMMARY_THRESHOLD = 3000


class ConfigError(Exception):
    """Raised when configuration is invalid."""


@dataclass(frozen=True)
class Settings:
    groq_api_key: str
    model: str = DEFAULT_MODEL
    summarize_long_pdf: bool = True
    summary_threshold: int = SUMMARY_THRESHOLD


def load_settings(model: str = DEFAULT_MODEL, no_summarize: bool = False) -> Settings:
    load_dotenv()
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        raise ConfigError("GROQ_API_KEY not found in .env")

    return Settings(
        groq_api_key=api_key,
        model=model,
        summarize_long_pdf=not no_summarize,
    )

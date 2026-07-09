"""Load configuration from environment variables."""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # OpenAI / OpenRouter API
    # If key starts with 'sk-or-', it's an OpenRouter key
    # and we set the base URL to OpenRouter's endpoint
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "openai/gpt-4o")  # OpenRouter model format

    @property
    def openai_base_url(self) -> str | None:
        """Return base URL for OpenRouter if that's the key type."""
        if self.OPENAI_API_KEY.startswith("sk-or-"):
            return "https://openrouter.ai/api/v1"
        return None  # None means use default OpenAI endpoint

    # Airtable
    AIRTABLE_API_KEY: str = os.getenv("AIRTABLE_API_KEY", "")
    AIRTABLE_BASE_ID: str = os.getenv("AIRTABLE_BASE_ID", "")
    AIRTABLE_GROOM_TABLE: str = os.getenv("AIRTABLE_GROOM_TABLE", "Groom")
    AIRTABLE_BRIDE_TABLE: str = os.getenv("AIRTABLE_BRIDE_TABLE", "Bride")

    # Admin
    ADMIN_PHONE: str = os.getenv("ADMIN_PHONE", "+91 8660038025")
    ADMIN_NAME: str = os.getenv("ADMIN_NAME", "KVRSA Raju")

    # App
    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT: int = int(os.getenv("APP_PORT", "8000"))


settings = Settings()
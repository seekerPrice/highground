"""Explicit runtime settings; private values never appear in repr."""
from dataclasses import dataclass, field
import os
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    gcp_project: str = ""
    telegram_bot_token: str = field(default="", repr=False)
    telegram_webhook_secret: str = field(default="", repr=False)
    hash_salt: str = field(default="", repr=False)
    operator_token: str = field(default="", repr=False)
    vertex_location: str = ""
    gemini_fast_model: str = ""
    gemini_pro_model: str = ""


def load_settings() -> Settings:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)
    env_names = {"operator_token": "DEMO_OPERATOR_TOKEN"}
    return Settings(**{name: os.environ.get(env_names.get(name, name.upper()), "") for name in Settings.__dataclass_fields__})

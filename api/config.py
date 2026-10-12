"""Explicit runtime settings; private values never appear in repr."""
from dataclasses import dataclass, field
import os
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    gcp_project: str = ""
    gcs_bucket: str = ""
    telegram_bot_token: str = field(default="", repr=False)
    telegram_webhook_secret: str = field(default="", repr=False)
    hash_salt: str = field(default="", repr=False)
    operator_token: str = field(default="", repr=False)
    vertex_location: str = ""
    gemini_fast_model: str = ""
    gemini_pro_model: str = ""
    telegram_bot_username: str = ""
    geocoding_user_agent: str = ""
    geocoding_base_url: str = "https://nominatim.openstreetmap.org"
    demo_mode: bool = False
    pubsub_topic: str = "flood-events"
    bigquery_dataset: str = "highground"
    vehicle_action_target_minutes: int = 15
    stock_action_target_minutes: int = 30
    default_alert_radius_m: int = 1000
    destination_search_radius_m: int = 20000

    def __post_init__(self) -> None:
        if type(self.destination_search_radius_m) is not int or not 1 <= self.destination_search_radius_m <= 100000:
            raise ValueError("Destination search radius must be an integer from 1 to 100000")
        if type(self.default_alert_radius_m) is not int or not 1 <= self.default_alert_radius_m <= 10000:
            raise ValueError("Default alert radius must be an integer from 1 to 10000")
        if type(self.vehicle_action_target_minutes) is not int or type(self.stock_action_target_minutes) is not int or not 0 < self.vehicle_action_target_minutes < self.stock_action_target_minutes:
            raise ValueError("Vehicle action target must be positive and earlier than stock")


def load_settings() -> Settings:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)
    env_names = {"operator_token": "DEMO_OPERATOR_TOKEN", "bigquery_dataset": "BQ_DATASET"}
    defaults = Settings()
    values = {name: os.environ.get(env_names.get(name, name.upper()), getattr(defaults, name)) for name in Settings.__dataclass_fields__ if name not in ("demo_mode", "vehicle_action_target_minutes", "stock_action_target_minutes", "default_alert_radius_m", "destination_search_radius_m")}
    demo = os.environ.get("DEMO_MODE", "false").lower()
    if demo not in ("true", "false"):
        raise ValueError("DEMO_MODE must be true or false")
    try:
        vehicle = int(os.environ.get("VEHICLE_ACTION_TARGET_MINUTES", "15"))
        stock = int(os.environ.get("STOCK_ACTION_TARGET_MINUTES", "30"))
        radius = int(os.environ.get("DEFAULT_ALERT_RADIUS_M", "1000"))
        destination_radius = int(os.environ.get("DESTINATION_SEARCH_RADIUS_M", "20000"))
    except ValueError:
        raise ValueError("Action target minutes must be integers") from None
    return Settings(**values, demo_mode=demo == "true", vehicle_action_target_minutes=vehicle, stock_action_target_minutes=stock, default_alert_radius_m=radius, destination_search_radius_m=destination_radius)

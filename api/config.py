"""Explicit runtime settings; private values never appear in repr."""
from dataclasses import dataclass, field
from datetime import timedelta
import os
import math
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    web_base_url: str = "http://localhost:3000"
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
    demo_virtual_delivery: bool = False
    local_development: bool = False
    scheduler_local_auth: bool = False
    scheduler_audience: str = ""
    scheduler_caller_email: str = ""
    scheduler_caller_subject: str = ""
    pubsub_topic: str = "flood-events"
    bigquery_dataset: str = "highground"
    vehicle_action_target_minutes: int = 15
    stock_action_target_minutes: int = 30
    default_alert_radius_m: int = 1000
    destination_search_radius_m: int = 20000
    official_max_age_minutes: int = 90
    lorry_capacity_m3: float = 10.
    outcome_ask_after_h: float = 6.

    @property
    def official_max_age(self) -> timedelta:
        return timedelta(minutes=self.official_max_age_minutes)

    def __post_init__(self) -> None:
        if type(self.outcome_ask_after_h) not in (int,float) or not math.isfinite(self.outcome_ask_after_h) or not 0<self.outcome_ask_after_h<=720:raise ValueError('Outcome delay must be finite, positive and at most720 hours')
        if type(self.lorry_capacity_m3) not in (int,float) or not math.isfinite(self.lorry_capacity_m3) or self.lorry_capacity_m3<=0:raise ValueError('Lorry capacity must be finite and positive')
        if type(self.official_max_age_minutes) is not int or not 1 <= self.official_max_age_minutes <= 90:
            raise ValueError("Official maximum age must be an integer from 1 to 90 minutes")
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
    values = {name: os.environ.get(env_names.get(name, name.upper()), getattr(defaults, name)) for name in Settings.__dataclass_fields__ if name not in ("local_development", "scheduler_local_auth", "demo_mode", "demo_virtual_delivery", "vehicle_action_target_minutes", "stock_action_target_minutes", "default_alert_radius_m", "destination_search_radius_m", "official_max_age_minutes")}
    try:
        values['lorry_capacity_m3']=float(values['lorry_capacity_m3'])
        values['outcome_ask_after_h']=float(values['outcome_ask_after_h'])
    except (TypeError,ValueError):raise ValueError('Lorry capacity must be a number') from None
    flags = {}
    for name in ("local_development", "scheduler_local_auth", "demo_virtual_delivery"):
        value = os.environ.get(name.upper(), "false").lower()
        if value not in ("true", "false"):
            raise ValueError(name + " must be true or false")
        flags[name] = value == "true"
    demo = os.environ.get("DEMO_MODE", "false").lower()
    if demo not in ("true", "false"):
        raise ValueError("DEMO_MODE must be true or false")
    try:
        vehicle = int(os.environ.get("VEHICLE_ACTION_TARGET_MINUTES", "15"))
        stock = int(os.environ.get("STOCK_ACTION_TARGET_MINUTES", "30"))
        radius = int(os.environ.get("DEFAULT_ALERT_RADIUS_M", "1000"))
        official_age = int(os.environ.get("OFFICIAL_MAX_AGE_MINUTES", "90"))
        destination_radius = int(os.environ.get("DESTINATION_SEARCH_RADIUS_M", "20000"))
    except ValueError:
        raise ValueError("Action target minutes must be integers") from None
    return Settings(**values, **flags, demo_mode=demo == "true", vehicle_action_target_minutes=vehicle, stock_action_target_minutes=stock, default_alert_radius_m=radius, destination_search_radius_m=destination_radius, official_max_age_minutes=official_age)

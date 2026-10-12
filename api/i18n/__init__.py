"""Committed translations and deterministic Danger rendering only."""
import json
from typing import Any
from pathlib import Path
from string import Formatter
from urllib.parse import urlsplit, parse_qs
import math

LANGUAGES = ("en", "ms", "zh", "ta", "bn", "ne", "my", "id")
ROOT = Path(__file__).resolve().parent


def placeholders(value: str) -> set[str]:
    names = set()
    for _, name, format_spec, conversion in Formatter().parse(value):
        if name is not None:
            if not name.isidentifier() or format_spec or conversion:
                raise ValueError("Unsupported translation placeholder")
            names.add(name)
    return names


def validate_catalog(data: dict[str, Any], language: str, source: dict[str, Any]) -> None:
    if set(data) != set(source) or data.get("_language") != language or type(data.get("_reviewed")) is not bool:
        raise ValueError("Translation metadata/key mismatch")
    for key, value in data.items():
        if key.startswith("_"):
            continue
        if not isinstance(value, str) or not value.strip() or placeholders(value) != placeholders(source[key]):
            raise ValueError(f"Invalid translation key: {key}")
    for key in ("danger_destination", "danger_no_destination", "danger_sim_destination", "danger_sim_no_destination"):
        prefix = (data["simulation_label"] + "\n" if "_sim_" in key else "") + data["translation_notice"] + "\n"
        if data["_reviewed"] is False and not data[key].startswith(prefix):
            raise ValueError("Unreviewed Danger template lacks committed review notice")
        if not data[key].endswith(data["emergency_footer"]):
            raise ValueError("Danger emergency footer must remain last")
        if "_sim_" in key and not data[key].startswith(data["simulation_label"] + "\n"):
            raise ValueError("Simulated Danger template lacks committed label")


def catalog(language: str) -> dict[str, Any]:
    language = language if language in LANGUAGES else "en"
    source = json.loads((ROOT / "en.json").read_text())
    data = json.loads((ROOT / f"{language}.json").read_text())
    validate_catalog(data, language, source)
    return data


def text(language: str, key: str, **values: object) -> str:
    value = catalog(language)[key]
    if key.startswith("_") or not isinstance(value, str) or set(values) != placeholders(value):
        raise ValueError("Translation arguments mismatch")
    return value.format(**values)


def danger_text(language: str, *, is_demo: bool, safe_point_name: str | None = None, route_link: str | None = None) -> str:
    destination = safe_point_name is not None and route_link is not None
    if (safe_point_name is None) != (route_link is None):
        raise ValueError("Destination name and route link must be supplied together")
    if destination:
        if not safe_point_name.strip() or len(safe_point_name) > 160 or any(c in safe_point_name for c in "\n\r{}"):
            raise ValueError("Invalid destination name")
        url = urlsplit(route_link)
        query = parse_qs(url.query, strict_parsing=True)
        if url.scheme != "https" or url.netloc != "www.google.com" or url.path != "/maps/dir/" or url.fragment or set(query) != {"api", "destination"} or query["api"] != ["1"] or len(query["destination"]) != 1:
            raise ValueError("Invalid destination route")
        try:
            coordinates = [float(value) for value in query["destination"][0].split(",")]
            if len(coordinates) != 2 or not all(math.isfinite(value) for value in coordinates) or not -90 <= coordinates[0] <= 90 or not -180 <= coordinates[1] <= 180:
                raise ValueError("Invalid destination coordinates")
        except (TypeError, ValueError):
            raise ValueError("Invalid destination coordinates") from None

    key = "danger_" + ("sim_" if is_demo else "") + ("destination" if destination else "no_destination")
    return text(language, key, **({"safe_point_name": safe_point_name, "route_link": route_link} if destination else {}))

import json

import pytest

from api.config import Settings, load_settings
from api import i18n


def test_eight_catalogs_and_fixed_danger_variants():
    source = i18n.catalog("en")
    route = "https://www.google.com/maps/dir/?api=1&destination=3.028,101.725"
    for language in i18n.LANGUAGES:
        data = i18n.catalog(language)
        assert set(data) == set(source)
        assert data["_reviewed"] is (language == "en")
        for simulation in (False, True):
            for destination in (False, True):
                key = "danger_" + ("sim_" if simulation else "") + ("destination" if destination else "no_destination")
                values = {"safe_point_name": "Sourced location", "route_link": route} if destination else {}
                actual = i18n.danger_text(language, is_demo=simulation, **values)
                assert actual == data[key].format(**values)
                assert actual.endswith(data["emergency_footer"])
                assert i18n.placeholders(data[key]) == ({"safe_point_name", "route_link"} if destination else set())
                if language != "en":
                    assert data["translation_notice"] in actual
                if simulation:
                    assert actual.startswith(data["simulation_label"] + "\n")
    assert i18n.catalog("unsupported") == source


@pytest.mark.parametrize("route", ["https://www.google.com/url?q=https://example.com", "https://www.google.com/maps/dir/?api=1&destination=nan,1", "https://www.google.com/maps/dir/?api=1&destination=91,1", "https://www.google.com/maps/dir/?api=1&destination=1,181", "https://www.google.com:443/maps/dir/?api=1&destination=1,1", "https://www.google.com/maps/dir/?api=1&destination=1,1#extra", "https://www.google.com/maps/dir/?api=1&destination=1,1&extra=x"])
def test_danger_rejects_noncanonical_routes(route):
    with pytest.raises(ValueError):
        i18n.danger_text("en", is_demo=False, safe_point_name="Place", route_link=route)


def test_catalog_missing_and_malformed_fail_clearly(tmp_path, monkeypatch):
    (tmp_path / "en.json").write_text(json.dumps(i18n.catalog("en")))
    monkeypatch.setattr(i18n, "ROOT", tmp_path)
    with pytest.raises(FileNotFoundError):
        i18n.catalog("ms")
    (tmp_path / "ms.json").write_text("{}")
    with pytest.raises(ValueError):
        i18n.catalog("ms")


def test_configurable_targets_are_positive_ordered(monkeypatch):
    monkeypatch.setenv("VEHICLE_ACTION_TARGET_MINUTES", "10")
    monkeypatch.setenv("STOCK_ACTION_TARGET_MINUTES", "25")
    settings = load_settings()
    assert settings.vehicle_action_target_minutes == 10
    assert settings.stock_action_target_minutes == 25
    for vehicle, stock in [(0, 30), (30, 30), (31, 30), (-1, 30), (True, 30)]:
        with pytest.raises(ValueError):
            Settings(vehicle_action_target_minutes=vehicle, stock_action_target_minutes=stock)

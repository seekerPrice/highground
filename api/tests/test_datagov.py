import asyncio
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
import pytest
from pydantic import ValidationError

from api.models import Geography, Warning
from api.tools.datagov import (dedupe_warnings, fetch_warnings, parse_flood,
                               parse_weather, source_time, weather_record_id)

NOW = datetime(2026, 10, 13, 2, tzinfo=UTC)
FIXTURES = Path(__file__).parents[1] / 'fixtures'


def row(**changes):
    value = dict(station_id='station', latitude=3.0, longitude=101.0,
                 district='Klang', state='SELANGOR', water_level_current=2.0,
                 water_level_indicator='ALERT',
                 water_level_update_datetime=NOW.isoformat(),
                 station_status='ON', water_level_status='ON')
    value.update(changes)
    return value


def test_capture_never_becomes_current_alert():
    payload = json.loads((FIXTURES / 'flood_warning_sample.json').read_bytes())
    result = parse_flood(payload, now=NOW, naive_timezone=ZoneInfo('Asia/Kuala_Lumpur'))
    assert result.records_received == 1276
    assert not result.warnings and result.records_current == 0
    assert result.rejected['stale'] > 0
    assert sum(result.rejected.values()) == len(payload)


def test_timezone_requires_evidence_and_boundary():
    assert source_time('2026-10-13 10:00:00', ZoneInfo('Asia/Kuala_Lumpur')) == NOW
    result = parse_flood([row(water_level_update_datetime='2026-10-13 10:00:00')], now=NOW)
    assert result.rejected == {'unverified_timezone': 1}
    assert len(parse_flood([row(water_level_update_datetime=(NOW-timedelta(minutes=90)).isoformat())], now=NOW).warnings) == 1
    assert not parse_flood([row(water_level_update_datetime=(NOW-timedelta(minutes=90, seconds=1)).isoformat())], now=NOW).warnings


@pytest.mark.parametrize('change,reason', [
    ({'water_level_update_datetime': None}, 'missing_timestamp'),
    ({'water_level_update_datetime': 'garbage'}, 'invalid_timestamp'),
    ({'water_level_update_datetime': (NOW+timedelta(seconds=1)).isoformat()}, 'future'),
    ({'water_level_indicator': 'ERROR'}, 'device_error'),
    ({'water_level_status': 'OFF'}, 'device_error'),
    ({'station_status': 'OFF'}, 'device_error'),
    ({'latitude': float('nan')}, 'invalid_record'),
    ({'longitude': 181.0}, 'invalid_record'),
    ({'latitude': True}, 'invalid_record'),
    ({'water_level_current': float('inf')}, 'invalid_record'),
    ({'water_level_indicator': 'ON'}, 'invalid_record'),
])
def test_reject(change, reason):
    result = parse_flood([row(**change)], now=NOW)
    assert result.rejected == {reason: 1}
    assert not result.warnings


def test_indicator_not_thresholds_or_device_status():
    result = parse_flood([row(water_level_indicator='DANGER', water_level_danger_level=99,
                             water_level_warning_level=120)], now=NOW)
    assert result.warnings[0].level == 'danger'
    normal = parse_flood([row(water_level_indicator='NORMAL')], now=NOW)
    assert normal.status == 'current' and not normal.warnings
    assert normal.resolved == {'jps:station': NOW}
    assert parse_flood([], now=NOW).status == 'empty'
    assert parse_flood({}, now=NOW).status == 'unavailable'


def test_duplicates_and_mixed_source_health():
    result = parse_flood([row(), row(), row(latitude=999.0)], now=NOW)
    assert result.status == 'degraded' and len(result.warnings) == 1


def test_weather_marine_and_unmapped_district_never_alert():
    payload = json.loads((FIXTURES / 'weather_warning_sample.json').read_bytes())
    for tz in (None, ZoneInfo('Asia/Kuala_Lumpur')):
        result = parse_weather(payload, now=NOW, naive_timezone=tz)
        assert not result.warnings
        assert result.records_current == 0 and sum(result.rejected.values()) == len(payload)
    synthetic = [{'warning_issue': {'issued': NOW.isoformat(), 'title_en': 'Thunderstorms Warning'},
                  'valid_from': NOW.isoformat(), 'valid_to': (NOW+timedelta(hours=1)).isoformat(),
                  'text_en': 'Heavy rain in Klang'}]
    assert parse_weather(synthetic, now=NOW).status == 'unsupported'
    synthetic[0]['valid_to'] = (NOW-timedelta(hours=1)).isoformat()
    assert parse_weather(synthetic, now=NOW).rejected == {'invalid_validity': 1}
    assert parse_weather([None], now=NOW).rejected == {'invalid_record': 1}
    assert parse_weather({}, now=NOW).status == 'unavailable'


def warning(level='warning', at=NOW):
    return Warning(source='jps', source_id='station', level=level, observed_at=at,
                   geography=Geography(latitude=3, longitude=101), reason='JPS indicator')


def test_dedupe_escalation_retries_and_later_episode():
    events, state = dedupe_warnings((warning(),), {})
    assert len(events) == 1
    retry, _ = dedupe_warnings((warning(),), {})
    assert retry[0].event_id == events[0].event_id
    assert not dedupe_warnings((warning(at=NOW+timedelta(minutes=5)),), state)[0]
    escalated, state = dedupe_warnings((warning('danger', NOW+timedelta(minutes=10)),), state)
    assert len(escalated) == 1 and escalated[0].event_id != events[0].event_id
    assert not dedupe_warnings((warning(at=NOW),), state)[0]
    later, _ = dedupe_warnings((warning(at=NOW+timedelta(hours=2)),), state)
    assert len(later) == 1 and later[0].event_id != events[0].event_id
    resolved, state = dedupe_warnings((), state, resolved={'jps:station': NOW+timedelta(minutes=11)})
    assert not resolved and state['jps:station'].resolved_at == NOW+timedelta(minutes=11)
    assert len(dedupe_warnings((warning(at=NOW+timedelta(minutes=12)),), state)[0]) == 1


def test_old_recovery_cannot_clear_newer_episode():
    _, state = dedupe_warnings((warning(),), {})
    _, recovered = dedupe_warnings((), state, resolved={'jps:station': NOW-timedelta(seconds=1)})
    assert recovered == state


@pytest.mark.parametrize('failure', ['network', 'http', 'json', 'shape'])
def test_client_failure_isolated(failure):
    def handle(request):
        if request.url.path.endswith('flood-warning'):
            if failure == 'network':
                raise httpx.ConnectError('not reachable', request=request)
            if failure == 'http':
                return httpx.Response(503)
            if failure == 'json':
                return httpx.Response(200, content=b'not json')
            return httpx.Response(200, json={'results': []})
        return httpx.Response(200, json=[])
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle), timeout=2) as client:
            return await fetch_warnings(client=client, clock=lambda: NOW)
    flood, weather = asyncio.run(run())
    assert flood.status == 'unavailable' and weather.status == 'empty'


def test_client_success_and_full_unfiltered_endpoints():
    paths = []
    def handle(request):
        paths.append(str(request.url))
        return httpx.Response(200, json=[row()] if 'flood' in request.url.path else [])
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            return await fetch_warnings(client=client, clock=lambda: NOW)
    assert asyncio.run(run())[0].warnings[0].level == 'watch'
    assert paths == ['https://api.data.gov.my/flood-warning', 'https://api.data.gov.my/weather/warning']


def test_common_model_rejects_invented_or_malformed_geography():
    with pytest.raises(ValidationError):
        Geography(latitude=3)
    with pytest.raises(ValidationError):
        Geography()
    with pytest.raises(ValidationError):
        Warning(source='jps', source_id='station', level='danger', observed_at=datetime(2026, 10, 13),
                geography=Geography(latitude=3, longitude=101), reason='bad time')


def test_mapped_current_land_and_marine_exclusion():
    land = {'warning_issue': {'issued': NOW.isoformat(), 'title_en': 'Thunderstorms Warning'},
            'valid_from': NOW.isoformat(), 'valid_to': (NOW+timedelta(hours=1)).isoformat(),
            'text_en': 'Thunderstorms, heavy rain and strong winds in Selangor (Klang)'}
    geo = Geography(district='Klang', state='Selangor')
    mapping = {weather_record_id(land): (geo,)}
    result = parse_weather([land], now=NOW, verified_geographies=mapping)
    assert result.status == 'current' and result.warnings[0].level == 'watch'
    assert result.warnings[0].geography == geo
    assert result.warnings[0].valid_until == NOW+timedelta(hours=1)
    marine = dict(land, text_en='Heavy rain over the waters of Selangor')
    assert not parse_weather([marine], now=NOW,
                             verified_geographies={weather_record_id(marine): (geo,)}).warnings
    changed = dict(land, text_en='Heavy rain in another district')
    assert parse_weather([changed], now=NOW, verified_geographies=mapping).status == 'unsupported'
    assert parse_weather([land], now=NOW+timedelta(hours=1), verified_geographies=mapping).status == 'stale'


@pytest.mark.parametrize('indicator,level', [('ALERT','watch'), ('WARNING','warning'), ('DANGER','danger')])
def test_jps_distinct_official_severities(indicator, level):
    parsed = parse_flood([row(water_level_indicator=indicator)], now=NOW)
    assert parsed.warnings[0].level == level
    assert parsed.warnings[0].source_indicator == indicator


def test_date_only_is_not_a_reading_time():
    result = parse_flood([row(water_level_update_datetime='2026-10-13')], now=NOW,
                         naive_timezone=ZoneInfo('Asia/Kuala_Lumpur'))
    assert result.rejected == {'invalid_timestamp': 1}


def test_recovery_does_not_reemit_older_warning_in_same_batch():
    _, state = dedupe_warnings((warning(),), {})
    events, state = dedupe_warnings((warning(),), state,
                                   resolved={'jps:station': NOW+timedelta(seconds=1)})
    assert not events and state['jps:station'].resolved_at == NOW+timedelta(seconds=1)


def test_recovery_watermark_survives_later_out_of_order_poll():
    _, state = dedupe_warnings((warning(),), {})
    events, state = dedupe_warnings((warning(at=NOW+timedelta(minutes=5)),), state,
                                   resolved={'jps:station': NOW+timedelta(minutes=10)})
    assert not events
    events, state = dedupe_warnings((warning(at=NOW+timedelta(minutes=5)),), state)
    assert not events
    events, state = dedupe_warnings((warning(at=NOW+timedelta(minutes=11)),), state)
    assert len(events) == 1 and state['jps:station'].resolved_at is None


def test_parser_to_dedupe_warning_recovery_new_warning():
    first = parse_flood([row(water_level_indicator='WARNING')], now=NOW)
    emitted, state = dedupe_warnings(first.warnings, {}, resolved=first.resolved)
    assert len(emitted) == 1
    normal_time = NOW+timedelta(minutes=10)
    normal = parse_flood([row(water_level_indicator='NORMAL',
                             water_level_update_datetime=normal_time.isoformat())], now=normal_time)
    emitted, state = dedupe_warnings(normal.warnings, state, resolved=normal.resolved)
    assert not emitted and state['jps:station'].resolved_at == normal_time
    new_time = NOW+timedelta(minutes=11)
    later = parse_flood([row(water_level_indicator='WARNING',
                            water_level_update_datetime=new_time.isoformat())], now=new_time)
    emitted, state = dedupe_warnings(later.warnings, state, resolved=later.resolved)
    assert len(emitted) == 1 and state['jps:station'].started_at == new_time

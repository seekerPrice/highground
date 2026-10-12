"""Fail-closed adapters for data.gov.my. No network/model work in parsing.

Naive timestamps require a verified source timezone supplied by the caller.
Weather currently has no documented structured district field: it is reported as
unsupported rather than guessed from prose. Dedupe is a pure state transition;
Task 7 must persist its state atomically with event creation, across pollers.
"""
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, tzinfo
from hashlib import sha256
import json
import re
from typing import Callable, Literal, Mapping

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from api.models import Geography, Source, SourceResult, Warning

FLOOD_URL = 'https://api.data.gov.my/flood-warning'
WEATHER_URL = 'https://api.data.gov.my/weather/warning'
DEFAULT_MAX_AGE = timedelta(minutes=90)


class FloodRow(BaseModel):
    model_config = ConfigDict(extra='ignore', strict=True, allow_inf_nan=False)
    station_id: str = Field(min_length=1)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    district: str = Field(min_length=1)
    state: str = Field(min_length=1)
    water_level_current: float
    water_level_indicator: Literal['NORMAL', 'ALERT', 'WARNING', 'DANGER', 'ERROR']
    water_level_update_datetime: str | None
    station_status: Literal['ON', 'OFF']
    water_level_status: Literal['ON', 'OFF']


class TimestampError(ValueError):
    pass


def source_time(value: str | None, naive_timezone: tzinfo | None) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise TimestampError('missing_timestamp')
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?', value):
        raise TimestampError('invalid_timestamp')
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise TimestampError('invalid_timestamp') from error
    if parsed.tzinfo is None:
        if naive_timezone is None:
            raise TimestampError('unverified_timezone')
        parsed = parsed.replace(tzinfo=naive_timezone)
    return parsed.astimezone(UTC)


def _check_config(now: datetime, max_age: timedelta) -> None:
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError('observation clock must be timezone aware')
    if max_age <= timedelta(0):
        raise ValueError('max_age must be positive')


def _result(source: Source, now: datetime, size: int, current: int,
            rejected: Counter[str], warnings: list[Warning]) -> SourceResult:
    if not size:
        status = 'empty'
    elif current:
        status = 'degraded' if rejected else 'current'
    elif rejected.get('stale') == size:
        status = 'stale'
    elif rejected.get('unsupported') == size:
        status = 'unsupported'
    else:
        status = 'degraded'
    return SourceResult(source=source, status=status, checked_at=now,
                        records_received=size, records_current=current,
                        rejected=dict(rejected), warnings=tuple(warnings))


def parse_flood(payload: object, *, now: datetime,
                max_age: timedelta = DEFAULT_MAX_AGE,
                naive_timezone: tzinfo | None = None) -> SourceResult:
    _check_config(now, max_age)
    if not isinstance(payload, list):
        return SourceResult(source='jps', status='unavailable', checked_at=now,
                            detail='invalid_response_shape')
    rejected: Counter[str] = Counter()
    warnings: list[Warning] = []
    current = 0
    resolved: dict[str, datetime] = {}
    for raw in payload:
        try:
            row = FloodRow.model_validate(raw)
        except ValidationError:
            rejected['invalid_record'] += 1
            continue
        if (row.water_level_indicator == 'ERROR' or row.station_status != 'ON'
                or row.water_level_status != 'ON'):
            rejected['device_error'] += 1
            continue
        try:
            observed = source_time(row.water_level_update_datetime, naive_timezone)
        except TimestampError as error:
            rejected[str(error)] += 1
            continue
        if observed > now:
            rejected['future'] += 1
            continue
        if now - observed > max_age:
            rejected['stale'] += 1
            continue
        current += 1
        level = {'ALERT': 'watch', 'WARNING': 'warning', 'DANGER': 'danger'}.get(
            row.water_level_indicator)
        if not level:
            recovery_key = f'jps:{row.station_id}'
            resolved[recovery_key] = max(observed, resolved.get(recovery_key, observed))
        if level:
            warnings.append(Warning(
                source='jps', source_id=row.station_id, level=level,
                observed_at=observed,
                geography=Geography(latitude=row.latitude, longitude=row.longitude,
                                    district=row.district, state=row.state),
                reason=f'JPS water-level indicator: {row.water_level_indicator}',
                source_indicator=row.water_level_indicator,
            ))
    # Duplicate station rows cannot generate duplicate events in one response.
    unique = {(w.source_id, w.level, w.observed_at): w for w in warnings}
    result = _result('jps', now, len(payload), current, rejected, list(unique.values()))
    return result.model_copy(update={'resolved': resolved})


def weather_record_id(row: Mapping[str, object]) -> str:
    """Stable exact-record identity for a reviewed attribution, not authenticity."""
    canonical = json.dumps(dict(row), sort_keys=True, separators=(',', ':'), allow_nan=False)
    return sha256(canonical.encode()).hexdigest()


def parse_weather(payload: object, *, now: datetime,
                  naive_timezone: tzinfo | None = None,
                  verified_geographies: Mapping[str, tuple[Geography, ...]] | None = None,
                  ) -> SourceResult:
    """Only reviewed exact-record district attribution can produce a Watch.

    Caller must verify attribution against the official warning. No shipped
    mapping exists. Exact fingerprint prevents applying an old attribution to
    changed text. Marine/unknown types stay excluded even if supplied a mapping.
    """
    _check_config(now, DEFAULT_MAX_AGE)
    if not isinstance(payload, list):
        return SourceResult(source='met', status='unavailable', checked_at=now,
                            detail='invalid_response_shape')
    rejected: Counter[str] = Counter()
    warnings: list[Warning] = []
    current = 0
    for row in payload:
        if not isinstance(row, dict) or not isinstance(row.get('warning_issue'), dict):
            rejected['invalid_record'] += 1
            continue
        issue = row['warning_issue']
        if not all(isinstance(issue.get(k), str) for k in ('issued', 'title_en')):
            rejected['invalid_record'] += 1
            continue
        # This title/type is observed in the captured official land warning.
        # Do not infer a land warning from heavy-rain words in marine prose.
        if (issue['title_en'] != 'Thunderstorms Warning'
                or not isinstance(row.get('text_en'), str)
                or 'heavy rain' not in row['text_en'].lower()
                or any(term in row['text_en'].lower()
                       for term in ('waters', 'shipping', 'rough seas', 'nautical'))):
            rejected['unsupported'] += 1
            continue
        try:
            issued = source_time(issue['issued'], naive_timezone)
            start = source_time(row.get('valid_from'), naive_timezone)
            end = source_time(row.get('valid_to'), naive_timezone)
        except TimestampError as error:
            rejected[str(error)] += 1
            continue
        if issued > now or start > now:
            rejected['future'] += 1
            continue
        if end < start or end < issued:
            rejected['invalid_validity'] += 1
            continue
        if now >= end:
            rejected['stale'] += 1
            continue
        try:
            identity = weather_record_id(row)
        except (ValueError, TypeError):
            rejected['invalid_record'] += 1
            continue
        geographies = (verified_geographies or {}).get(identity, ())
        if not geographies or any(not (geo.district and geo.state) for geo in geographies):
            rejected['unsupported'] += 1
            continue
        current += 1
        for geo in geographies:
            warnings.append(Warning(
                source='met', source_id=f'{identity}:{geo.state}:{geo.district}',
                level='watch', observed_at=issued, valid_until=end, geography=geo,
                reason='MET land thunderstorm warning includes heavy rain; reviewed district attribution',
                source_indicator=issue['title_en'],
            ))
    unique = {w.source_id: w for w in warnings}
    return _result('met', now, len(payload), current, rejected, list(unique.values()))


async def fetch_warnings(*, client: httpx.AsyncClient,
                         clock: Callable[[], datetime] = lambda: datetime.now(UTC),
                         max_age: timedelta = DEFAULT_MAX_AGE,
                         naive_timezone: tzinfo | None = None,
                         verified_geographies: Mapping[str, tuple[Geography, ...]] | None = None,
                         ) -> tuple[SourceResult, SourceResult]:
    """One complete unfiltered list per endpoint; no undocumented pagination.

    Caller owns the client's timeout/transport and lifetime. Independent failures
    remain separate. No retries here: scheduled polling supplies the next attempt.
    """
    results: list[SourceResult] = []
    for source, url in [('jps', FLOOD_URL), ('met', WEATHER_URL)]:
        now = clock()
        _check_config(now, max_age)
        try:
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPError:
            results.append(SourceResult(source=source, status='unavailable',
                                        checked_at=now, detail='http_or_network_error'))
            continue
        except ValueError:
            results.append(SourceResult(source=source, status='unavailable',
                                        checked_at=now, detail='invalid_json'))
            continue
        if source == 'jps':
            results.append(parse_flood(payload, now=now, max_age=max_age,
                                       naive_timezone=naive_timezone))
        else:
            results.append(parse_weather(payload, now=now, naive_timezone=naive_timezone,
                                         verified_geographies=verified_geographies))
    return results[0], results[1]


@dataclass(frozen=True)
class EpisodeState:
    started_at: datetime
    last_observed_at: datetime
    highest_level: Literal['watch', 'warning', 'danger'] | None
    resolved_at: datetime | None = None


@dataclass(frozen=True)
class NewWarning:
    warning: Warning
    event_id: str


def dedupe_warnings(warnings: tuple[Warning, ...],
                    previous: Mapping[str, EpisodeState], *,
                    episode_gap: timedelta = DEFAULT_MAX_AGE,
                    resolved: Mapping[str, datetime] | None = None,
                    ) -> tuple[tuple[NewWarning, ...], dict[str, EpisodeState]]:
    """Emit first/escalated warning, or a new episode after a data-time gap.

    Pure transition: no implicit in-memory persistence. Stale/failed/empty polls
    must not clear previous states. Source time, never polling time, closes a gap.
    Event identity is stable across retries and advances with episode + severity.
    """
    if episode_gap <= timedelta(0):
        raise ValueError('episode_gap must be positive')
    state = dict(previous)
    for key, observed in (resolved or {}).items():
        if observed.tzinfo is None or observed.utcoffset() is None:
            raise ValueError("recovery timestamps must be timezone aware")
        old = state.get(key)
        if old is None or observed >= old.last_observed_at:
            state[key] = EpisodeState(observed, observed, None, observed)
    emitted: list[NewWarning] = []
    ranks = {'watch': 0, 'warning': 1, 'danger': 2}
    for warning in sorted(warnings, key=lambda w: (w.observed_at, ranks[w.level])):
        key = f'{warning.source}:{warning.source_id}'
        if (resolved or {}).get(key) is not None and resolved[key] >= warning.observed_at:
            continue
        old = state.get(key)
        if old and old.resolved_at is not None and warning.observed_at <= old.resolved_at:
            continue
        if old and warning.observed_at < old.last_observed_at:
            continue
        is_new = (old is None or old.highest_level is None
                  or warning.observed_at - old.last_observed_at > episode_gap)
        escalates = (old is not None and old.highest_level is not None
                     and ranks[warning.level] > ranks[old.highest_level])
        started = warning.observed_at if is_new else old.started_at
        highest = warning.level if is_new or escalates else old.highest_level
        state[key] = EpisodeState(started, warning.observed_at, highest)
        if is_new or escalates:
            identity = f'{key}|{started.isoformat()}|{warning.level}'
            emitted.append(NewWarning(warning, sha256(identity.encode()).hexdigest()))
    return tuple(emitted), state

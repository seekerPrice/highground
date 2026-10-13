from datetime import UTC,datetime,timedelta
from math import degrees
import pytest
from pydantic import ValidationError
from api.models import SourceResult,Warning,Geography
from api.public_check_models import CheckLocation,PrivateCheckReport
from api.public_check import project_check
NOW=datetime(2026,10,13,12,tzinfo=UTC)
LOCATION=CheckLocation(lat=0.,lng=0.)

def warning(distance=1000.,**changes):
    return Warning(**(dict(source='jps',source_id='PRIVATE-STATION',level='warning',observed_at=NOW-timedelta(minutes=1),geography=Geography(latitude=degrees(distance/6371008.8),longitude=0.),reason='PRIVATE SOURCE REASON')|changes))
def source(*warnings,**changes):return SourceResult(**(dict(source='jps',status='current',checked_at=NOW,warnings=warnings)|changes))
def report(**changes):return PrivateCheckReport(**(dict(report_id='a'*32,shop_id='PRIVATE-SHOP',sha256='c'*64,lat=0.,lng=0.,received_at=NOW-timedelta(minutes=1),telegram_date=NOW-timedelta(minutes=2),confirmed_at=NOW-timedelta(seconds=30),location_attribution='confirmed_shop',evidence_status='positive',level='danger',is_demo=False)|changes))


def test_exact_two_km_filter_precedes_public_rounding_and_private_fields_are_absent():
    result=project_check(LOCATION,(source(warning(1999.9),warning(2000.1,source_id='outside')),),(report(),report()),(),now=NOW)
    assert len(result.observations)==2
    assert sorted(o.rounded_distance_m for o in result.observations)==[0,2000]
    assert result.level=='danger'
    payload=result.model_dump_json()
    for private in ('PRIVATE-SHOP','PRIVATE-STATION','PRIVATE SOURCE REASON','report_id','shop_id','latitude','longitude','media_id'):
        assert private not in payload
    assert 'no flood' in result.qualification and 'capture time' in result.qualification
    with pytest.raises(ValidationError):CheckLocation(lat=float('nan'),lng=0.)


def test_current_cached_source_rejects_stale_future_and_normal_watermarks_without_fresh_coverage_claim():
    stale=source(warning(observed_at=NOW-timedelta(minutes=31)))
    result=project_check(LOCATION,(stale,),(),(),now=NOW,official_max_age=timedelta(minutes=30))
    assert not result.observations and next(s for s in result.sources if s.source=='jps').status=='degraded'
    for invalid in (source(warning(observed_at=NOW+timedelta(seconds=1))),source(warning(),status='unavailable')):
        assert not project_check(LOCATION,(invalid,),(),(),now=NOW).observations
    resolved=source(warning(),resolved={'jps:PRIVATE-STATION':NOW})
    assert not project_check(LOCATION,(resolved,),(),(),now=NOW).observations


def test_identical_private_upload_hash_is_one_report_without_hash_or_location_disclosure():
    reports=(report(),report(report_id='b'*32,shop_id='OTHER-SHOP'))
    result=project_check(LOCATION,(),reports,(),now=NOW)
    assert len(result.observations)==1
    assert 'sha256' not in result.model_dump_json()


def test_public_listing_requires_checked_source_and_nonfictional_eligible_point():
    import json
    from pathlib import Path
    from api.destinations import SafePoint
    point=SafePoint.model_validate(json.loads(Path('infra/data/safe_points.json').read_text())[0])
    for patch in ({'verified':False},{'is_demo':True},{'opening_status':'closed'}):
        with pytest.raises(ValueError):project_check(LOCATION,(),(),(point.model_copy(update=patch),),now=NOW)


def test_district_geometry_is_separate_and_report_confirmation_cannot_refresh_age():
    district=warning(source='met',level='watch',geography=Geography(district='Klang',state='Selangor'))
    met=SourceResult(source='met',status='current',checked_at=NOW,warnings=(district,))
    result=project_check(LOCATION,(met,),(),(),now=NOW)
    assert not result.observations and result.level is None
    assert result.status=='partial' and result.district_warnings[0].scope=='district_only'
    invalid=(report(is_demo=True),report(evidence_status='rejected'),report(confirmed_at=None),report(location_attribution='unconfirmed_shop'),report(received_at=NOW-timedelta(minutes=31),confirmed_at=NOW),report(telegram_date=NOW-timedelta(minutes=31),confirmed_at=NOW),report(telegram_date=NOW+timedelta(seconds=1)))
    for candidate in invalid:
        assert not project_check(LOCATION,(),(candidate,),(),now=NOW).observations
    unknown=project_check(LOCATION,(),(report(level=None,evidence_status='unverified'),),(),now=NOW)
    assert unknown.observations[0].level is None and unknown.level is None
    assert project_check(LOCATION,(),(),(),now=NOW,report_source_available=False).status=='unavailable'


def test_report_duplicate_cannot_refresh_receipt_or_claim_conflicting_locations():
    original=report(received_at=NOW-timedelta(minutes=31),telegram_date=NOW-timedelta(minutes=32),confirmed_at=NOW-timedelta(minutes=30))
    assert not project_check(LOCATION,(),(original,report(report_id='b'*32)),(),now=NOW).observations
    disputed=project_check(LOCATION,(),(report(),report(report_id='b'*32,lat=.01)),(),now=NOW)
    assert not disputed.observations and next(s for s in disputed.sources if s.source=='shop_report').status=='degraded'

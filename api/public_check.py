"""Read-only nearby projection. Submitted coordinates stay transient."""
from datetime import datetime,timedelta
from api.models import SourceResult
from api.destinations import SafePoint
from api.public_check_models import CheckLocation,PrivateCheckReport,CheckResult,CheckObservation,DistrictCheckWarning,CheckSource
from api.tools.datagov import DEFAULT_MAX_AGE
from api.tools.geo import distance_m

LEVELS={'watch':1,'warning':2,'danger':3}


def project_check(location:CheckLocation,official:tuple[SourceResult,...],reports:tuple[PrivateCheckReport,...],destinations:tuple[SafePoint,...],*,now:datetime,official_max_age:timedelta=DEFAULT_MAX_AGE,report_source_available:bool=True)->CheckResult:
    if now.tzinfo is None or now.utcoffset() is None:raise ValueError('Lookup clock must be aware')
    if not timedelta(0)<official_max_age<=DEFAULT_MAX_AGE:raise ValueError('Official freshness must be positive and at most90 minutes')
    if type(report_source_available) is not bool:raise ValueError('Report availability must be explicit')
    if len(official)>2 or len({result.source for result in official})!=len(official):raise ValueError('Official sources must be unique and bounded')
    if len(destinations)>3:raise ValueError('Destination lookup exceeds bound')
    observations=[];district=[];statuses={name:'unavailable' for name in ('jps','met')}
    def fresh(at,age):return at<=now and now-at<=age
    def mapped(source,at,level,lat,lng,attribution):
        meters=distance_m(location.lat,location.lng,lat,lng)
        if meters<=2000:
            observations.append(CheckObservation(source=source,reported_at=at,level=level,rounded_distance_m=int(meters/100+.5)*100,attribution=attribution))
    for result in official:
        if not fresh(result.checked_at,official_max_age) or len(result.warnings)>1000:continue
        statuses[result.source]=result.status
        if result.status not in ('current','degraded'):continue
        latest={}
        for warning in result.warnings:
            if warning.source!=result.source:statuses[result.source]='unavailable';latest={};break
            previous=latest.get(warning.source_id)
            if previous is None or (warning.observed_at,LEVELS[warning.level])>(previous.observed_at,LEVELS[previous.level]):latest[warning.source_id]=warning
        for warning in latest.values():
            if not fresh(warning.observed_at,official_max_age) or (warning.valid_until is not None and now>=warning.valid_until):
                statuses[result.source]='degraded';continue
            resolved=result.resolved.get(f'{warning.source}:{warning.source_id}')
            if resolved is not None and resolved>=warning.observed_at and fresh(resolved,official_max_age):continue
            geo=warning.geography
            if geo.latitude is None:
                if warning.source=='met':district.append(DistrictCheckWarning(source='met',reported_at=warning.observed_at,level=warning.level,district=geo.district,state=geo.state))
                else:statuses[result.source]='degraded'
            else:mapped(warning.source,warning.observed_at,warning.level,geo.latitude,geo.longitude,'official_observation')
    unique={};conflict=False
    if len(reports)>1000:report_source_available=False
    if report_source_available:
        for report in reports:
            if report.report_id in unique and unique[report.report_id]!=report:conflict=True;break
            unique[report.report_id]=report
    if conflict:report_source_available=False
    statuses['shop_report']='empty' if report_source_available else 'unavailable'
    if report_source_available:
        hashes={}
        for report in sorted(unique.values(),key=lambda row:(row.received_at,row.report_id)):
            if report.is_demo or report.evidence_status=='rejected':continue
            hashes.setdefault(report.sha256,[]).append(report)
        for copies in hashes.values():
            if len({(copy.lat,copy.lng) for copy in copies})>1:
                statuses['shop_report']='degraded';continue
            report=copies[0] # Original known receipt wins; a duplicate does not refresh its age.
            if report.is_demo or report.evidence_status=='rejected' or report.confirmed_at is None or report.location_attribution=='unconfirmed_shop':continue
            if not fresh(report.received_at,timedelta(minutes=30)) or not fresh(report.telegram_date,timedelta(minutes=30)) or report.confirmed_at>now or report.confirmed_at<report.received_at:continue
            if statuses['shop_report']!='degraded':statuses['shop_report']='current'
            mapped('shop_report',report.telegram_date,report.level,report.lat,report.lng,'reporter_confirmed_location')
    if len(observations)>100 or len(district)>100:
        observations=[];district=[];statuses={key:'unavailable' for key in statuses}
    sources=tuple(CheckSource(source=name,status=status) for name,status in statuses.items())
    incomplete=any(status not in ('current','empty') for status in statuses.values()) or bool(district)
    status='unavailable' if all(value=='unavailable' for value in statuses.values()) else 'partial' if incomplete else 'available'
    known=[row.level for row in observations if row.level is not None]
    level=max(known,key=LEVELS.get) if known else None
    return CheckResult(checked_at=now,status=status,level=level,observations=tuple(sorted(observations,key=lambda row:(row.reported_at,row.source,row.rounded_distance_m),reverse=True)),district_warnings=tuple(district),destinations=destinations,sources=sources)


def fixed_check_danger(result:CheckResult,language:str):
    """Danger never enters a generated summary or property flow."""
    if result.level!='danger':return None
    from api.alert_composer import render_danger
    destination=next((point.destination() for point in result.destinations if point.type in ('pps','high_ground')),None)
    return render_danger(language,False,destination)


def location_routing(intent_status:str,*,registered_flow_waiting:bool)->str:
    """An active registration/media context takes priority over public lookup."""
    if type(registered_flow_waiting) is not bool:raise ValueError('Location routing requires explicit flow state')
    return 'public_check' if intent_status=='waiting_location' and not registered_flow_waiting else 'existing_flow'


class PublicCheckReader:
    """Read-only adapters; no registration, risk writes or submitted-location storage."""
    def __init__(self,client,*,official_max_age=DEFAULT_MAX_AGE,destination_radius_m=20000,reports='photo_reports',destinations='safe_points',transport=None,clock=None,owned_client=False):
        from datetime import UTC
        if not timedelta(0)<official_max_age<=DEFAULT_MAX_AGE:raise ValueError('Invalid official cutoff')
        if type(destination_radius_m) is not int or not 1<=destination_radius_m<=100000:raise ValueError('Invalid destination scope')
        self.client,self.official_max_age,self.destination_radius_m=client,official_max_age,destination_radius_m
        self.reports,self.destinations,self.transport=reports,destinations,transport
        self.clock=clock or (lambda:datetime.now(UTC));self.owned_client=owned_client
    def _reports(self,now):
        from google.cloud.firestore_v1.base_query import FieldFilter
        from pydantic import ValidationError
        # Preserve earliest known byte-hash provenance before applying the30-minute window.
        # More than1000 real rows is unavailable, never an incomplete first-seen claim.
        query=self.client.collection(self.reports).where(filter=FieldFilter('is_demo','==',False)).limit(1001)
        rows=list(query.stream(timeout=5,retry=None))
        if len(rows)>1000:return (),False
        reports=[]
        for snapshot in rows:
            value=snapshot.to_dict()
            if not value or value.get('is_demo') is not False or value.get('evidence_status') not in ('positive','unverified') or value.get('confirmed_at') is None:continue
            try:
                reports.append(PrivateCheckReport(report_id=snapshot.id,shop_id=value['shop_id'],sha256=value['sha256'],lat=value['lat'],lng=value['lng'],received_at=value['received_at'],telegram_date=value['telegram_date'],confirmed_at=value['confirmed_at'],location_attribution=value['location_attribution'],evidence_status=value['evidence_status'],level=value.get('level') or (value.get('triage') or {}).get('level'),is_demo=False))
            except (KeyError,ValidationError,TypeError):return (),False
        return tuple(reports),True
    def _destinations(self,location):
        from pydantic import ValidationError
        rows=list(self.client.collection(self.destinations).limit(1001).stream(timeout=5,retry=None))
        if len(rows)>1000:return (),False
        candidates=[]
        for snapshot in rows:
            try:point=SafePoint.model_validate(dict(snapshot.to_dict() or {},safe_point_id=snapshot.id))
            except (ValidationError,TypeError):return (),False
            if not point.verified or point.is_demo or point.opening_status=='closed':continue
            meters=distance_m(location.lat,location.lng,point.lat,point.lng)
            if meters<=self.destination_radius_m:candidates.append((meters,point.safe_point_id,point))
        selected={}
        for _,_,point in sorted(candidates,key=lambda row:(row[0],row[1])):selected.setdefault(point.type,point)
        return tuple(selected.values()),True
    async def read(self,location:CheckLocation)->CheckResult:
        import asyncio
        import httpx
        from api.tools.datagov import fetch_warnings
        class BoundedClient(httpx.AsyncClient):
            async def get(self,url,**kwargs):
                async with self.stream('GET',url,**kwargs) as response:
                    data=bytearray()
                    async for chunk in response.aiter_bytes(chunk_size=65536):
                        data.extend(chunk)
                        if len(data)>5_000_000:raise httpx.HTTPError('Official response exceeds bound')
                    headers={key:value for key,value in response.headers.items() if key.lower() not in ('content-encoding','content-length')}
                    return httpx.Response(response.status_code,headers=headers,content=bytes(data),request=response.request)
        async def official():
            try:
                async with asyncio.timeout(12),BoundedClient(transport=self.transport,timeout=5) as http:
                    return await fetch_warnings(client=http,clock=self.clock,max_age=self.official_max_age)
            except Exception:
                return tuple(SourceResult(source=name,status='unavailable',checked_at=self.clock()) for name in ('jps','met'))
        async def reports():
            try:return await asyncio.to_thread(self._reports,self.clock())
            except Exception:return (),False
        async def destinations():
            try:return await asyncio.to_thread(self._destinations,location)
            except Exception:return (),False
        sources,(private,available),(places,places_available)=await asyncio.gather(official(),reports(),destinations())
        result=project_check(location,sources,private,places,now=self.clock(),official_max_age=self.official_max_age,report_source_available=available)
        return result.model_copy(update={'destination_status':'available' if places_available else 'unavailable','status':'partial' if not places_available and result.status=='available' else result.status})
    def close(self):
        if self.owned_client:self.client.close()


def create_public_check_reader(settings)->PublicCheckReader:
    from api.tools.firestore import create_firestore_client
    return PublicCheckReader(create_firestore_client(settings),official_max_age=settings.official_max_age,destination_radius_m=settings.destination_search_radius_m,owned_client=True)

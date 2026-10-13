#!/usr/bin/env python3
"""Explicit local emulator lifecycle. Never deletes containers or volumes."""
import argparse
import json
import subprocess
from dataclasses import dataclass

CLOUD = 'gcr.io/google.com/cloudsdktool/google-cloud-cli:588.0.0-emulators@sha256:be2f0e582a94c9e06e7a384fe2b3b39d590eeb8da65a110eda991598c100fe80'
VOLUME = 'highground-bigquery-live-data'

@dataclass(frozen=True)
class Emulator:
    role: str
    port: int
    image: str
    command: tuple[str, ...]
    environment: tuple[str, ...] = ()
    memory: int = 768 * 1024**2
    swap: int = 1024**3
    volume: str | None = None

    @property
    def name(self): return 'highground-' + self.role

SPECS = (
    Emulator('firestore',8787,CLOUD,('gcloud','emulators','firestore','start','--host-port=0.0.0.0:8787','--project=highground-local','--quiet'),('JAVA_TOOL_OPTIONS=-Xms64m -Xmx384m',)),
    Emulator('pubsub',8797,CLOUD,('gcloud','beta','emulators','pubsub','start','--host-port=0.0.0.0:8797','--project=highground-local','--quiet'),('JAVA_TOOL_OPTIONS=-Xms64m -Xmx384m',)),
    Emulator('gcs',4443,'fsouza/fake-gcs-server:1.56.1@sha256:797ce226d62f947c009dc40246b30cfb456b8473d8241407f9d6f2c04e4d69ef',('-scheme','http','-external-url','http://127.0.0.1:4443'),memory=256*1024**2,swap=384*1024**2),
    Emulator('bigquery',9050,'ghcr.io/goccy/bigquery-emulator:0.8.1@sha256:f4e428d265a93dc5ce36c294e1c584c7c9b384117d47ab8ddbb63d8d50b7f393',('--project=highground-2026-lucas','--dataset=highground','--database=/data/bigquery.db'),('GOMEMLIMIT=512MiB','GOGC=100'),volume=VOLUME),
)

def docker(*arguments):
    return subprocess.run(['docker',*arguments],check=True,capture_output=True,text=True,timeout=30).stdout

def inspect(spec):
    ids=docker('container','ls','--all','--filter','name=^/'+spec.name+'$','--format','{{.ID}}').split()
    if not ids:return None
    if len(ids)!=1:raise ValueError('Ambiguous container identity')
    values=json.loads(docker('inspect',ids[0]))
    if len(values)!=1:raise ValueError('Invalid inspection result')
    return values[0]

def validate(spec, record, bounded=False):
    config=record['Config'];host=record['HostConfig']
    if record['Name']!='/'+spec.name or not record['Id'] or record['Image']!=spec.image.split('@')[1]:raise ValueError('Container name/image identity mismatch')
    if config['Image'] not in (spec.image,spec.image.split('@')[0]) or tuple(config.get('Cmd') or ())!=spec.command:raise ValueError('Container image/command mismatch')
    entrypoints={'gcs':['/bin/fake-gcs-server','-data','/data'],'bigquery':['/bin/bigquery-emulator']}
    if config.get('Entrypoint')!=entrypoints.get(spec.role):raise ValueError('Unexpected container entrypoint')
    labels=config.get('Labels') or {}
    if labels.get('highground.project','highground')!='highground' or labels.get('highground.role',spec.role+'-emulator')!=spec.role+'-emulator':raise ValueError('Container ownership mismatch')
    if host.get('Privileged') or host.get('NetworkMode')=='host':raise ValueError('Unsafe container privileges/network')
    if host['PortBindings']!={str(spec.port)+'/tcp':[{'HostIp':'127.0.0.1','HostPort':str(spec.port)}]}:raise ValueError('Unexpected port exposure')
    mounts=record.get('Mounts') or []
    if spec.volume:
        if len(mounts)!=1 or mounts[0].get('Type')!='volume' or mounts[0].get('Name')!=spec.volume or mounts[0].get('Destination')!='/data' or not mounts[0].get('RW'):raise ValueError('Unexpected persistent volume')
    elif mounts:raise ValueError('Unexpected mount')
    environment=config.get('Env') or []
    for value in spec.environment:
        name=value.split('=')[0]+'='
        matches=[e for e in environment if e.startswith(name)]
        if bounded and matches!=[value]:raise ValueError('Resource environment requires explicit migration')
    if bounded and (host['Memory']!=spec.memory or host['MemorySwap']!=spec.swap):raise ValueError('Memory limits require explicit migration')

def run_command(spec):
    args=['run','-d','--name',spec.name,'--label','highground.project=highground','--label','highground.role='+spec.role+'-emulator','--memory='+str(spec.memory),'--memory-swap='+str(spec.swap),'-p',f'127.0.0.1:{spec.port}:{spec.port}']
    for value in spec.environment:args+=['-e',value]
    if spec.volume:args+=['--mount',f'type=volume,source={spec.volume},target=/data']
    return args+[spec.image,*spec.command]

def operate(action, specs=SPECS, ack=False, initialize=False):
    if initialize and (action!='start' or len(specs)!=1 or specs[0].role!='bigquery'):raise ValueError('Fresh initialization requires start --service bigquery only')
    # Validate the whole requested set before any mutation, then recheck each exact ID.
    records=[]
    for spec in specs:
        record=inspect(spec)
        if record:validate(spec,record,bounded=action=='start')
        if action=='stop' and record and record['State']['Running'] and not spec.volume and not ack:raise ValueError('Stopping ephemeral emulators loses data; --ack-disposable-data required')
        records.append((spec,record))
    if initialize:
        if records[0][1] is not None:raise ValueError('Existing BigQuery container forbids fresh initialization')
        if docker('container','ls','--all','--filter','name=^/highground-bigquery','--format','{{.ID}}').strip():raise ValueError('Historical BigQuery containers require explicit recovery, not fresh initialization')
        for name in (VOLUME,'highground-bigquery-data','highground-bigquery-recovered-data'):
            if docker('volume','ls','--filter','name=^'+name+'$','--format','{{.Name}}').strip():raise ValueError('Retained BigQuery data forbids fresh initialization')
        docker('volume','create','--label','highground.project=highground','--label','highground.role=bigquery-data',VOLUME)
    for spec,record in records:
        if action=='status':
            bounded=True
            if record:
                try:validate(spec,record,bounded=True)
                except ValueError:bounded=False
            print(f'{spec.name}: '+('running' if record and record['State']['Running'] else 'stopped' if record else 'absent')+f'; bounded configuration={bounded if record else "not created"}')
            continue
        if record:
            fresh=inspect(spec)
            if not fresh or fresh['Id']!=record['Id']:raise ValueError('Container identity changed; no mutation')
            validate(spec,fresh,bounded=action=='start')
            if action=='start' and not fresh['State']['Running']:docker('start',record['Id'])
            if action=='stop' and fresh['State']['Running']:
                if not spec.volume and not ack:raise ValueError('Stopping ephemeral emulators loses data; --ack-disposable-data required')
                docker('stop','--time','20',record['Id'])
        elif action=='start':
            if spec.volume:docker('volume','inspect',spec.volume) # Never silently replace lost retained data.
            docker(*run_command(spec))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('start','status','stop'))
    parser.add_argument('--service',choices=tuple(s.role for s in SPECS))
    parser.add_argument('--ack-disposable-data',action='store_true')
    parser.add_argument('--initialize-new-data',action='store_true',help='Fresh BigQuery installation only; refuses retained runtime/data')
    args=parser.parse_args()
    try:operate(args.action,tuple(s for s in SPECS if not args.service or s.role==args.service),args.ack_disposable_data,args.initialize_new_data)
    except (ValueError,KeyError,OSError,subprocess.SubprocessError,json.JSONDecodeError) as error:
        parser.exit(1,'Emulator operation stopped: '+(str(error) if isinstance(error,ValueError) else type(error).__name__)+'\n')

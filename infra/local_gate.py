"""Explicit test scope and validated local endpoints; no shell dotenv execution."""
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

ENDPOINTS={'FIRESTORE_EMULATOR_HOST':'127.0.0.1:8787','PUBSUB_EMULATOR_HOST':'127.0.0.1:8797','STORAGE_EMULATOR_HOST':'http://127.0.0.1:4443','BIGQUERY_EMULATOR_HOST':'http://127.0.0.1:9050'}

def environment(mode, current, dotenv):
    result=dict(current)
    for name,expected in ENDPOINTS.items():
        if mode=='unit':result[name]='';continue
        value=current.get(name,dotenv.get(name))
        if value!=expected:raise ValueError('Full gate requires exact loopback configuration: '+name)
        result[name]=value
    return result

def require_no_skips(path):
    if any(node.tag=='skipped' for node in ET.parse(path).iter()):raise ValueError('Full integration gate rejected skipped tests')

def main(mode):
    from dotenv import dotenv_values
    root=Path(__file__).resolve().parents[1]
    config=dotenv_values(root/'.env') if mode=='full' else {}
    env=environment(mode,os.environ,config)
    if mode=='full':
        for value in ENDPOINTS.values():
            host,port=value.removeprefix('http://').split(':')
            with socket.create_connection((host,int(port)),timeout=3):pass
    else:print('UNIT-ONLY RUN: integration coverage intentionally unavailable; not full Must acceptance.',flush=True)
    with tempfile.TemporaryDirectory(prefix='highground-gate-') as directory:
        report=Path(directory)/'pytest.xml'
        subprocess.run([sys.executable,'-m','pytest','api/tests','-q','--junitxml='+str(report)],cwd=root,env=env,check=True)
        if mode=='full':require_no_skips(report)
    print('API '+mode+' gate passed.',flush=True)

if __name__=='__main__':
    try:main(sys.argv[1])
    except (ValueError,OSError,subprocess.SubprocessError) as error:
        print('Local gate stopped: '+(str(error) if isinstance(error,ValueError) else type(error).__name__),file=sys.stderr)
        sys.exit(1)

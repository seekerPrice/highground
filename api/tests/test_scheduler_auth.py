import asyncio
import json
import time
from dataclasses import replace
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from google.auth import crypt,jwt
import pytest
import httpx
from api.config import Settings
from api.main import create_app
from api.scheduler_auth import verify_scheduler_token,authorize_scheduler,BoundedCertificateRequest


SETTINGS=Settings(scheduler_audience='https://api.example.test',scheduler_caller_email='scheduler@example.iam.gserviceaccount.com',scheduler_caller_subject='1234')


def signed(claims):
    key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    pem=key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption())
    public=key.public_key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    token=jwt.encode(crypt.RSASigner.from_string(pem,key_id='test'),claims).decode()
    class Response:status=200;data=json.dumps({'test':public}).encode()
    return token,lambda *args,**kwargs:Response()


def claims():return {'iss':'https://accounts.google.com','sub':'1234','email':SETTINGS.scheduler_caller_email,'email_verified':True,'aud':SETTINGS.scheduler_audience,'iat':int(time.time())-1,'exp':int(time.time())+60}


def test_actual_signature_and_exact_identity_validation():
    token,transport=signed(claims());verify_scheduler_token(token,SETTINGS,transport)
    for changes in ({'aud':'wrong'},{'sub':'999'},{'email':'other'},{'email_verified':False},{'iss':'https://evil.test'},{'exp':int(time.time())-100}):
        token,transport=signed({**claims(),**changes})
        with pytest.raises(ValueError):verify_scheduler_token(token,SETTINGS,transport)
    token,transport=signed(claims());other,_=signed(claims())
    with pytest.raises(ValueError):verify_scheduler_token(other,SETTINGS,transport)
    with pytest.raises(ValueError):verify_scheduler_token(token,Settings(),transport)


def test_local_auth_requires_explicit_config_not_host(monkeypatch):
    monkeypatch.setenv('FIRESTORE_EMULATOR_HOST','127.0.0.1:8787');monkeypatch.delenv('K_SERVICE',raising=False)
    local=Settings(local_development=True,scheduler_local_auth=True,demo_mode=True,operator_token='synthetic')
    asyncio.run(authorize_scheduler('Bearer synthetic',local))
    for settings in (replace(local,local_development=False),replace(local,demo_mode=False)):
        with pytest.raises(ValueError):asyncio.run(authorize_scheduler('Bearer synthetic',settings))
    monkeypatch.setenv('K_SERVICE','hosted')
    with pytest.raises(ValueError):asyncio.run(authorize_scheduler('Bearer synthetic',local))
    app=create_app(Settings(operator_token='synthetic',demo_mode=True))
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://localhost') as client:
            response=await client.post('/jobs/poll-warnings',headers={'Authorization':'Bearer synthetic','Host':'localhost'})
            assert response.status_code==403
    asyncio.run(run())


def test_cert_fetch_timeout_bounded():
    class Session:
        def request(self,*args,**kwargs):
            assert kwargs['timeout']==5
            class Result:status_code=200;headers={};content=b'{}'
            return Result()
        def close(self):pass
    request=BoundedCertificateRequest(session=Session())
    assert request('https://example.test',timeout=120).status==200


def test_scheduler_script_refuses_cloud_work_before_hosting_authorized(tmp_path):
    import os,subprocess
    from pathlib import Path
    marker=tmp_path/'cloud-called'
    fake=tmp_path/'gcloud'
    fake.write_text('#!/bin/sh\ntouch "'+str(marker)+'"\n')
    fake.chmod(0o755)
    environment={**os.environ,'PATH':str(tmp_path)+':'+os.environ['PATH'],'HOSTING_AUTHORIZED':'false'}
    result=subprocess.run(['bash','infra/scheduler.sh'],env=environment,capture_output=True,text=True)
    assert result.returncode==1 and 'Hosting is deferred' in result.stderr and not marker.exists()

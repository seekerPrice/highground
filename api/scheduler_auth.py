"""Exact Google OIDC caller authorization; explicit local-only development path."""
import asyncio
import hmac
import os

from google.auth.transport.requests import Request
from google.oauth2 import id_token

from api.tools.emulators import loopback_endpoint


class BoundedCertificateRequest(Request):
    def __call__(self, url, method='GET', body=None, headers=None, timeout=5, **kwargs):
        return super().__call__(url,method=method,body=body,headers=headers,timeout=min(timeout or 5,5),**kwargs)


def verify_scheduler_token(token,settings,transport=None):
    if not settings.scheduler_audience or not settings.scheduler_caller_email or not settings.scheduler_caller_subject:
        raise ValueError('Scheduler OIDC is not configured')
    request=transport or BoundedCertificateRequest()
    try:
        claims=id_token.verify_oauth2_token(token,request,audience=settings.scheduler_audience)
        if claims.get('email_verified') is not True or claims.get('email')!=settings.scheduler_caller_email or claims.get('sub')!=settings.scheduler_caller_subject:
            raise ValueError('Unauthorized Scheduler caller')
    except Exception:
        raise ValueError('Scheduler authorization rejected') from None
    finally:
        if transport is None:request.session.close()


async def authorize_scheduler(header,settings):
    if not isinstance(header,str) or not header.startswith('Bearer ') or not 1<=len(header[7:])<=8192:raise ValueError('Invalid authorization')
    token=header[7:]
    if settings.scheduler_local_auth:
        if not settings.local_development or not settings.demo_mode or os.environ.get('K_SERVICE') or not os.environ.get('FIRESTORE_EMULATOR_HOST'):
            raise ValueError('Local Scheduler authentication is disabled')
        loopback_endpoint(os.environ['FIRESTORE_EMULATOR_HOST'])
        if not settings.operator_token or not hmac.compare_digest(token.encode(),settings.operator_token.encode()):raise ValueError('Invalid local operator')
        return
    await asyncio.to_thread(verify_scheduler_token,token,settings)

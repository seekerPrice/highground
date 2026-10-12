"""Explicit-project Firestore clients for domain records and ADK sessions."""
import os
from typing import TYPE_CHECKING

import google.auth
from google.auth.credentials import AnonymousCredentials, Credentials
from google.cloud import firestore

if TYPE_CHECKING:
    from api.config import Settings


def _credentials(settings: 'Settings') -> Credentials:
    if not settings.gcp_project.strip():
        raise ValueError('GCP_PROJECT is required for Firestore')
    if os.environ.get('FIRESTORE_EMULATOR_HOST'):
        return AnonymousCredentials()
    credentials, _ = google.auth.default(
        scopes=['https://www.googleapis.com/auth/cloud-platform'],
        quota_project_id=settings.gcp_project,
    )
    return credentials


def create_firestore_client(settings: 'Settings') -> firestore.Client:
    return firestore.Client(project=settings.gcp_project, credentials=_credentials(settings))


def create_async_firestore_client(settings: 'Settings') -> firestore.AsyncClient:
    return firestore.AsyncClient(project=settings.gcp_project, credentials=_credentials(settings))


async def close_async_firestore_client(client: firestore.AsyncClient) -> None:
    """Close the gRPC transport; SDK Client.close only closes optional HTTP.

    Firestore 2.34.1 exposes no public async-client transport close. Keep this
    pinned-SDK access here so callers can release the owned gRPC channel.
    """
    await client._firestore_api.transport.close()
    client.close()

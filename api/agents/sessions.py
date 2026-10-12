"""Use ADK's shipped transactional Firestore integration, without memory fallback."""
import hashlib
import hmac
from typing import TYPE_CHECKING

from google.adk.integrations.firestore.firestore_session_service import FirestoreSessionService
from google.cloud import firestore

from api.tools.firestore import create_async_firestore_client

if TYPE_CHECKING:
    from api.config import Settings


def session_user_id(chat_id: int, hash_salt: str) -> str:
    if not hash_salt:
        raise ValueError('HASH_SALT is required for session identities')
    if isinstance(chat_id, bool) or not isinstance(chat_id, int):
        raise ValueError('chat_id must be an integer')
    return hmac.new(hash_salt.encode(), str(chat_id).encode(), hashlib.sha256).hexdigest()


def create_session_service(settings: 'Settings', *, root_collection: str = 'highground-adk',
                           client: firestore.AsyncClient | None = None) -> FirestoreSessionService:
    if not root_collection.strip() or '/' in root_collection:
        raise ValueError('root_collection must be a nonempty collection ID')
    return FirestoreSessionService(client=client or create_async_firestore_client(settings),
                                   root_collection=root_collection)

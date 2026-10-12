"""Transactional webhook claims; no external sends inside retried transactions."""
from datetime import datetime, timedelta, timezone
from typing import Any, Literal
from uuid import uuid4

from google.cloud import firestore

ClaimStatus = Literal["claimed", "done", "busy", "uncertain"]


class FirestoreInbox:
    def __init__(self, client: firestore.Client, collection: str = "telegram_inbox") -> None:
        self.client = client
        self.collection = collection

    def claim(self, update_id: int, operation_id: str | None = None) -> tuple[ClaimStatus, str]:
        reference = self.client.collection(self.collection).document(operation_id or str(update_id))
        owner = uuid4().hex
        now = datetime.now(timezone.utc)

        @firestore.transactional
        def acquire(transaction: firestore.Transaction) -> ClaimStatus:
            snapshot = reference.get(transaction=transaction)
            state = snapshot.to_dict() if snapshot.exists else {}
            status = state.get("status")
            if status not in (None, "processing", "sending", "retryable", "done", "uncertain"):
                raise RuntimeError("Invalid inbox state")
            if status == "done":
                return "done"
            if status == "uncertain":
                return "uncertain"
            if status in ("processing", "sending"):
                if state["lease_until"] > now:
                    return "busy"
                if status == "sending":
                    transaction.update(reference, {"status": "uncertain"})
                    return "uncertain"
            transaction.set(reference, {
                "status": "processing", "owner": owner,
                "lease_until": now + timedelta(seconds=60), "updated_at": now,
            })
            return "claimed"

        return acquire(self.client.transaction()), owner

    def transition(self, update_id: int, owner: str, status: str, *, operation_id: str | None = None, **fields: Any) -> None:
        reference = self.client.collection(self.collection).document(operation_id or str(update_id))

        @firestore.transactional
        def change(transaction: firestore.Transaction) -> None:
            state = reference.get(transaction=transaction).to_dict()
            if not state or state.get("owner") != owner:
                raise RuntimeError("Inbox claim ownership changed")
            transaction.update(reference, {"status": status, "updated_at": datetime.now(timezone.utc), **fields})

        change(self.client.transaction())

"""Private shop recipients and single-use invitations; no public serialization."""
from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from typing import Any
from uuid import uuid4

from google.cloud import firestore


class ConversationBusy(Exception):
    pass


class InvitationInvalid(Exception):
    pass


class OnboardingStore:
    def __init__(self, client: firestore.Client, *, prefix: str = "") -> None:
        self.client = client
        self.prefix = prefix

    def collection(self, name: str) -> firestore.CollectionReference:
        return self.client.collection(self.prefix + name)

    def get_shop(self, shop_id: str) -> dict[str, Any] | None:
        return self.collection("shops").document(shop_id).get().to_dict()

    def acquire(self, identity: str) -> str:
        reference = self.collection("conversation_claims").document(identity)
        owner = uuid4().hex
        now = datetime.now(timezone.utc)

        @firestore.transactional
        def claim(transaction: firestore.Transaction) -> None:
            state = reference.get(transaction=transaction).to_dict() or {}
            if state.get("until", now) > now:
                raise ConversationBusy()
            transaction.set(reference, {"owner": owner, "until": now + timedelta(seconds=45)})
        claim(self.client.transaction())
        return owner

    def release(self, identity: str, owner: str) -> None:
        reference = self.collection("conversation_claims").document(identity)

        @firestore.transactional
        def unlock(transaction: firestore.Transaction) -> None:
            state = reference.get(transaction=transaction).to_dict() or {}
            if state.get("owner") == owner:
                transaction.delete(reference)
        unlock(self.client.transaction())

    def save_shop(self, identity: str, chat_id: int, data: dict[str, Any]) -> str:
        shop_id = "shop-" + identity[:32]
        reference = self.collection("shops").document(shop_id)

        @firestore.transactional
        def save(transaction: firestore.Transaction) -> None:
            if reference.get(transaction=transaction).exists:
                return
            transaction.create(reference, {
                "shop_name": data["shop_name"], "shop_type": data["shop_type"],
                "lat": data["lat"], "lng": data["lng"], "address_text": data.get("address_text", ""),
                "floor": data["floor"], "has_vehicle": data["has_vehicle"],
                "vehicle_type": data.get("vehicle_type"),
                "recipients": [{"telegram_chat_id": chat_id, "language": data["language"], "role": "owner"}],
                "risk_score": (40 if data["floor"] == "ground" else 0) + (20 if data["has_vehicle"] else 0),
                "risk_score_provisional": True, "risk_score_missing": ["inventory", "river_or_past_event_exposure"],
                "baseline_inventory_id": None, "lift_first": [], "lift_first_value_rm": 0,
                "created_at": datetime.now(timezone.utc), "is_demo": False,
            })
        save(self.client.transaction())
        return shop_id

    @staticmethod
    def invitation_digest(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    def create_invitation(self, shop_id: str, chat_id: int) -> str:
        token = secrets.token_urlsafe(24)
        digest = self.invitation_digest(token)
        reference = self.collection("invitations").document(digest)
        current = self.collection("shop_invitations").document(shop_id)
        shop_ref = self.collection("shops").document(shop_id)

        @firestore.transactional
        def create(transaction: firestore.Transaction) -> None:
            shop = shop_ref.get(transaction=transaction).to_dict() or {}
            recipients = shop.get("recipients", [])
            if not any(r["telegram_chat_id"] == chat_id and r["role"] == "owner" for r in recipients) or any(r["role"] == "worker" for r in recipients):
                raise InvitationInvalid()
            transaction.set(current, {"digest": digest})
            transaction.create(reference, {"shop_id": shop_id, "expires_at": datetime.now(timezone.utc) + timedelta(hours=1), "used": False})
        create(self.client.transaction())
        return token

    def invitation_shop(self, digest: str) -> dict[str, Any]:
        invite = self.collection("invitations").document(digest).get().to_dict() or {}
        if not invite or invite["used"] or invite["expires_at"] <= datetime.now(timezone.utc):
            raise InvitationInvalid()
        current = self.collection("shop_invitations").document(invite["shop_id"]).get().to_dict() or {}
        shop = self.get_shop(invite["shop_id"])
        if current.get("digest") != digest or not shop:
            raise InvitationInvalid()
        return {"shop_id": invite["shop_id"], "shop_name": shop["shop_name"]}

    def join(self, digest: str, chat_id: int, identity: str, language: str, update_id: int) -> dict[str, Any]:
        reference = self.collection("invitations").document(digest)

        @firestore.transactional
        def consume(transaction: firestore.Transaction) -> dict[str, Any]:
            invite = reference.get(transaction=transaction).to_dict() or {}
            if not invite:
                raise InvitationInvalid()
            if invite["used"]:
                if invite.get("joined_identity") != identity or invite.get("used_update_id") != update_id:
                    raise InvitationInvalid()
                recovered = self.collection("shops").document(invite["shop_id"]).get(transaction=transaction).to_dict() or {}
                if not any(r["telegram_chat_id"] == chat_id and r["role"] == "worker" for r in recovered.get("recipients", [])):
                    raise InvitationInvalid()
                return {"shop_id": invite["shop_id"], "shop_name": recovered["shop_name"]}
            if invite["expires_at"] <= datetime.now(timezone.utc):
                raise InvitationInvalid()
            shop_ref = self.collection("shops").document(invite["shop_id"])
            shop = shop_ref.get(transaction=transaction).to_dict() or {}
            current = self.collection("shop_invitations").document(invite["shop_id"]).get(transaction=transaction).to_dict() or {}
            if current.get("digest") != digest or not shop:
                raise InvitationInvalid()
            recipients = shop["recipients"]
            if any(r["telegram_chat_id"] == chat_id or r["role"] == "worker" for r in recipients):
                raise InvitationInvalid()
            transaction.update(shop_ref, {"recipients": recipients + [{"telegram_chat_id": chat_id, "language": language, "role": "worker"}]})
            transaction.update(reference, {"used": True, "joined_identity": identity, "used_update_id": update_id, "used_at": datetime.now(timezone.utc)})
            return {"shop_id": invite["shop_id"], "shop_name": shop["shop_name"]}
        return consume(self.client.transaction())

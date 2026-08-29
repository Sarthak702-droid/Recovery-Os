import hashlib
import hmac
from datetime import UTC, datetime
import httpx
from app.core.config import get_settings
from domain.events import NormalizedEvent


class RazorpayAdapter:
    """The sole owner of Razorpay Test/Live API and webhook shapes."""
    name = "razorpay"

    async def verify_webhook(self, raw_body: bytes, headers: dict[str, str]) -> bool:
        supplied = headers.get("x-razorpay-signature", "")
        secret = get_settings().razorpay_webhook_secret
        if not secret or not supplied:
            return False
        expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(supplied, expected)

    async def normalize_webhook(self, payload: dict) -> list[NormalizedEvent]:
        event_type = payload.get("event", "unknown")
        payment = payload.get("payload", {}).get("payment", {}).get("entity", {})
        link = payload.get("payload", {}).get("payment_link", {}).get("entity", {})
        entity = payment or link
        entity_id = entity.get("id") or "unknown"
        occurred_at = datetime.fromtimestamp(entity.get("created_at", datetime.now(UTC).timestamp()), UTC)
        event_id = payload.get("id") or f"rzp_{event_type}_{entity_id}_{int(occurred_at.timestamp())}"
        return [NormalizedEvent("razorpay", event_id, event_type, entity_id, occurred_at, payload, f"razorpay:{entity_id}:{event_type}:{int(occurred_at.timestamp())}")]

    async def _request(self, method: str, path: str, body: dict | None = None) -> dict:
        settings = get_settings()
        if not settings.razorpay_key_id or not settings.razorpay_key_secret:
            raise RuntimeError("Razorpay credentials are required; no provider action was attempted")
        async with httpx.AsyncClient(base_url="https://api.razorpay.com/v1", timeout=15) as client:
            response = await client.request(method, path, json=body, auth=(settings.razorpay_key_id, settings.razorpay_key_secret))
            response.raise_for_status()
            return response.json()

    async def get_payment(self, payment_id: str) -> dict: return await self._request("GET", f"/payments/{payment_id}")
    async def get_order(self, order_id: str) -> dict: return await self._request("GET", f"/orders/{order_id}")
    async def create_payment_link(self, request: dict) -> dict: return await self._request("POST", "/payment_links", request)
    async def get_payment_link(self, link_id: str) -> dict: return await self._request("GET", f"/payment_links/{link_id}")
    async def cancel_payment_link(self, link_id: str) -> None: await self._request("POST", f"/payment_links/{link_id}/cancel")
    async def get_subscription(self, subscription_id: str) -> dict: return await self._request("GET", f"/subscriptions/{subscription_id}")

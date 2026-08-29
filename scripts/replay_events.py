"""Replay a webhook fixture against the local API, signing its raw bytes."""
import argparse, hashlib, hmac, json
from pathlib import Path
import httpx

parser = argparse.ArgumentParser(); parser.add_argument("fixture"); parser.add_argument("--secret", default="dev_webhook_secret"); parser.add_argument("--url", default="http://localhost:8000/api/v1/webhooks/razorpay")
args = parser.parse_args(); raw = Path(args.fixture).read_bytes(); signature = hmac.new(args.secret.encode(), raw, hashlib.sha256).hexdigest()
response = httpx.post(args.url, content=raw, headers={"Content-Type":"application/json", "X-Razorpay-Signature":signature}); print(response.status_code, response.text)

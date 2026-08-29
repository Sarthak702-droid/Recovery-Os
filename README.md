# RecoverOS

RecoverOS is an AI-assisted, policy-controlled revenue recovery platform. The agent recommends one bounded next action; deterministic policy authorizes it; the executor rechecks live state; payment-provider evidence verifies recovery; an append-only audit ledger records the flow.

## Run locally

```bash
cp .env.example .env
docker compose --profile ai up --build -d
docker compose exec ollama ollama pull qwen3:1.7b
docker compose exec ollama ollama pull bge-small-en-v1.5
```

The web console is at `http://localhost:3000`; the FastAPI documentation is at `http://localhost:8001/docs`.

## Real integration setup

1. Copy `.env.example` to `.env`; set `MERCHANT_ID`, `MERCHANT_NAME`, Razorpay Test Mode keys, and a strong webhook secret. Do not leave placeholder secrets in this file.
2. Configure Razorpay Test Mode to POST selected payment events to `/api/v1/webhooks/razorpay` and use that same webhook secret.
3. Start the Qwen service with `docker compose --profile ai up -d ollama`, then run `docker compose exec ollama ollama pull qwen3:1.7b` and `docker compose exec ollama ollama pull bge-small-en-v1.5`.
4. Configure SMTP only if you want real recovery emails. Without it, messaging is policy-blocked.

The dashboard shows only persisted webhook/provider outcomes. Razorpay Test Mode is a real integration flow but not real-money revenue; it is labelled accordingly.

## Demonstrable safety controls

- Razorpay webhook HMAC verification uses raw request bytes and durable deduplication.
- Provider JSON is normalized only inside `providers/razorpay`.
- Recommendations are schema-bound and advisory; the policy engine has final authority.
- Payment-link and message commands use idempotency keys and a current-state recheck.
- Only verified successful-payment events can recover a case or attribute revenue.
- Audit events are append-only.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and [docs/AGENT.md](docs/AGENT.md).

# Usage Metering & Billing Engine

A small FastAPI backend that meters simulated AI requests for isolated tenants, enforces monthly plans, calculates integer-based costs, and synchronizes Pro subscriptions from verified Stripe test-mode webhooks.

## Architecture

```text
Client
  | X-Tenant-API-Key + Idempotency-Key
  v
FastAPI routes -> MeteringService -> QuotaService -> PostgreSQL usage_events
                    |                    |
                    +-> CostService      +-> 429 / 402

GET /usage -> monthly usage rollup
Stripe Checkout -> Stripe test mode -> signed /webhooks/stripe -> Subscription sync
```

The HTTP layer (`app/api`) delegates to focused services (`app/services`); SQLAlchemy models and Alembic own persistence.

## Plans and quota behavior

| Plan | API calls/month | AI tokens/month |
|---|---:|---:|
| FREE | 1,000 | 100,000 |
| PRO | 10,000 | 1,000,000 |

The request that brings usage exactly to a limit is allowed. The next request is rejected with `429` and a clear quota message. A non-active subscription returns `402` before metering.

## Pricing

Money is stored as integer **microcents** (`1 cent = 1,000,000 microcents`), never floats.

| Item | microcents |
|---|---:|
| API call | 100 |
| fresh input token | 2 |
| cached input token | 1 |
| output token | 4 |
| reasoning token | 4 |

`input_tokens` includes cached input. Therefore fresh input is `input_tokens - cached_input_tokens`; reasoning tokens use output pricing. A generation produces one API-call event and one AI-token event, both with the same idempotency key. A retry produces neither again.

## Run locally

Prerequisites: Python 3.11+, Docker/Compose, and optionally the Stripe CLI for live webhook verification.

```bash
cp .env.example .env
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
docker compose up -d db
DATABASE_URL=postgresql+psycopg://metering:metering@localhost:5432/metering .venv/bin/alembic upgrade head
DATABASE_URL=postgresql+psycopg://metering:metering@localhost:5432/metering .venv/bin/python -m app.seed
DATABASE_URL=postgresql+psycopg://metering:metering@localhost:5432/metering .venv/bin/uvicorn app.main:app --reload
```

One-container alternative: set safe test placeholders in `.env`, then run `docker compose up --build`.

Run tests with `.venv/bin/pytest`. The tests use an in-memory SQLite database only for fast service tests; production and migrations target PostgreSQL.

## Development authentication and endpoints

The seed command creates `demo-free-key` and `demo-pro-key`. Send either in `X-Tenant-API-Key`; requests only query that tenant’s records.

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | service health |
| POST | `/generate` | simulated billable generation; requires `Idempotency-Key` |
| GET | `/usage` | current tenant’s monthly usage, limits, and cost |
| POST | `/checkout/pro` | creates a Stripe test-mode Pro Checkout session |
| POST | `/webhooks/stripe` | verifies and synchronizes Stripe events |

Example:

```bash
curl -X POST http://localhost:8000/generate \
  -H 'X-Tenant-API-Key: demo-free-key' -H 'Idempotency-Key: demo-001' \
  -H 'Content-Type: application/json' \
  -d '{"input_tokens":100,"cached_input_tokens":20,"output_tokens":10,"reasoning_tokens":5}'
curl http://localhost:8000/usage -H 'X-Tenant-API-Key: demo-free-key'
```

## Stripe test mode

Set only an `sk_test_...` key, a test Price ID, and the `whsec_...` printed by:

```bash
stripe listen --forward-to localhost:8000/webhooks/stripe
```

Call `/checkout/pro`, open its returned URL, and use Stripe test card `4242 4242 4242 4242` with any future date/CVC. The verified `checkout.session.completed` event updates the local tenant to Pro. `customer.subscription.updated` updates payment status; `customer.subscription.deleted` returns the tenant to Free. Replayed event IDs are acknowledged but ignored.

## Background work, migration, and limits

After a successful, committed usage write, FastAPI schedules a notification simulation. Its failure is logged and cannot roll back metering. Alembic migration `0001_initial` creates the four core models plus deduplicated Stripe events and indexes.

Intentionally not implemented: real AI calls, live payments, invoices, proration, overage billing, full auth, Celery/Redis, or a frontend. Demo tenant API keys are deliberately simple; production should hash and rotate them.

# Evidence

All evidence below is from the local test run on 2026-10-02. Stripe Checkout cannot be completed without a user-supplied Stripe test key, Price ID, and webhook secret, so it is explicitly marked manual rather than claimed as complete.

| Requirement | Proof | Command / real output | Explanation |
|---|---|---|---|
| Exactly-once metering and duplicate key | `test_normal_request_and_idempotent_retry` | `.venv/bin/pytest` -> `7 passed in 2.28s` | First response is replayed and the test asserts exactly two records (one API and one token record), not four. |
| Quota boundary and 429 | `test_quota_boundary_and_exceeded` | Same run: `7 passed in 2.28s` | Limit 2: requests 1 and 2 pass; request 3 raises HTTP 429 with `quota exceeded`. |
| 402 payment state | `test_inactive_subscription_returns_402` | Same run: `7 passed in 2.28s` | A `past_due` subscription blocks metering with HTTP 402. |
| Monthly usage and cost | `test_pricing_cached_and_reasoning_rollup` | Same run: `7 passed in 2.28s` | Rollup asserts 115 billable tokens and 340 microcents. |
| Cached-input and reasoning pricing | `test_pricing_cached_and_reasoning_rollup` | Same run: `7 passed in 2.28s` | Proves `80*2 + 20*1 + (10+5)*4 + 100 = 340`. |
| Validation | `test_invalid_input_and_tenant_isolation` | Same run: `7 passed in 2.28s` | Pydantic rejects cached input greater than total input. HTTP FastAPI translates this boundary failure to 422. |
| Tenant isolation | `test_invalid_input_and_tenant_isolation` | Same run: `7 passed in 2.28s` | Tenant B’s rollup stays zero after Tenant A usage. |
| Forged webhook | `test_forged_webhook_is_rejected` | Same run: `7 passed in 2.28s` | Invalid signature becomes HTTP 400 before a processed-event row exists. |
| Duplicate webhook | `test_duplicate_verified_webhook_processed_once` | Same run: `7 passed in 2.28s` | Unique Stripe event ID rejects a repeat; only one processed-event row remains. |
| Persistence and migration | Alembic SQL generation | `DATABASE_URL=... .venv/bin/alembic upgrade head --sql` | Generated PostgreSQL DDL for all five tables. Docker daemon access prevented executing it against a local server. |
| Background job | source review | `app/services/notifications.py` | It runs only after commit and catches/logs its own failure. |
| Secrets | source review | `.gitignore` and `.env.example` | `.env` ignored; placeholders only; Stripe test key is checked for `sk_test_`. |
| Stripe Checkout and verified live webhook | manual required | See README Stripe section | Requires real test-mode credentials and Stripe CLI; not falsely represented as locally completed. |

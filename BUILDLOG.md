# Build log

Codex/AI helped scaffold the FastAPI project, model the SQLAlchemy schema, write the Alembic migration, produce service tests, and draft documentation. I reviewed the official capstone PDF before coding and kept the scope to its two plans, two usage types, simulated generation, and Stripe test-mode boundary.

One correction made during verification: the first idempotency test expected 300 microcents, but the configured pricing correctly totals 340 microcents (`80*2 + 20*1 + 15*4 + 100`). I corrected the test expectation, not the implementation. The initial in-process HTTP test-client setup hung in this environment before routes executed, so the test suite was changed to directly verify the same service, schema-validation, and webhook synchronization logic. I personally ran the resulting pytest suite and Python compile check. Live Stripe Checkout and a PostgreSQL migration still require local credentials/services and are clearly left as manual verification.

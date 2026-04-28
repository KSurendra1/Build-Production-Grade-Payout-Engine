# Playto Payout Engine

Production-grade payout service with ledger integrity, lock-safe concurrency, idempotent payout APIs, async background processing, and a React dashboard.

## Stack
- Backend: Django + DRF
- DB: PostgreSQL (primary)
- Async workers: Celery + Redis
- Frontend: React + Tailwind + Vite

## Core URLs
- API base: `http://127.0.0.1:8000/api/v1`
- Frontend: `http://127.0.0.1:5173`

For production frontend deployment, set `VITE_API_BASE_URL` to your live backend API base (example: `https://backend-api.onrender.com/api/v1`).

## API Endpoints
- `POST /api/v1/merchants`
- `GET /api/v1/merchants/{merchant_id}/balance`
- `GET /api/v1/merchants/{merchant_id}/dashboard`
- `POST /api/v1/payouts` (requires `Idempotency-Key` header)
- `GET /api/v1/payouts?merchant_id={merchant_id}`

## Local Setup (Without Docker)
1. Start PostgreSQL and create DB `payment_db`.
2. In `backend/.env`, set:
   - `DATABASE_URL=postgres://postgres:12345@localhost:5432/payment_db`
3. Backend:
   - `cd backend`
   - `venv\Scripts\pip install -r requirements.txt`
   - `venv\Scripts\python manage.py migrate`
   - `venv\Scripts\python manage.py seed_demo_data --reset`
   - `venv\Scripts\python manage.py runserver 127.0.0.1:8000`
4. Celery (new terminals, from `backend`):
   - `venv\Scripts\python -m celery -A config worker -l info --pool=solo`
   - `venv\Scripts\python -m celery -A config beat -l info`
5. Frontend:
   - `cd frontend`
   - `npm install`
   - `npm run dev -- --host 127.0.0.1 --port 5173`

## Docker Setup
1. `docker compose up --build`
2. `docker compose exec backend python manage.py migrate`
3. `docker compose exec backend python manage.py seed_demo_data --reset`

## Run Tests
- Local: `cd backend && venv\Scripts\python manage.py test payouts.tests -v 2`
- Docker: `docker compose exec backend python manage.py test payouts.tests -v 2`

## Guarantees Implemented
- Money integrity:
  - All amounts are `BigIntegerField` paise.
  - No float math for money.
  - Append-only ledger entries: `CREDIT`, `HOLD`, `DEBIT`, `RELEASE`.
  - Balance is DB aggregation only (no Python balance mutation).
- Concurrency:
  - Merchant row is locked with `SELECT ... FOR UPDATE` in payout creation.
  - Simultaneous overdraw attempts allow exactly one success.
- Idempotency:
  - Key uniqueness scoped by `(merchant, key)`.
  - Request hash is stored to reject same key with different payload.
  - In-flight key returns `409 Conflict`; completed key returns cached response.
  - Exact same response returned for duplicate key.
  - Keys expire after 24h and are recycled.
- State machine:
  - Legal: `PENDING -> PROCESSING -> COMPLETED|FAILED`.
  - Illegal backward transitions are blocked.
  - Refund on failed payout is atomic with state transition.
- Retry:
  - Stuck `PROCESSING` payouts (>30s) retried with exponential backoff.
  - Max 3 retries, then fail + refund atomically.

## Submission Notes
- `EXPLAINER.md` answers all required architecture and AI-audit questions with exact code snippets.
- Tests include:
  - `test_concurrent_payouts_prevent_overdraw`
  - `test_idempotency_returns_same_response_and_single_payout`
- Optional bonus included: `docker-compose.yml`.

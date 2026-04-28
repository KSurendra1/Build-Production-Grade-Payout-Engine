# EXPLAINER

## 1. The Ledger

Why append-only:
- Every money movement is an immutable ledger row (`CREDIT`, `HOLD`, `DEBIT`, `RELEASE`).
- No mutable balance column exists, so drift cannot happen from missed updates.
- Audit trail is complete and replayable.

Balance query (DB aggregation only):

```python
result = LedgerEntry.objects.filter(merchant_id=merchant_id).aggregate(
    balance=Sum(
        Case(
            When(entry_type=LedgerEntry.CREDIT, then=F("amount_paise")),
            When(entry_type=LedgerEntry.HOLD, then=F("amount_paise") * Value(-1)),
            When(entry_type=LedgerEntry.DEBIT, then=F("amount_paise") * Value(-1)),
            When(entry_type=LedgerEntry.RELEASE, then=F("amount_paise")),
            output_field=BigIntegerField(),
        )
    )
)["balance"]
```

Held balance query:

```python
result = LedgerEntry.objects.filter(merchant_id=merchant_id).aggregate(
    held=Sum(
        Case(
            When(entry_type=LedgerEntry.HOLD, then=F("amount_paise")),
            When(entry_type=LedgerEntry.RELEASE, then=F("amount_paise") * Value(-1)),
            output_field=BigIntegerField(),
        )
    )
)["held"]
```

## 2. The Lock

Exact overdraw prevention path:

```python
with transaction.atomic():
    merchant_locked = Merchant.objects.select_for_update().get(pk=merchant.pk)
    available_balance = Merchant.compute_available_balance(merchant_locked.id)
    if available_balance < amount:
        ...
    payout = Payout.objects.create(...)
    LedgerEntry.objects.create(entry_type=LedgerEntry.HOLD, ...)
```

Lock primitive:
- PostgreSQL row-level lock (`SELECT ... FOR UPDATE`) on merchant row.
- Competing requests serialize on the same merchant, so only one can reserve funds first.

## 3. The Idempotency

Storage:
- `IdempotencyKey` unique on `(merchant, key)`.
- Stores `request_hash`, `status` (`processing|completed`), `response_json`, and `response_status`.

Duplicate logic:
- Existing key + `completed` -> return stored response exactly.
- Existing key + `processing` -> return `409 Conflict`.
- Same key with different payload (`request_hash` mismatch) -> `409 Conflict`.

Race handling:
- Two simultaneous inserts of same key rely on DB uniqueness.
- One insert wins, the other catches `IntegrityError` and re-reads locked row.

## 4. The State Machine

Transition guard in model:

```python
legal_transitions = {
    self.STATUS_PENDING: [self.STATUS_PROCESSING],
    self.STATUS_PROCESSING: [self.STATUS_COMPLETED, self.STATUS_FAILED],
    self.STATUS_COMPLETED: [],
    self.STATUS_FAILED: [],
}
if new_status not in legal_transitions.get(self.status, []):
    raise ValueError(...)
```

This blocks invalid transitions such as `FAILED -> COMPLETED` and `COMPLETED -> PENDING`.

## 5. The AI Audit

Wrong AI-style code:

```python
merchant = Merchant.objects.get(id=merchant_id)
if merchant.available_balance >= amount:
    Payout.objects.create(...)
    LedgerEntry.objects.create(...)
```

Why it fails:
- Read-check-write without row lock allows double-spend under concurrent requests.

Corrected production code:

```python
with transaction.atomic():
    merchant_locked = Merchant.objects.select_for_update().get(pk=merchant.pk)
    available_balance = Merchant.compute_available_balance(merchant_locked.id)
    if available_balance < amount:
        ...
    payout = Payout.objects.create(...)
    LedgerEntry.objects.create(entry_type=LedgerEntry.HOLD, ...)
```

Result:
- Concurrency safety is guaranteed by database locking, not Python timing assumptions.

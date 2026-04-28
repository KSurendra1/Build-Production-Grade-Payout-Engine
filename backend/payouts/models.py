import uuid
from datetime import timedelta

from django.db import models
from django.db.models import BigIntegerField, Case, F, Sum, Value, When
from django.utils import timezone


class Merchant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    @staticmethod
    def compute_available_balance(merchant_id):
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
        return result or 0

    @staticmethod
    def compute_held_balance(merchant_id):
        result = LedgerEntry.objects.filter(merchant_id=merchant_id).aggregate(
            held=Sum(
                Case(
                    When(entry_type=LedgerEntry.HOLD, then=F("amount_paise")),
                    When(entry_type=LedgerEntry.RELEASE, then=F("amount_paise") * Value(-1)),
                    output_field=BigIntegerField(),
                )
            )
        )["held"]
        return max(result or 0, 0)

    @property
    def available_balance(self):
        return Merchant.compute_available_balance(self.id)

    @property
    def held_balance(self):
        return Merchant.compute_held_balance(self.id)


class Payout(models.Model):
    STATUS_PENDING = "PENDING"
    STATUS_PROCESSING = "PROCESSING"
    STATUS_COMPLETED = "COMPLETED"
    STATUS_FAILED = "FAILED"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_PROCESSING, "Processing"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_FAILED, "Failed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, related_name="payouts")
    amount_paise = models.BigIntegerField()
    bank_account_id = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    retry_count = models.IntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.id} - {self.status}"

    def _validate_transition(self, new_status):
        legal_transitions = {
            self.STATUS_PENDING: [self.STATUS_PROCESSING],
            self.STATUS_PROCESSING: [self.STATUS_COMPLETED, self.STATUS_FAILED],
            self.STATUS_COMPLETED: [],
            self.STATUS_FAILED: [],
        }

        if new_status not in legal_transitions.get(self.status, []):
            raise ValueError(f"Illegal payout status transition: {self.status} -> {new_status}")

    def transition_to(self, new_status):
        if self.status == new_status:
            return

        self._validate_transition(new_status)
        self.status = new_status
        self.save(update_fields=["status", "updated_at"])


class LedgerEntry(models.Model):
    CREDIT = "CREDIT"
    HOLD = "HOLD"
    DEBIT = "DEBIT"
    RELEASE = "RELEASE"

    ENTRY_TYPES = [
        (CREDIT, "Credit"),
        (HOLD, "Hold"),
        (DEBIT, "Debit"),
        (RELEASE, "Release"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, related_name="ledger_entries")
    amount_paise = models.BigIntegerField()
    entry_type = models.CharField(max_length=10, choices=ENTRY_TYPES)
    payout = models.ForeignKey(
        Payout,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ledger_entries",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.entry_type} - {self.amount_paise}"


class IdempotencyKey(models.Model):
    STATUS_PROCESSING = "processing"
    STATUS_COMPLETED = "completed"
    STATUS_CHOICES = [
        (STATUS_PROCESSING, "Processing"),
        (STATUS_COMPLETED, "Completed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, related_name="idempotency_keys")
    key = models.UUIDField()
    request_hash = models.CharField(max_length=64, default="")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PROCESSING)
    response_status = models.IntegerField(null=True, blank=True)
    response_json = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("merchant", "key")
        indexes = [models.Index(fields=["merchant", "key"])]

    def __str__(self):
        return str(self.key)

    @property
    def is_expired(self):
        expiration = timezone.now() - timedelta(hours=24)
        return self.created_at < expiration

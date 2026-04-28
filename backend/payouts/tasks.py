import random
from datetime import timedelta

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from .models import LedgerEntry, Payout

PROCESSING_TIMEOUT_SECONDS = 30
MAX_RETRY_ATTEMPTS = 3
BASE_RETRY_DELAY_SECONDS = 30


@shared_task
def process_payout(payout_id):
    try:
        with transaction.atomic():
            payout = Payout.objects.select_for_update().get(id=payout_id)
            if payout.status in [Payout.STATUS_COMPLETED, Payout.STATUS_FAILED]:
                return

            if payout.status == Payout.STATUS_PENDING:
                payout.transition_to(Payout.STATUS_PROCESSING)

        outcome = random.random()

        if outcome < 0.70:
            _complete_payout_atomic(payout_id)
            return

        if outcome < 0.90:
            _fail_and_refund_atomic(payout_id)
            return

        # 10% hangs in processing intentionally; retried by periodic task.
        return

    except Payout.DoesNotExist:
        return


@shared_task
def retry_stuck_payouts():
    stuck_threshold = timezone.now() - timedelta(seconds=PROCESSING_TIMEOUT_SECONDS)
    stuck_payout_ids = list(
        Payout.objects.filter(
            status=Payout.STATUS_PROCESSING,
            updated_at__lt=stuck_threshold,
        ).values_list("id", flat=True)
    )

    for payout_id in stuck_payout_ids:
        with transaction.atomic():
            payout = Payout.objects.select_for_update().get(id=payout_id)
            if payout.status != Payout.STATUS_PROCESSING:
                continue

            if payout.retry_count >= MAX_RETRY_ATTEMPTS:
                _fail_and_refund_locked(payout)
                continue

            payout.retry_count = payout.retry_count + 1
            payout.save(update_fields=["retry_count", "updated_at"])
            countdown = BASE_RETRY_DELAY_SECONDS * (2 ** (payout.retry_count - 1))
            process_payout.apply_async(args=[str(payout.id)], countdown=countdown)


def _fail_and_refund_atomic(payout_id):
    with transaction.atomic():
        payout = Payout.objects.select_for_update().get(id=payout_id)
        if payout.status != Payout.STATUS_PROCESSING:
            return
        _fail_and_refund_locked(payout)


def _fail_and_refund_locked(payout):
    payout.transition_to(Payout.STATUS_FAILED)
    LedgerEntry.objects.create(
        merchant=payout.merchant,
        amount_paise=payout.amount_paise,
        entry_type=LedgerEntry.RELEASE,
        payout=payout,
    )


def _complete_payout_atomic(payout_id):
    with transaction.atomic():
        payout = Payout.objects.select_for_update().get(id=payout_id)
        if payout.status != Payout.STATUS_PROCESSING:
            return

        payout.transition_to(Payout.STATUS_COMPLETED)
        # RELEASE cancels HOLD; DEBIT records finalized settlement.
        LedgerEntry.objects.create(
            merchant=payout.merchant,
            amount_paise=payout.amount_paise,
            entry_type=LedgerEntry.RELEASE,
            payout=payout,
        )
        LedgerEntry.objects.create(
            merchant=payout.merchant,
            amount_paise=payout.amount_paise,
            entry_type=LedgerEntry.DEBIT,
            payout=payout,
        )

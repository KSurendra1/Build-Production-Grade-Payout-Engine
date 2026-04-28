import uuid
from concurrent.futures import ThreadPoolExecutor

from django.db import connection
from django.test import TransactionTestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from .models import IdempotencyKey, LedgerEntry, Merchant, Payout


class PayoutTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.client = APIClient()
        self.merchant = Merchant.objects.create(name="Test Merchant")
        LedgerEntry.objects.create(
            merchant=self.merchant,
            amount_paise=10000,
            entry_type=LedgerEntry.CREDIT,
        )
        self.payout_url = reverse("payout-create")

    def test_idempotency_returns_same_response_and_single_payout(self):
        idem_key = str(uuid.uuid4())
        data = {
            "merchant_id": str(self.merchant.id),
            "amount_paise": 6000,
            "bank_account_id": "xyz-bank",
        }

        response1 = self.client.post(self.payout_url, data, format="json", HTTP_IDEMPOTENCY_KEY=idem_key)
        response2 = self.client.post(self.payout_url, data, format="json", HTTP_IDEMPOTENCY_KEY=idem_key)

        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response2.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response1.json(), response2.json())
        self.assertEqual(Payout.objects.filter(merchant=self.merchant).count(), 1)
        self.assertEqual(IdempotencyKey.objects.filter(merchant=self.merchant).count(), 1)

    def test_concurrent_payouts_prevent_overdraw(self):
        connection.close()

        payloads = [
            {
                "merchant_id": str(self.merchant.id),
                "amount_paise": 6000,
                "bank_account_id": "xyz-bank-1",
                "idem_key": str(uuid.uuid4()),
            },
            {
                "merchant_id": str(self.merchant.id),
                "amount_paise": 6000,
                "bank_account_id": "xyz-bank-2",
                "idem_key": str(uuid.uuid4()),
            },
        ]

        def make_request(payload):
            client = APIClient()
            response = client.post(
                self.payout_url,
                {
                    "merchant_id": payload["merchant_id"],
                    "amount_paise": payload["amount_paise"],
                    "bank_account_id": payload["bank_account_id"],
                },
                format="json",
                HTTP_IDEMPOTENCY_KEY=payload["idem_key"],
            )
            connection.close()
            return response

        with ThreadPoolExecutor(max_workers=2) as executor:
            responses = list(executor.map(make_request, payloads))

        successes = [r for r in responses if r.status_code == status.HTTP_201_CREATED]
        failures = [r for r in responses if r.status_code == status.HTTP_400_BAD_REQUEST]

        self.assertEqual(len(successes), 1)
        self.assertEqual(len(failures), 1)
        self.assertIn("Insufficient funds", failures[0].json()["error"])

        self.merchant.refresh_from_db()
        self.assertEqual(self.merchant.available_balance, 4000)
        self.assertEqual(self.merchant.held_balance, 6000)
        self.assertEqual(Payout.objects.filter(merchant=self.merchant).count(), 1)
        self.assertEqual(LedgerEntry.objects.filter(entry_type=LedgerEntry.HOLD).count(), 1)

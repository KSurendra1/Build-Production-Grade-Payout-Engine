import os
import django
import uuid
import requests
import time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from payouts.models import Merchant, LedgerEntry

def main():
    print("Seeding database with a test Merchant...")
    merchant = Merchant.objects.create(name="Test Corp")
    print(f"Created Merchant: {merchant.name} (ID: {merchant.id})")

    print("\nAdding initial balance of 1000.00 INR (100,000 paise)...")
    LedgerEntry.objects.create(
        merchant=merchant,
        amount_paise=100000,
        entry_type='CREDIT'
    )
    
    balance_res = requests.get(f"http://127.0.0.1:8000/api/v1/merchants/{merchant.id}/balance")
    print(f"Current Balance via API: {balance_res.json()}")

    print("\nRequesting a Payout of 500.00 INR...")
    idempotency_key = str(uuid.uuid4())
    payload = {
        "merchant_id": str(merchant.id),
        "amount_paise": 50000,
        "bank_account_id": "bank_123456"
    }
    headers = {
        "Idempotency-Key": idempotency_key
    }
    
    payout_res = requests.post("http://127.0.0.1:8000/api/v1/payouts", json=payload, headers=headers)
    print(f"Payout Response: {payout_res.json()}")

    print("\nWaiting 3 seconds for Celery to process the payout...")
    time.sleep(3)

    balance_res_after = requests.get(f"http://127.0.0.1:8000/api/v1/merchants/{merchant.id}/balance")
    print(f"Final Balance after Payout: {balance_res_after.json()}")
    
    payouts_res = requests.get(f"http://127.0.0.1:8000/api/v1/payouts/?merchant_id={merchant.id}")
    print(f"Payouts List: {payouts_res.json()}")

if __name__ == '__main__':
    main()

import json
import logging
import uuid
from hashlib import sha256

from django.core.serializers.json import DjangoJSONEncoder
from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import IdempotencyKey, LedgerEntry, Merchant, Payout
from .serializers import (
    LedgerEntrySerializer,
    MerchantCreateSerializer,
    MerchantSerializer,
    PayoutCreateSerializer,
    PayoutSerializer,
)
from .tasks import process_payout

logger = logging.getLogger(__name__)


class MerchantBalanceView(APIView):
    def get(self, request, merchant_id):
        try:
            merchant = Merchant.objects.get(id=merchant_id)
        except Merchant.DoesNotExist:
            return Response({"error": "Merchant not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = MerchantSerializer(merchant)
        return Response(serializer.data)


class MerchantDashboardView(APIView):
    def get(self, request, merchant_id):
        try:
            merchant = Merchant.objects.get(id=merchant_id)
        except Merchant.DoesNotExist:
            return Response({"error": "Merchant not found"}, status=status.HTTP_404_NOT_FOUND)

        payouts = Payout.objects.filter(merchant=merchant).order_by("-created_at")[:20]
        recent_entries = LedgerEntry.objects.filter(merchant=merchant).order_by("-created_at")[:20]

        return Response(
            {
                "merchant": MerchantSerializer(merchant).data,
                "payouts": PayoutSerializer(payouts, many=True).data,
                "recent_credits": LedgerEntrySerializer(
                    recent_entries.filter(
                        entry_type__in=[LedgerEntry.CREDIT, LedgerEntry.RELEASE]
                    ),
                    many=True,
                ).data,
                "recent_debits": LedgerEntrySerializer(
                    recent_entries.filter(
                        entry_type__in=[LedgerEntry.HOLD, LedgerEntry.DEBIT]
                    ),
                    many=True,
                ).data,
            }
        )


class MerchantCreateView(APIView):
    def post(self, request):
        serializer = MerchantCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        name = serializer.validated_data["name"]
        initial_credit = serializer.validated_data["initial_credit_paise"]

        try:
            with transaction.atomic():
                merchant = Merchant.objects.create(name=name)
                if initial_credit > 0:
                    LedgerEntry.objects.create(
                        merchant=merchant,
                        amount_paise=initial_credit,
                        entry_type=LedgerEntry.CREDIT,
                    )
                response_data = MerchantSerializer(merchant).data
        except Exception:
            logger.exception("Error creating merchant")
            return Response({"error": "Failed to create merchant"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(response_data, status=status.HTTP_201_CREATED)


class PayoutView(APIView):
    def get(self, request):
        merchant_id = request.query_params.get("merchant_id")
        if not merchant_id:
            return Response({"error": "merchant_id query parameter is required"}, status=status.HTTP_400_BAD_REQUEST)

        payouts = Payout.objects.filter(merchant_id=merchant_id).order_by("-created_at")
        serializer = PayoutSerializer(payouts, many=True)
        return Response(serializer.data)

    def post(self, request):
        merchant_id = request.data.get("merchant_id")
        if not merchant_id:
            return Response({"error": "merchant_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        idempotency_key_str = request.headers.get("Idempotency-Key")
        if not idempotency_key_str:
            return Response({"error": "Idempotency-Key header is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            idempotency_key = uuid.UUID(idempotency_key_str)
        except ValueError:
            return Response({"error": "Idempotency-Key must be a UUID"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = PayoutCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        amount = serializer.validated_data["amount_paise"]
        bank_account_id = serializer.validated_data["bank_account_id"]
        request_hash = self._build_request_hash(merchant_id, amount, bank_account_id)

        try:
            merchant = Merchant.objects.get(id=merchant_id)
        except Merchant.DoesNotExist:
            return Response({"error": "Merchant not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            with transaction.atomic():
                idem_key, created = self._get_or_create_active_idempotency_key(
                    merchant, idempotency_key, request_hash
                )
                if not created:
                    if idem_key.request_hash != request_hash:
                        return Response(
                            {"error": "Idempotency-Key reused with different payload"},
                            status=status.HTTP_409_CONFLICT,
                        )
                    if idem_key.status == IdempotencyKey.STATUS_PROCESSING:
                        return Response(
                            {"error": "Request with this Idempotency-Key is still processing"},
                            status=status.HTTP_409_CONFLICT,
                        )
                    return Response(idem_key.response_json, status=idem_key.response_status)

                merchant_locked = Merchant.objects.select_for_update().get(pk=merchant.pk)
                available_balance = Merchant.compute_available_balance(merchant_locked.id)

                if available_balance < amount:
                    response_data = {"error": "Insufficient funds", "available_balance": available_balance}
                    response_status = status.HTTP_400_BAD_REQUEST
                    idem_key.response_json = response_data
                    idem_key.response_status = response_status
                    idem_key.status = IdempotencyKey.STATUS_COMPLETED
                    idem_key.save(
                        update_fields=["response_json", "response_status", "status", "updated_at"]
                    )
                    return Response(response_data, status=response_status)

                payout = Payout.objects.create(
                    merchant=merchant_locked,
                    amount_paise=amount,
                    bank_account_id=bank_account_id,
                    status=Payout.STATUS_PENDING,
                )

                LedgerEntry.objects.create(
                    merchant=merchant_locked,
                    amount_paise=amount,
                    entry_type=LedgerEntry.HOLD,
                    payout=payout,
                )

                response_data = PayoutSerializer(payout).data
                response_status = status.HTTP_201_CREATED
                idem_key.response_json = json.loads(json.dumps(response_data, cls=DjangoJSONEncoder))
                idem_key.response_status = response_status
                idem_key.status = IdempotencyKey.STATUS_COMPLETED
                idem_key.save(update_fields=["response_json", "response_status", "status", "updated_at"])
        except Exception:
            logger.exception("Error processing payout")
            return Response({"error": "Internal server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        process_payout.delay(str(payout.id))
        return Response(response_data, status=response_status)

    def _build_request_hash(self, merchant_id, amount_paise, bank_account_id):
        payload = f"{merchant_id}|{amount_paise}|{bank_account_id}".encode("utf-8")
        return sha256(payload).hexdigest()

    def _get_or_create_active_idempotency_key(self, merchant, key, request_hash):
        while True:
            try:
                idem_key = IdempotencyKey.objects.select_for_update().get(merchant=merchant, key=key)
                if idem_key.is_expired:
                    idem_key.delete()
                    continue
                return idem_key, False
            except IdempotencyKey.DoesNotExist:
                try:
                    return (
                        IdempotencyKey.objects.create(
                            merchant=merchant,
                            key=key,
                            request_hash=request_hash,
                            status=IdempotencyKey.STATUS_PROCESSING,
                        ),
                        True,
                    )
                except IntegrityError:
                    continue

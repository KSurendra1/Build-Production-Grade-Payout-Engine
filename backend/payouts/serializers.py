from rest_framework import serializers
from .models import Merchant, Payout, LedgerEntry

class MerchantSerializer(serializers.ModelSerializer):
    available_balance = serializers.IntegerField(read_only=True)
    held_balance = serializers.IntegerField(read_only=True)

    class Meta:
        model = Merchant
        fields = ['id', 'name', 'available_balance', 'held_balance', 'created_at']

class PayoutSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payout
        fields = ['id', 'merchant', 'amount_paise', 'bank_account_id', 'status', 'created_at', 'updated_at']
        read_only_fields = ['id', 'status', 'created_at', 'updated_at']

class PayoutCreateSerializer(serializers.Serializer):
    amount_paise = serializers.IntegerField(min_value=1)
    bank_account_id = serializers.CharField(max_length=255)

class MerchantCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    initial_credit_paise = serializers.IntegerField(min_value=0, default=0)

class LedgerEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = LedgerEntry
        fields = ['id', 'merchant', 'amount_paise', 'entry_type', 'payout', 'created_at']

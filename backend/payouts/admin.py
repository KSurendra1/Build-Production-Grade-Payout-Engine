from django.contrib import admin
from .models import Merchant, Payout, LedgerEntry, IdempotencyKey

@admin.register(Merchant)
class MerchantAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'available_balance')
    search_fields = ('name', 'id')

@admin.register(Payout)
class PayoutAdmin(admin.ModelAdmin):
    list_display = ('id', 'merchant', 'amount_paise', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('id', 'merchant__name')

@admin.register(LedgerEntry)
class LedgerEntryAdmin(admin.ModelAdmin):
    list_display = ('id', 'merchant', 'payout', 'amount_paise', 'entry_type', 'created_at')
    list_filter = ('entry_type',)
    search_fields = ('id', 'merchant__name', 'payout__id')

@admin.register(IdempotencyKey)
class IdempotencyKeyAdmin(admin.ModelAdmin):
    list_display = ('merchant', 'key', 'status', 'response_status', 'created_at')
    search_fields = ('key',)

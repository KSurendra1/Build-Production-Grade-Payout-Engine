from django.urls import path

from .views import MerchantBalanceView, MerchantCreateView, MerchantDashboardView, PayoutView

urlpatterns = [
    path("merchants", MerchantCreateView.as_view(), name="merchant-create"),
    path("merchants/<uuid:merchant_id>/balance", MerchantBalanceView.as_view(), name="merchant-balance"),
    path("merchants/<uuid:merchant_id>/dashboard", MerchantDashboardView.as_view(), name="merchant-dashboard"),
    path("payouts", PayoutView.as_view(), name="payout-create"),
]

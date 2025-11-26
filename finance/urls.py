from django.urls import path, include
from rest_framework.routers import DefaultRouter
from finance.views.payments import PaymentViewSet
from finance.views.requests import FundRequestViewSet
from finance.views.wallet import WalletTransactionViewSet
from finance.views.dashboard import NotificationViewSet

# Create a router and register our viewsets with it.
router = DefaultRouter()
router.register(r'payments', PaymentViewSet, basename='payment')
router.register(r'fund-requests', FundRequestViewSet, basename='fund-request')
router.register(r'wallet-transactions', WalletTransactionViewSet, basename='wallet-transaction')
router.register(r'notifications', NotificationViewSet, basename='notification')

urlpatterns = [
    path('', include(router.urls)),
]
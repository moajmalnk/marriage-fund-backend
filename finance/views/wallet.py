from rest_framework import viewsets, permissions
from django.db.models import Q
from finance.models import WalletTransaction
from finance.serializers import WalletTransactionSerializer
from finance.services import process_wallet_transaction

class WalletTransactionViewSet(viewsets.ModelViewSet):
    serializer_class = WalletTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return WalletTransaction.objects.all()
        # Members can only see their own transactions
        return WalletTransaction.objects.filter(user=user)

    def perform_create(self, serializer):
        # Save wallet transaction
        wallet_transaction = serializer.save()
        
        # Trigger notification service
        process_wallet_transaction(wallet_transaction, self.request.user)
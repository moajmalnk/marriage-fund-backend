# cbms-backend/finance/views/wallet.py

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from finance.models import WalletTransaction, Payment, Notification
from finance.serializers import WalletTransactionSerializer

class WalletTransactionViewSet(viewsets.ModelViewSet):
    serializer_class = WalletTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        # Admins see everything (to approve them)
        if user.role == 'admin':
            return WalletTransaction.objects.all().order_by('-date')
        # Users only see their own
        return WalletTransaction.objects.filter(user=user).order_by('-date')

    def perform_create(self, serializer):
        # Force status to PENDING for all new requests
        serializer.save(
            user=self.request.user, 
            recorded_by=self.request.user,
            status='PENDING'
        )
        # Notify Admin (Optional logic here)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """
        Admin approves a deposit.
        1. Updates WalletTransaction status to APPROVED.
        2. Creates a real Payment record so it counts in Dashboard/Team stats.
        """
        if request.user.role != 'admin':
            return Response({'error': 'Authorized personnel only.'}, status=403)

        wallet_tx = self.get_object()

        if wallet_tx.status != 'PENDING':
            return Response({'error': 'Transaction already processed.'}, status=400)

        with transaction.atomic():
            # 1. Update Wallet Status
            wallet_tx.status = 'APPROVED'
            wallet_tx.save()

            # 2. Create the Official Payment Record
            # This is what makes the money show up in "Collected Money" and "Team Stats"
            Payment.objects.create(
                user=wallet_tx.user,
                amount=wallet_tx.amount,
                transaction_type='COLLECT',
                date=wallet_tx.date.date(),
                time=wallet_tx.date.time(),
                recorded_by=request.user,
                notes=f"Wallet Deposit Approved (Ref: {wallet_tx.transaction_id})"
            )

            # 3. Notify User
            Notification.objects.create(
                user=wallet_tx.user,
                title="Deposit Approved ✅",
                message=f"Your deposit of ₹{wallet_tx.amount} has been verified and added to your total.",
                notification_type='SUCCESS',
                priority='MEDIUM'
            )

        return Response({'status': 'approved'})

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        if request.user.role != 'admin':
            return Response({'error': 'Authorized personnel only.'}, status=403)

        wallet_tx = self.get_object()
        if wallet_tx.status != 'PENDING':
            return Response({'error': 'Transaction already processed.'}, status=400)

        wallet_tx.status = 'REJECTED'
        wallet_tx.save()
        
        Notification.objects.create(
            user=wallet_tx.user,
            title="Deposit Rejected ❌",
            message=f"Your deposit of ₹{wallet_tx.amount} was rejected. Please contact admin.",
            notification_type='ERROR',
            priority='HIGH'
        )

        return Response({'status': 'rejected'})
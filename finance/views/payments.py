from rest_framework import viewsets, permissions
from django.db.models import Q
from decimal import Decimal # Required for accurate financial math
from finance.models import Payment, FundRequest
from finance.serializers import PaymentSerializer
from finance.services import process_payment_recording

class PaymentViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return Payment.objects.all()
        if user.role == 'responsible_member':
            return Payment.objects.filter(
                Q(recorded_by=user) |
                Q(user__responsible_member=user) |
                Q(user=user)
            )
        return Payment.objects.filter(user=user)

    def perform_create(self, serializer):
        # 1. Extract the request_id (sent from frontend)
        request_id = serializer.validated_data.pop('request_id', None)
        
        # 2. Save the Payment Record first
        payment = serializer.save()
        
        # 3. Smart Status Update Logic
        if request_id and payment.transaction_type == 'DISBURSE':
            try:
                fund_request = FundRequest.objects.get(id=request_id)
                
                # A. Calculate new total paid
                # Handle cases where paid_amount might be None
                current_paid = fund_request.paid_amount or Decimal('0.00')
                new_total_paid = current_paid + payment.amount
                
                # Update the running total on the request
                fund_request.paid_amount = new_total_paid

                # B. Compare Total Paid vs Requested Amount
                if new_total_paid >= fund_request.amount:
                    fund_request.payment_status = 'PAID'
                else:
                    fund_request.payment_status = 'PARTIAL'
                
                fund_request.save()
                
            except FundRequest.DoesNotExist:
                # Should not happen if frontend sends valid ID, but good for safety
                pass
        
        # 4. Send Notification
        process_payment_recording(payment, self.request.user)

    def perform_update(self, serializer):
        payment = serializer.save()
        process_payment_recording(payment, self.request.user)
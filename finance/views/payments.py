from rest_framework import viewsets, permissions
from django.db.models import Q
from finance.models import Payment
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
        # Save payment (recorded_by is set in the serializer)
        payment = serializer.save()
        
        # Trigger notification service
        process_payment_recording(payment, self.request.user)

    def perform_update(self, serializer):
        # Save updated payment
        payment = serializer.save()
        
        # Trigger notification service
        process_payment_recording(payment, self.request.user)
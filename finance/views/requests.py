from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from django.utils import timezone
from finance.models import FundRequest
from finance.serializers import FundRequestSerializer
from finance.services import process_fund_approval 
from finance.services import process_fund_approval, process_fund_rejection 


class FundRequestViewSet(viewsets.ModelViewSet):
    serializer_class = FundRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return FundRequest.objects.all()
        if user.role == 'responsible_member':
            return FundRequest.objects.filter(
                Q(user__responsible_member=user) | Q(user=user)
            )
        return FundRequest.objects.filter(user=user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user, status='PENDING')

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        if request.user.role != 'admin':
            return Response({'error': 'Not authorized.'}, status=403)
            
        fund_request = self.get_object()
        if fund_request.status == 'APPROVED':
             return Response({'error': 'Already approved.'}, status=400)

        # Use the service layer
        payment_date = request.data.get('payment_date')
        process_fund_approval(fund_request, request.user, payment_date)
        
        return Response({'status': 'approved'})

    @action(detail=True, methods=['post'])
    def decline(self, request, pk=None):
        if request.user.role != 'admin':
             return Response({'error': 'Not authorized.'}, status=403)
            
        fund_request = self.get_object()
        reason = request.data.get('reason', '')
        
        process_fund_rejection(fund_request, request.user, reason)
        
        return Response({'status': 'declined'})
    

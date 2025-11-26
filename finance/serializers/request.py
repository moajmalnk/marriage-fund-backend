from rest_framework import serializers
from finance.models import FundRequest

class FundRequestSerializer(serializers.ModelSerializer):
    user_name = serializers.ReadOnlyField(source='user.get_full_name')
    reviewed_by_name = serializers.ReadOnlyField(source='reviewed_by.get_full_name')

    class Meta:
        model = FundRequest
        fields = [
            'id', 'user', 'user_name', 'amount', 'reason', 
            'detailed_reason', 'status', 'requested_date',
            'reviewed_by', 'reviewed_by_name', 'reviewed_at', 
            'rejection_reason', 'scheduled_payment_date', 
            'payment_status', 'paid_amount'
        ]
        read_only_fields = ['user', 'reviewed_by', 'reviewed_at']
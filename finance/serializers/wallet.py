from rest_framework import serializers
from finance.models import WalletTransaction
from django.utils import timezone

class WalletTransactionSerializer(serializers.ModelSerializer):
    user_name = serializers.ReadOnlyField(source='user.get_full_name')
    recorded_by_name = serializers.ReadOnlyField(source='recorded_by.get_full_name')

    class Meta:
        model = WalletTransaction
        fields = [
            'id', 'user', 'user_name', 'amount', 'transaction_type', 
            'payment_method', 'transaction_id', 'notes', 'date', 
            'recorded_by', 'recorded_by_name', 'created_at'
        ]
        read_only_fields = ['user', 'recorded_by', 'created_at']

    def validate(self, data):
        """
        Validate wallet transaction data
        """
        request_user = self.context['request'].user
        data['user'] = request_user
        data['recorded_by'] = request_user
        
        # Set current time if not provided
        if not data.get('date'):
            data['date'] = timezone.now()
            
        return data
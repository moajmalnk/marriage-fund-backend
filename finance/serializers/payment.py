from rest_framework import serializers
from finance.models import Payment
from django.utils import timezone

class PaymentSerializer(serializers.ModelSerializer):

    request_id = serializers.IntegerField(required=False, write_only=True)
    # Flatten these fields so frontend gets names directly
    user_name = serializers.ReadOnlyField(source='user.get_full_name')
    recorded_by_name = serializers.ReadOnlyField(source='recorded_by.get_full_name')

    class Meta:
        model = Payment
        fields = [
            'id', 'user', 'user_name', 'amount', 'transaction_type', 
            'date', 'time', 'recorded_by', 'recorded_by_name', 
            'notes', 'created_at', 'request_id' 
        ]

        read_only_fields = ['recorded_by']
        extra_kwargs = {
            'time': {'required': False} 
        }

    def validate(self, data):
        """
        Security Fix: Ensure Responsible Members can only record payments 
        for themselves or their assigned team members.
        """
        request_user = self.context['request'].user
        target_user_id = data.get('user')
        
        # For disbursement transactions, get user from the request if not provided
        if data.get('transaction_type') == 'DISBURSE' and not target_user_id:
            request_id = data.get('request_id')
            if request_id:
                try:
                    from finance.models import FundRequest
                    fund_request = FundRequest.objects.get(id=request_id)
                    target_user_id = fund_request.user.id
                    data['user'] = fund_request.user
                except FundRequest.DoesNotExist:
                    raise serializers.ValidationError({'request_id': 'Invalid request ID.'})

        # Set recorded_by to the requesting user
        data['recorded_by'] = request_user

        # Set time if not provided
        if not data.get('time'):
            data['time'] = timezone.now().time()
        elif isinstance(data['time'], str):
            # Parse time string if provided as string
            try:
                from datetime import time as time_constructor
                time_parts = data['time'].split(':')
                if len(time_parts) >= 2:
                    hour = int(time_parts[0])
                    minute = int(time_parts[1])
                    second = int(time_parts[2]) if len(time_parts) > 2 and time_parts[2] else 0
                    data['time'] = time_constructor(hour, minute, second)
            except (ValueError, IndexError):
                # If parsing fails, use current time
                data['time'] = timezone.now().time()

        # Convert user ID to User object
        try:
            from users.models import User
            if isinstance(target_user_id, (int, str)):
                target_user = User.objects.get(id=target_user_id)
                data['user'] = target_user
            else:
                target_user = target_user_id
        except User.DoesNotExist:
            raise serializers.ValidationError({'user': 'Invalid user ID.'})
        except Exception:
            raise serializers.ValidationError({'user': 'Invalid user data.'})

        # Admin can record for anyone
        if request_user.role == 'admin':
            return data

        # Responsible Member Logic
        if request_user.role == 'responsible_member':
            is_self = target_user == request_user
            
            is_assigned = False
            if hasattr(target_user, 'responsible_member'):
                is_assigned = target_user.responsible_member == request_user
            
            if not (is_self or is_assigned):
                raise serializers.ValidationError(
                    {"user": "You are not authorized to record payments for this member."}
                )
            return data

        if target_user != request_user:
             raise serializers.ValidationError({"user": "You cannot record payments for others."})
             
        return data
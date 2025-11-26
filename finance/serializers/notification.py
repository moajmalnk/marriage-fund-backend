from rest_framework import serializers
from finance.models import Notification

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            'id', 'user', 'title', 'message', 'notification_type', 
            'priority', 'is_read', 'created_at', 
            'related_object_id', 'related_object_type'
        ]
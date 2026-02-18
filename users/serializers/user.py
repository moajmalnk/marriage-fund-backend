from rest_framework import serializers
from users.models import User, TermsAcknowledgement

class UserSerializer(serializers.ModelSerializer):
    responsible_member_name = serializers.ReadOnlyField(source='responsible_member.get_full_name')
    name = serializers.SerializerMethodField()
    has_acknowledged_terms = serializers.SerializerMethodField()
    terms_acknowledged_at = serializers.SerializerMethodField()
    profile_photo = serializers.ImageField(use_url=True, required=False)  # Ensure full URL is provided
    
    class Meta:
        model = User
        # FIX: Added 'password' to this list
        fields = [
            'id', 'username', 'password', 'name', 'first_name', 'last_name', 'email', 
            'role', 'marital_status', 'phone', 'profile_photo', 
            'assigned_monthly_amount', 'responsible_member', 
            'responsible_member_name', 'date_joined',
            'has_acknowledged_terms', 'terms_acknowledged_at', 'is_active'
        ]
        extra_kwargs = {'password': {'write_only': True}}

    def get_name(self, obj):
        full_name = obj.get_full_name()
        return full_name if full_name else obj.username
    
    def get_has_acknowledged_terms(self, obj):
        return hasattr(obj, 'terms_acknowledgement')

    def get_terms_acknowledged_at(self, obj):
        if hasattr(obj, 'terms_acknowledgement'):
            return obj.terms_acknowledgement.acknowledged_at
        return None

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        instance = self.Meta.model(**validated_data)
        if password is not None:
            instance.set_password(password)
        instance.save()
        return instance

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if password:
            instance.set_password(password) # This handles the hashing
            
        instance.save()
        return instance

# --- NEW SERIALIZER (Safe for Public Lists) ---
class PublicUserSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    profile_photo = serializers.ImageField(use_url=True, required=False)  # Ensure full URL is provided
    has_acknowledged_terms = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 
            'name', 
            'role', 
            'marital_status', 
            'profile_photo', 
            'responsible_member',
            'has_acknowledged_terms' 
        ]

    def get_name(self, obj):
        full_name = obj.get_full_name()
        return full_name if full_name else obj.username
        
    def get_has_acknowledged_terms(self, obj):
        return hasattr(obj, 'terms_acknowledgement')

class TermsAcknowledgementSerializer(serializers.ModelSerializer):
    class Meta:
        model = TermsAcknowledgement
        fields = ['id', 'user', 'acknowledged_at', 'ip_address', 'user_agent']
        read_only_fields = ['user', 'acknowledged_at', 'ip_address', 'user_agent']



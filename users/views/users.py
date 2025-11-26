
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from users.models import User, TermsAcknowledgement
from users.serializers import UserSerializer, TermsAcknowledgementSerializer, PublicUserSerializer
  
class UserViewSet(viewsets.ModelViewSet):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return User.objects.all().order_by('first_name')
        if user.role == 'responsible_member':
            return User.objects.filter(
                Q(id=user.id) |
                Q(responsible_member=user)
            ).order_by('first_name')
        return User.objects.filter(id=user.id)

    @action(detail=False, methods=['get'])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def my_members(self, request):
        """
        Get all members assigned to the current responsible member.
        """
        user = request.user
        
        if user.role != 'responsible_member':
            return Response(
                {'detail': 'This endpoint is only available for responsible members.'},
                status=403
            )
        
        members = User.objects.filter(responsible_member=user).order_by('first_name')
        serializer = self.get_serializer(members, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def all_public(self, request):
        """
        Returns all users for public lists (like Terms Acknowledgement).
        FIX: Uses PublicUserSerializer to prevent leaking phone/email/financials.
        """
        users = User.objects.all().order_by('first_name')
        # FIX: Use the safe serializer here
        serializer = PublicUserSerializer(users, many=True)
        return Response(serializer.data)

class TermsAcknowledgementViewSet(viewsets.ModelViewSet):
    serializer_class = TermsAcknowledgementSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        serializer.save(user=self.request.user, ip_address=ip)
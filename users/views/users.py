
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from users.models import User, TermsAcknowledgement
from django.core.mail import send_mail
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.conf import settings
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

    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def request_password_reset(self, request):
        email = request.data.get('email')
        if not email:
            return Response({'detail': 'Email is required.'}, status=400)
            
        try:
            user = User.objects.get(email__iexact=email)
            token_generator = PasswordResetTokenGenerator()
            token = token_generator.make_token(user)
            uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
            
            # Find the best origin. Look for a production domain first.
            origins = getattr(settings, 'CORS_ALLOWED_ORIGINS', [])
            frontend_url = 'http://localhost:5173'
            
            for origin in origins:
                if 'codoacademy.com' in origin:
                    frontend_url = origin.rstrip('/')
                    break
            
            reset_url = f"{frontend_url}/reset-password/{uidb64}/{token}"

            # Plain text fallback
            text_content = f'Hello {user.first_name},\n\nPlease click the link below to reset your password:\n{reset_url}\n\nIf you did not request this, please ignore this email.'
            
            # Professional HTML Template
            html_content = render_to_string('emails/password_reset.html', {
                'user': user,
                'reset_url': reset_url,
            })

            msg = EmailMultiAlternatives(
                subject='Password Reset Request - CBMS Fund',
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email],
            )
            msg.attach_alternative(html_content, "text/html")
            msg.send(fail_silently=False)
            
            return Response({'detail': 'If an account with this email exists, a password reset email has been sent.'})
        except User.DoesNotExist:
            # Return success anyway to prevent email enumeration
            return Response({'detail': 'If an account with this email exists, a password reset email has been sent.'})
        except Exception as e:
            # Mask the raw exception so it doesn't break UI layout with traceback strings
            error_msg = str(e)
            if "Authentication Required" in error_msg:
                return Response({'detail': 'Failed to send email: Your email credentials in .env are incorrect or need an App Password.'}, status=500)
            return Response({'detail': 'Failed to send email. Please try again later or contact the administrator.'}, status=500)

    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def confirm_password_reset(self, request):
        uidb64 = request.data.get('uidb64')
        token = request.data.get('token')
        new_password = request.data.get('new_password')

        if not all([uidb64, token, new_password]):
            return Response({'detail': 'Missing required fields.'}, status=400)

        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
            token_generator = PasswordResetTokenGenerator()
            
            if not token_generator.check_token(user, token):
                return Response({'detail': 'Invalid or expired token.'}, status=400)
                
            user.set_password(new_password)
            user.save()
            return Response({'detail': 'Password reset successfully.'})
            
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({'detail': 'Invalid or expired reset link.'}, status=400)

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
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
import os

class User(AbstractUser):
    class Roles(models.TextChoices):
        # We change these to lowercase to match your React frontend types
        ADMIN = 'admin', _('Admin')
        RESPONSIBLE_MEMBER = 'responsible_member', _('Responsible Member')
        MEMBER = 'member', _('Member')

    class MaritalStatus(models.TextChoices):
        MARRIED = 'Married', _('Married')
        UNMARRIED = 'Unmarried', _('Unmarried')

    role = models.CharField(
        max_length=20,
        choices=Roles.choices,
        default=Roles.MEMBER,
        help_text="Determines user permissions"
    )

    responsible_member = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_members',
        limit_choices_to={'role': Roles.RESPONSIBLE_MEMBER},
        help_text="The leader responsible for collecting funds from this member"
    )

    marital_status = models.CharField(
        max_length=10,
        choices=MaritalStatus.choices,
        default=MaritalStatus.UNMARRIED
    )
    phone = models.CharField(max_length=15, blank=True)
    profile_photo = models.ImageField(upload_to='profile_photos/', null=True, blank=True)
    
    assigned_monthly_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.00
    )

    def save(self, *args, **kwargs):
        # Auto-set Admin role if this is a superuser
        if self.is_superuser and not self.role:
            self.role = self.Roles.ADMIN
            
        # Check if profile_photo is being updated
        if self.pk:  # Only for existing users
            try:
                old_user = User.objects.get(pk=self.pk)
                # If the profile photo is changing, delete the old one
                if old_user.profile_photo and self.profile_photo != old_user.profile_photo:
                    # Delete the old profile photo file from storage
                    if old_user.profile_photo and os.path.isfile(old_user.profile_photo.path):
                        os.remove(old_user.profile_photo.path)
            except User.DoesNotExist:
                pass  # User is new, no old photo to delete
        
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Delete profile photo file when user is deleted
        if self.profile_photo:
            if os.path.isfile(self.profile_photo.path):
                os.remove(self.profile_photo.path)
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

class TermsAcknowledgement(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='terms_acknowledgement')
    acknowledged_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    def __str__(self):
        return f"Terms accepted by {self.user.username}"
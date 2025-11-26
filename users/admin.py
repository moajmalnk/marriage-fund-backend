from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

class CustomUserAdmin(UserAdmin):
    model = User
    # Display these columns in the list view
    list_display = ['username', 'email', 'first_name', 'last_name', 'role', 'marital_status']
    
    # Add our custom fields to the edit form
    fieldsets = UserAdmin.fieldsets + (
        ('Custom Fields', {'fields': ('role', 'marital_status', 'phone', 'responsible_member', 'assigned_monthly_amount')}),
    )
    
    # Add our custom fields to the "add user" form
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Custom Fields', {'fields': ('role', 'marital_status', 'phone', 'responsible_member', 'assigned_monthly_amount')}),
    )

admin.site.register(User, CustomUserAdmin)
from django.contrib import admin
from .models import Payment, FundRequest, Notification

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['user', 'amount', 'transaction_type', 'date', 'recorded_by']
    list_filter = ['transaction_type', 'date']
    search_fields = ['user__username', 'user__first_name']

@admin.register(FundRequest)
class FundRequestAdmin(admin.ModelAdmin):
    list_display = ['user', 'amount', 'status', 'payment_status']
    list_filter = ['status', 'payment_status']

admin.site.register(Notification)
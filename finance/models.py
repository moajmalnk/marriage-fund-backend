from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

class Payment(models.Model):
    class TransactionType(models.TextChoices):
        COLLECT = 'COLLECT', _('Collection (In)')
        DISBURSE = 'DISBURSE', _('Disbursement (Out)')

    # Relationships
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='payments',
        help_text="The member who paid or received the money"
    )
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='recorded_payments',
        help_text="The admin or responsible member who entered this record"
    )

    # Transaction Details
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_type = models.CharField(
        max_length=10, 
        choices=TransactionType.choices, 
        default=TransactionType.COLLECT
    )
    date = models.DateField()
    time = models.TimeField(default=timezone.now)
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-time']

    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.user.username} - {self.amount}"


class FundRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', _('Pending')
        APPROVED = 'APPROVED', _('Approved')
        DECLINED = 'DECLINED', _('Declined')

    class PaymentStatus(models.TextChoices):
        PENDING = 'PENDING', _('Pending Payment')
        PARTIAL = 'PARTIAL', _('Partially Paid')
        PAID = 'PAID', _('Fully Paid')

    # Request Details
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name='fund_requests'
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.CharField(max_length=100, default="Marriage Expenses")
    detailed_reason = models.TextField()
    
    # Workflow State
    status = models.CharField(
        max_length=10, 
        choices=Status.choices, 
        default=Status.PENDING
    )
    requested_date = models.DateTimeField(auto_now_add=True)
    
    # Approval Details
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_requests'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    # Payment Tracking (Post-Approval)
    scheduled_payment_date = models.DateField(null=True, blank=True)
    payment_status = models.CharField(
        max_length=10,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING
    )
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    def __str__(self):
        return f"Request by {self.user.username} - {self.status}"


class WalletTransaction(models.Model):
    class TransactionType(models.TextChoices):
        DEPOSIT = 'DEPOSIT', _('Deposit')
        WITHDRAWAL = 'WITHDRAWAL', _('Withdrawal')

    class PaymentMethod(models.TextChoices):
        BANK_TRANSFER = 'bank_transfer', _('Bank Transfer')
        UPI = 'upi', _('UPI Payment')
        CREDIT_CARD = 'credit_card', _('Credit Card')
        DEBIT_CARD = 'debit_card', _('Debit Card')
        NET_BANKING = 'net_banking', _('Net Banking')

    # Relationships
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='wallet_transactions'
    )
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='recorded_wallet_transactions'
    )

    # Transaction Details
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_type = models.CharField(
        max_length=20, 
        choices=TransactionType.choices, 
        default=TransactionType.DEPOSIT
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.BANK_TRANSFER
    )
    transaction_id = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    
    # Timestamps
    date = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date']
        verbose_name = "Wallet Transaction"
        verbose_name_plural = "Wallet Transactions"

    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.user.username} - {self.amount}"

    @property
    def is_deposit(self):
        return self.transaction_type == self.TransactionType.DEPOSIT

    @property
    def is_withdrawal(self):
        return self.transaction_type == self.TransactionType.WITHDRAWAL


class Notification(models.Model):
    class Type(models.TextChoices):
        INFO = 'INFO', _('Info')
        SUCCESS = 'SUCCESS', _('Success')
        WARNING = 'WARNING', _('Warning')
        ERROR = 'ERROR', _('Error')
        PAYMENT = 'PAYMENT', _('Payment')
        WEDDING = 'WEDDING', _('Wedding')
        ANNOUNCEMENT = 'ANNOUNCEMENT', _('Announcement')

    class Priority(models.TextChoices):
        LOW = 'LOW', _('Low')
        MEDIUM = 'MEDIUM', _('Medium')
        HIGH = 'HIGH', _('High')

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=Type.choices, default=Type.INFO)
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.LOW)
    
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    #  Link notification to a specific object
    related_object_id = models.PositiveIntegerField(null=True, blank=True)
    related_object_type = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
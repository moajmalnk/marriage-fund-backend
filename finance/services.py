from django.db import transaction
from django.utils import timezone
from datetime import datetime 
from users.models import User
from .models import Payment, Notification, WalletTransaction

def process_fund_approval(fund_request, user, payment_date=None):
    """
    Handles the approval logic: Updates status only.
    Payment is now a separate manual step.
    """
    with transaction.atomic():
        if payment_date and isinstance(payment_date, str):
            try:
                payment_date = datetime.strptime(payment_date, '%Y-%m-%d').date()
            except ValueError:
                payment_date = timezone.now().date()

        # 1. Update Request Status
        fund_request.status = 'APPROVED'
        fund_request.reviewed_by = user
        fund_request.reviewed_at = timezone.now()
        
        # 2. Set Payment Status to PENDING (Waiting for manual disbursement)
        fund_request.payment_status = 'PENDING' 
        
        if payment_date:
            fund_request.scheduled_payment_date = payment_date
            
        fund_request.save()
        
        # 3. Notify User
        Notification.objects.create(
            user=fund_request.user,
            title="Fund Request Approved! 🎉",
            message=f"Your fund request of ₹{fund_request.amount} has been approved. You will receive the funds on or before {payment_date or 'the scheduled date'}.",
            notification_type=Notification.Type.SUCCESS,
            priority=Notification.Priority.HIGH
        )

def process_fund_rejection(fund_request, user, reason):
    """
    Handles the rejection logic: Updates status, Notifies User.
    """
    with transaction.atomic():
        fund_request.status = 'DECLINED'
        fund_request.reviewed_by = user
        fund_request.reviewed_at = timezone.now()
        fund_request.rejection_reason = reason
        fund_request.save()
        
        # Notify User
        Notification.objects.create(
            user=fund_request.user,
            title="Fund Request Declined",
            message=f"Your fund request of ₹{fund_request.amount} has been declined. Reason: {reason}",
            notification_type=Notification.Type.WARNING,
            priority=Notification.Priority.MEDIUM
        )

def process_payment_recording(payment, user):
    """
    Handles payment recording notifications.
    """
    action = "recorded" if payment.transaction_type == 'COLLECT' else "disbursed"
    amount = payment.amount
    
    # Notify the user who made/received the payment
    Notification.objects.create(
        user=payment.user,
        title=f"Payment {action.title()} 💰",
        message=f"A payment of ₹{amount} has been {action} on {payment.date.strftime('%d %B %Y')}.",
        notification_type=Notification.Type.PAYMENT,
        priority=Notification.Priority.LOW
    )

def process_wallet_transaction(wallet_transaction, user):
    """
    Handles wallet transaction notifications.
    """
    action = "deposited" if wallet_transaction.transaction_type == 'DEPOSIT' else "withdrawn"
    amount = wallet_transaction.amount
    
    # Notify the user about the wallet transaction
    Notification.objects.create(
        user=wallet_transaction.user,
        title=f"Wallet {action.title()} 💳",
        message=f"An amount of ₹{amount} has been {action} to your wallet using {wallet_transaction.get_payment_method_display()}. Transaction ID: {wallet_transaction.transaction_id}",
        notification_type=Notification.Type.PAYMENT,
        priority=Notification.Priority.LOW
    )

def create_wedding_announcement(admin_user, title, message, priority='HIGH'):
    """
    Broadcasts an announcement to ALL users.
    """
    users = User.objects.all()
    notifications = []
    
    for user in users:
        notifications.append(
            Notification(
                user=user,
                title=title,
                message=message,
                notification_type=Notification.Type.ANNOUNCEMENT,
                priority=priority, # Use the passed priority
                related_object_id=admin_user.id,
                related_object_type='broadcast_by_admin'
            )
        )
    
    Notification.objects.bulk_create(notifications)
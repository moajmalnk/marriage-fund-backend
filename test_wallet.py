"""
Test script to verify wallet transaction functionality
"""
import os
import django
from django.conf import settings

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from users.models import User
from finance.models import WalletTransaction

def test_wallet_transaction():
    # Get a test user
    try:
        user = User.objects.get(username='testuser')
    except User.DoesNotExist:
        print("Test user not found. Please create a test user first.")
        return
    
    # Create a wallet transaction
    transaction = WalletTransaction.objects.create(
        user=user,
        amount=1000.00,
        transaction_type=WalletTransaction.TransactionType.DEPOSIT,
        payment_method=WalletTransaction.PaymentMethod.BANK_TRANSFER,
        transaction_id='TEST123456',
        notes='Test deposit'
    )
    
    print(f"Created wallet transaction: {transaction}")
    
    # Verify it was created
    retrieved = WalletTransaction.objects.get(id=transaction.id)
    print(f"Retrieved wallet transaction: {retrieved}")
    
    # Test string representation
    print(f"String representation: {str(retrieved)}")
    
    # Test properties
    print(f"Is deposit: {retrieved.is_deposit}")
    print(f"Is withdrawal: {retrieved.is_withdrawal}")

if __name__ == "__main__":
    test_wallet_transaction()
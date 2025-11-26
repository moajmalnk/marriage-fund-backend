from django.db import transaction
from .models import User

def create_user(username, password, **extra_fields):
    """
    Service to handle safe user creation with password hashing.
    """
    user = User(username=username, **extra_fields)
    user.set_password(password)
    user.save()
    return user

def update_user_profile(user, data):
    """
    Service to handle user profile updates.
    Separating this allows for future logic (e.g., logging changes, 
    sending email on email change) without cluttering views.
    """
    for field, value in data.items():
        if hasattr(user, field):
            setattr(user, field, value)
    
    user.save()
    return user
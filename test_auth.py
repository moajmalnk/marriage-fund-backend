#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from users.models import User

# Set admin password to a known value for testing
try:
    admin = User.objects.get(username='admin')
    admin.set_password('admin123')
    admin.save()
    print(f"✓ Admin password set to 'admin123'")
except User.DoesNotExist:
    print("✗ Admin user not found")

# Also update other users
for username in ['shibilii', 'anas', 'swafwan']:
    try:
        user = User.objects.get(username=username)
        user.set_password('test123')
        user.save()
        print(f"✓ User '{username}' password set to 'test123'")
    except User.DoesNotExist:
        pass

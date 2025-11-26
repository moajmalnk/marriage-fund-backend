from django.urls import path, include
from rest_framework.routers import DefaultRouter
from users.views.users import UserViewSet, TermsAcknowledgementViewSet

# Create a router and register our viewsets with it.
router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'terms', TermsAcknowledgementViewSet, basename='terms')

urlpatterns = [
    path('', include(router.urls)),
]
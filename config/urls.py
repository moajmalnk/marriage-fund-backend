from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenRefreshView

# Import views from your new modular structure
from users.views.auth import CustomTokenObtainPairView
from finance.views.dashboard import DashboardStatsView, TeamStructureView

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # --- Auth Endpoints ---
    # Uses your Custom View to return User Data + Token in one request
    path('api/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # --- Modular App URLs ---
    # This connects the routers defined in users/urls.py and finance/urls.py
    # Frontend routes like /api/users/ and /api/payments/ will work automatically
    path('api/', include('users.urls')),
    path('api/', include('finance.urls')),
    
    # --- Dashboard Specific Views ---
    # These are standalone APIViews, not ViewSets, so we map them manually
    path('api/dashboard/stats/', DashboardStatsView.as_view(), name='dashboard-stats'),
    path('api/teams/', TeamStructureView.as_view(), name='team-structure'),
]

# --- CRITICAL: Serve Media Files in Development ---
# Without this, profile photos uploaded by users will return 404 errors
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
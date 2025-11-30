from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve # <--- Import this
from rest_framework_simplejwt.views import TokenRefreshView

from users.views.auth import CustomTokenObtainPairView
from finance.views.dashboard import DashboardStatsView, TeamStructureView

urlpatterns = [
    path('admin/', admin.site.urls),
    
    path('api/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    path('api/', include('users.urls')),
    path('api/', include('finance.urls')),
    
    path('api/dashboard/stats/', DashboardStatsView.as_view(), name='dashboard-stats'),
    path('api/teams/', TeamStructureView.as_view(), name='team-structure'),
    
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
]

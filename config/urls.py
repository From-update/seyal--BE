from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('accounts.urls')),
    path('api/v1/', include('workspaces.urls')),
    path('api/v1/', include('content.urls')),
    path('api/v1/', include('tasks.urls')),
    path('api/v1/', include('notifications.urls')),
    path('api/v1/', include('billing.urls')),
    path('api/v1/', include('common.urls')),
]


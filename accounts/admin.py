from django.contrib import admin
from .models import User, AuthIdentity, OTPRequest, LoginAudit

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'name', 'phone', 'is_staff', 'is_superuser', 'usage_mode', 'created_at')
    list_filter = ('is_staff', 'is_superuser', 'email_verified', 'usage_mode')
    search_fields = ('email', 'name', 'phone')
    ordering = ('-created_at',)

@admin.register(AuthIdentity)
class AuthIdentityAdmin(admin.ModelAdmin):
    list_display = ('user', 'provider', 'provider_email', 'is_verified', 'created_at')
    list_filter = ('provider', 'is_verified')
    search_fields = ('provider_email', 'provider_user_id')

@admin.register(LoginAudit)
class LoginAuditAdmin(admin.ModelAdmin):
    list_display = ('user', 'provider', 'ip', 'success', 'created_at')
    list_filter = ('success', 'provider')
    search_fields = ('ip', 'device')

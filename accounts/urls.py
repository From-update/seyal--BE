from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    RegisterView, LoginView, SocialAuthView,
    OTPRequestView, OTPVerifyView, MeView,
    OnboardingUsageView, IdentitiesView
)

urlpatterns = [
    path('auth/register', RegisterView.as_view(), name='register'),
    path('auth/login', LoginView.as_view(), name='login'),
    path('auth/refresh', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/social/<str:provider>', SocialAuthView.as_view(), name='social_auth'),
    path('auth/otp/request', OTPRequestView.as_view(), name='otp_request'),
    path('auth/otp/verify', OTPVerifyView.as_view(), name='otp_verify'),
    path('auth/identities', IdentitiesView.as_view(), name='identities_list'),
    path('auth/identities/<uuid:pk>', IdentitiesView.as_view(), name='identity_detail'),
    path('me', MeView.as_view(), name='me'),
    path('onboarding/usage', OnboardingUsageView.as_view(), name='onboarding_usage'),
]


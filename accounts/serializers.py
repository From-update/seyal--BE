from rest_framework import serializers
from .models import User, AuthIdentity, OTPRequest

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'name', 'email', 'email_verified',
            'phone', 'phone_verified', 'avatar_url',
            'language', 'default_workspace_id', 'usage_mode',
            'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'email_verified', 'phone_verified', 'created_at']

class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=6)
    name = serializers.CharField(max_length=150, required=False, default="")
    phone = serializers.CharField(max_length=30, required=False, allow_blank=True, default="")
    role = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

class SocialAuthSerializer(serializers.Serializer):
    provider = serializers.ChoiceField(choices=['google', 'facebook', 'apple'])
    token = serializers.CharField(required=False, default="")
    provider_user_id = serializers.CharField(required=False, default="")
    email = serializers.EmailField(required=False, allow_blank=True, default="")
    name = serializers.CharField(required=False, allow_blank=True, default="")
    avatar_url = serializers.CharField(required=False, allow_blank=True, default="")

class OTPRequestSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=30, required=False, allow_blank=True, default="")
    email = serializers.EmailField(required=False, allow_blank=True, default="")
    provider = serializers.CharField(max_length=30, required=False, allow_blank=True, default="email_otp")

    def validate(self, data):
        phone = data.get('phone', '').strip()
        email = data.get('email', '').strip()
        if not phone and not email:
            raise serializers.ValidationError("Either phone or email is required to request an OTP")
        return data

class OTPVerifySerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=30, required=False, allow_blank=True, default="")
    email = serializers.EmailField(required=False, allow_blank=True, default="")
    code = serializers.CharField(max_length=10)
    name = serializers.CharField(required=False, allow_blank=True, default="")
    provider = serializers.CharField(max_length=30, required=False, allow_blank=True, default="email_otp")

    def validate(self, data):
        phone = data.get('phone', '').strip()
        email = data.get('email', '').strip()
        if not phone and not email:
            raise serializers.ValidationError("Either phone or email is required to verify OTP")
        return data

class AuthIdentitySerializer(serializers.ModelSerializer):
    class Meta:
        model = AuthIdentity
        fields = ['id', 'provider', 'provider_user_id', 'provider_email', 'is_verified', 'created_at']


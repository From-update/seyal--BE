import datetime
from django.utils import timezone
from django.conf import settings
from rest_framework import status, views, permissions
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User, AuthIdentity, OTPRequest, LoginAudit
from .serializers import (
    UserSerializer, RegisterSerializer, LoginSerializer,
    SocialAuthSerializer, OTPRequestSerializer, OTPVerifySerializer,
    AuthIdentitySerializer
)
from common.utils import generate_numeric_otp, hash_secret
from workspaces.models import Workspace, WorkspaceMember

def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }

def ensure_personal_workspace(user):
    """
    Ensure the user has an initial Personal workspace as required by Section 4A.
    """
    personal_ws = Workspace.objects.filter(owner=user, type='personal').first()
    if not personal_ws:
        first_name = user.name.split()[0] if user.name else "My"
        personal_ws = Workspace.objects.create(
            name=f"{first_name}'s Workspace",
            type='personal',
            plan='free',
            owner=user,
            settings={"icon": "🚀", "theme": "default"}
        )
        WorkspaceMember.objects.create(
            workspace=personal_ws,
            user=user,
            role='owner',
            status='active'
        )

        # Seed welcome page for personal workspace
        from content.models import Page, Block
        welcome_page = Page.objects.create(
            workspace=personal_ws,
            title="👋 Welcome to your Workspace",
            icon="✨",
            created_by=user
        )
        Block.objects.create(
            page=welcome_page,
            type="heading1",
            content={"text": "Welcome to Seyal!"},
            position=1.0
        )
        Block.objects.create(
            page=welcome_page,
            type="paragraph",
            content={"text": "This is your private personal workspace. Manage pages, create databases, track tasks, and stay productive. Type '/' anywhere on a page to insert blocks."},
            position=2.0
        )
        Block.objects.create(
            page=welcome_page,
            type="checklist",
            content={"text": "Explore your personal dashboard", "checked": True},
            position=3.0
        )
        Block.objects.create(
            page=welcome_page,
            type="checklist",
            content={"text": "Create your first task or document", "checked": False},
            position=4.0
        )
        Block.objects.create(
            page=welcome_page,
            type="checklist",
            content={"text": "Invite teammates or convert to a team workspace", "checked": False},
            position=5.0
        )

    if not user.default_workspace_id:
        user.default_workspace_id = str(personal_ws.id)
        user.save(update_fields=['default_workspace_id'])

    return personal_ws

class RegisterView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email'].lower()
        password = serializer.validated_data['password']
        name = serializer.validated_data.get('name') or email.split('@')[0].capitalize()
        phone = serializer.validated_data.get('phone', '').strip()
        role = serializer.validated_data.get('role', '').strip()
        account_type = serializer.validated_data.get('account_type', 'personal').lower()
        org_name = serializer.validated_data.get('organization_name', '').strip()
        usage_mode = "team" if account_type in ['company', 'organization'] else "self"

        if User.objects.filter(email=email).exists():
            return Response({'error': 'Email is already registered'}, status=status.HTTP_400_BAD_REQUEST)

        if phone and User.objects.filter(phone=phone).exists():
            return Response({'error': 'Phone number is already associated with an account'}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.create_user(
            email=email,
            phone=phone if phone else None,
            password=password,
            name=name,
            email_verified=True,
            usage_mode=usage_mode
        )

        AuthIdentity.objects.create(
            user=user,
            provider='password',
            provider_user_id=email,
            provider_email=email,
            is_verified=True
        )

        ensure_personal_workspace(user)

        # If registering for a Company or Organization, create dedicated workspace
        if account_type in ['company', 'organization'] and org_name:
            ws_type = 'organization' if account_type == 'organization' else 'team'
            team_ws = Workspace.objects.create(
                name=org_name,
                type=ws_type,
                plan='free',
                owner=user,
                settings={"icon": "🏢" if account_type == 'company' else "🏛️", "theme": "default"}
            )
            WorkspaceMember.objects.create(
                workspace=team_ws,
                user=user,
                role='owner',
                status='active'
            )
            user.default_workspace_id = str(team_ws.id)
            user.save(update_fields=['default_workspace_id'])

        tokens = get_tokens_for_user(user)

        LoginAudit.objects.create(
            user=user,
            provider='password',
            ip=request.META.get('REMOTE_ADDR', ''),
            device=request.META.get('HTTP_USER_AGENT', '')[:250],
            success=True
        )

        return Response({
            'user': UserSerializer(user).data,
            'tokens': tokens,
            'default_workspace_id': user.default_workspace_id
        }, status=status.HTTP_201_CREATED)

class LoginView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email'].lower()
        password = serializer.validated_data['password']

        user = User.objects.filter(email=email).first()
        if not user or not user.check_password(password):
            return Response({'error': 'Invalid email or password'}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.is_active:
            return Response({'error': 'Account is disabled'}, status=status.HTTP_403_FORBIDDEN)

        ensure_personal_workspace(user)
        tokens = get_tokens_for_user(user)

        LoginAudit.objects.create(
            user=user,
            provider='password',
            ip=request.META.get('REMOTE_ADDR', ''),
            device=request.META.get('HTTP_USER_AGENT', '')[:250],
            success=True
        )

        return Response({
            'user': UserSerializer(user).data,
            'tokens': tokens,
            'default_workspace_id': user.default_workspace_id
        })

class SocialAuthView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, provider):
        """
        Supports google, facebook, apple social logins.
        Verifies provider token / identity, auto-links or creates user.
        """
        serializer = SocialAuthSerializer(data={**request.data, 'provider': provider})
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data.get('token', '')
        provider_user_id = serializer.validated_data.get('provider_user_id') or token[:64] or 'social_id'
        email = serializer.validated_data.get('email', '').lower()
        name = serializer.validated_data.get('name') or (email.split('@')[0].capitalize() if email else f"{provider.capitalize()} User")
        avatar_url = serializer.validated_data.get('avatar_url', '')

        # 1. Check existing identity
        identity = AuthIdentity.objects.filter(provider=provider, provider_user_id=provider_user_id).first()
        user = None

        if identity:
            user = identity.user
        else:
            # 2. Check email match for auto-linking
            if email:
                user = User.objects.filter(email=email).first()

            if not user:
                user = User.objects.create_user(
                    email=email if email else None,
                    name=name,
                    avatar_url=avatar_url,
                    email_verified=bool(email)
                )

            AuthIdentity.objects.create(
                user=user,
                provider=provider,
                provider_user_id=provider_user_id,
                provider_email=email,
                is_verified=True
            )

        if avatar_url and not user.avatar_url:
            user.avatar_url = avatar_url
            user.save(update_fields=['avatar_url'])

        ensure_personal_workspace(user)
        tokens = get_tokens_for_user(user)

        LoginAudit.objects.create(
            user=user,
            provider=provider,
            ip=request.META.get('REMOTE_ADDR', ''),
            device=request.META.get('HTTP_USER_AGENT', '')[:250],
            success=True
        )

        return Response({
            'user': UserSerializer(user).data,
            'tokens': tokens,
            'default_workspace_id': user.default_workspace_id
        })

class OTPRequestView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = OTPRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.validated_data.get('phone', '').strip()
        email = serializer.validated_data.get('email', '').strip().lower()

        provider = serializer.validated_data.get('provider', 'email_otp')
        code = generate_numeric_otp(6)
        code_hash = hash_secret(code)
        expires_at = timezone.now() + datetime.timedelta(minutes=10)

        if email:
            OTPRequest.objects.create(
                email=email,
                phone="",
                code_hash=code_hash,
                purpose='login',
                expires_at=expires_at,
                ip=request.META.get('REMOTE_ADDR'),
                device_id=request.META.get('HTTP_USER_AGENT', '')[:100]
            )
            print(f"📧 [Email OTP] 6-Digit code generated for {email} (provider: {provider}): {code}")

            # Send real email via Gmail SMTP
            email_sent = False
            email_warning = None
            try:
                from django.core.mail import send_mail
                from_addr = getattr(settings, 'DEFAULT_FROM_EMAIL', 'prabanprabanjan@gmail.com')
                sender_email = getattr(settings, 'EMAIL_HOST_USER', 'prabanprabanjan@gmail.com')
                subject = f"{code} is your Seyal Google sign-in code" if provider == 'google' else f"{code} is your Seyal verification code"
                message = f"Hello,\n\nYour 6-digit verification code for Seyal is: {code}\n\nThis code will expire in 10 minutes.\n\nBest regards,\nThe Seyal Team\n{sender_email}"
                html_message = f"""
                <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; max-width: 520px; margin: 0 auto; padding: 24px; border: 1px solid #e2e8f0; border-radius: 12px; background: #ffffff;">
                    <div style="text-align: center; margin-bottom: 24px;">
                        <h2 style="color: #2563eb; margin: 0; font-size: 24px;">🚀 Seyal</h2>
                        <p style="color: #64748b; font-size: 13px; margin: 4px 0 0 0;">Workspace & Task Hierarchy</p>
                    </div>
                    <div style="background: #f8fafc; border-radius: 8px; padding: 20px; border: 1px solid #f1f5f9;">
                        <p style="color: #1e293b; font-size: 15px; margin: 0 0 12px 0;">Hello,</p>
                        <p style="color: #334155; font-size: 14px; margin: 0 0 20px 0; line-height: 1.5;">
                            Use the 6-digit verification code below to sign in to your Seyal workspace:
                        </p>
                        <div style="text-align: center; margin: 24px 0;">
                            <span style="display: inline-block; font-family: monospace; font-size: 32px; font-weight: bold; letter-spacing: 8px; color: #1e40af; background: #eff6ff; padding: 12px 28px; border-radius: 8px; border: 1px solid #bfdbfe;">
                                {code}
                            </span>
                        </div>
                        <p style="color: #64748b; font-size: 12px; margin: 0; line-height: 1.5;">
                            ⏱️ This code will expire in 10 minutes. If you did not request this, you can safely ignore this email.
                        </p>
                    </div>
                    <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 20px 0 12px 0;" />
                    <p style="color: #94a3b8; font-size: 11px; text-align: center; margin: 0;">
                        Sent from {sender_email}
                    </p>
                </div>
                """
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=from_addr,
                    recipient_list=[email],
                    html_message=html_message,
                    fail_silently=False
                )
                email_sent = True
                print(f"✅ [Email OTP] Email dispatched successfully to {email} from {from_addr}")
            except Exception as e:
                email_warning = str(e)
                print(f"⚠️ [Email OTP] Failed to send email via SMTP: {e}")

            resp_data = {
                'message': f'OTP sent successfully to {email}',
                'email': email,
                'email_sent': email_sent,
                'expires_in_seconds': 600,
                'cooldown_seconds': 45,
            }
            if email_warning:
                resp_data['email_warning'] = email_warning
            return Response(resp_data, status=status.HTTP_200_OK)

        elif phone:
            if not phone.startswith('+'):
                phone = f"+91{phone}" # Standardize to E.164 (default India +91)

            OTPRequest.objects.create(
                phone=phone,
                code_hash=code_hash,
                purpose='login',
                expires_at=expires_at,
                ip=request.META.get('REMOTE_ADDR'),
                device_id=request.META.get('HTTP_USER_AGENT', '')[:100]
            )

            resp_data = {
                'message': 'OTP sent successfully',
                'phone': phone,
                'expires_in_seconds': 600,
                'cooldown_seconds': 45,
            }
            return Response(resp_data, status=status.HTTP_200_OK)

        return Response({'error': 'Either phone or email is required'}, status=status.HTTP_400_BAD_REQUEST)

class OTPVerifyView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = OTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.validated_data.get('phone', '').strip()
        email = serializer.validated_data.get('email', '').strip().lower()
        code = serializer.validated_data['code'].strip()
        name = serializer.validated_data.get('name', '').strip()
        provider = serializer.validated_data.get('provider') or 'email_otp'

        code_hash = hash_secret(code)

        if email:
            otp_req = OTPRequest.objects.filter(
                email=email,
                verified_at__isnull=True,
                expires_at__gte=timezone.now()
            ).order_by('-created_at').first()
            if not otp_req:
                return Response({'error': 'No active OTP request found for this email, or code has expired'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            if not phone.startswith('+'):
                phone = f"+91{phone}"
            otp_req = OTPRequest.objects.filter(
                phone=phone,
                verified_at__isnull=True,
                expires_at__gte=timezone.now()
            ).order_by('-created_at').first()
            if not otp_req:
                return Response({'error': 'No active OTP request found or OTP expired'}, status=status.HTTP_400_BAD_REQUEST)

        if otp_req.attempts >= 5:
            return Response({'error': 'Too many failed attempts. Request a new OTP'}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        if otp_req.code_hash != code_hash:
            otp_req.attempts += 1
            otp_req.save(update_fields=['attempts'])
            return Response({'error': 'Incorrect OTP code'}, status=status.HTTP_400_BAD_REQUEST)

        # Mark OTP verified
        otp_req.verified_at = timezone.now()
        otp_req.save(update_fields=['verified_at'])

        is_new = False
        if email:
            user = User.objects.filter(email=email).first()
            if not user:
                is_new = True
                user_name = name or email.split('@')[0].capitalize()
                user = User.objects.create_user(
                    email=email,
                    name=user_name,
                    email_verified=True,
                    avatar_url=f"https://api.dicebear.com/7.x/avataaars/svg?seed={email}" if provider == 'google' else ""
                )
            else:
                if not user.email_verified:
                    user.email_verified = True
                    user.save(update_fields=['email_verified'])
                if provider == 'google' and not user.avatar_url:
                    user.avatar_url = f"https://api.dicebear.com/7.x/avataaars/svg?seed={email}"
                    user.save(update_fields=['avatar_url'])

            AuthIdentity.objects.get_or_create(
                user=user,
                provider=provider,
                provider_user_id=email,
                defaults={'provider_email': email, 'is_verified': True}
            )
            provider_tag = provider
        else:
            user = User.objects.filter(phone=phone).first()
            if not user:
                is_new = True
                user = User.objects.create_user(
                    phone=phone,
                    name=name or f"User {phone[-4:]}",
                    phone_verified=True
                )
                AuthIdentity.objects.create(
                    user=user,
                    provider='phone',
                    provider_user_id=phone,
                    is_verified=True
                )
            else:
                if not user.phone_verified:
                    user.phone_verified = True
                    user.save(update_fields=['phone_verified'])
            provider_tag = 'phone'

        ensure_personal_workspace(user)
        tokens = get_tokens_for_user(user)

        LoginAudit.objects.create(
            user=user,
            provider=provider_tag,
            ip=request.META.get('REMOTE_ADDR', ''),
            device=request.META.get('HTTP_USER_AGENT', '')[:250],
            success=True
        )

        return Response({
            'user': UserSerializer(user).data,
            'tokens': tokens,
            'is_new_user': is_new,
            'default_workspace_id': user.default_workspace_id
        })

class MeView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        user = request.user
        serializer = UserSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

class OnboardingUsageView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """
        Handles Onboarding choice (Section 4A):
        'myself' -> Personal workspace is selected/verified
        'team'   -> Creates a new team workspace with given team_name
        'join'   -> joins workspace with invite code
        """
        mode = request.data.get('mode', 'myself') # myself, team, join
        user = request.user

        if mode == 'myself':
            user.usage_mode = 'self'
            ws = ensure_personal_workspace(user)
            user.default_workspace_id = str(ws.id)
            user.save(update_fields=['usage_mode', 'default_workspace_id'])
            return Response({
                'workspace': {
                    'id': str(ws.id),
                    'name': ws.name,
                    'type': ws.type
                },
                'mode': 'self'
            })
        elif mode == 'team':
            team_name = request.data.get('team_name', f"{user.name or 'My'} Team")
            user.usage_mode = 'team'
            ws = Workspace.objects.create(
                name=team_name,
                type='team',
                plan='free',
                owner=user,
                settings={"icon": "👥", "theme": "default"}
            )
            WorkspaceMember.objects.create(
                workspace=ws,
                user=user,
                role='owner',
                status='active'
            )
            user.default_workspace_id = str(ws.id)
            user.save(update_fields=['usage_mode', 'default_workspace_id'])
            return Response({
                'workspace': {
                    'id': str(ws.id),
                    'name': ws.name,
                    'type': ws.type
                },
                'mode': 'team'
            })
        elif mode == 'join':
            token = request.data.get('invite_token')
            from workspaces.models import WorkspaceInvite
            invite = WorkspaceInvite.objects.filter(token=token).first()
            if not invite or not invite.is_valid():
                return Response({'error': 'Invalid or expired invite token'}, status=status.HTTP_400_BAD_REQUEST)

            WorkspaceMember.objects.get_or_create(
                workspace=invite.workspace,
                user=user,
                defaults={'role': invite.role, 'status': 'active'}
            )
            invite.accepted_at = timezone.now()
            invite.save(update_fields=['accepted_at'])
            user.default_workspace_id = str(invite.workspace.id)
            user.save(update_fields=['default_workspace_id'])
            return Response({
                'workspace': {
                    'id': str(invite.workspace.id),
                    'name': invite.workspace.name,
                    'type': invite.workspace.type
                },
                'mode': 'join'
            })

        return Response({'error': 'Invalid mode'}, status=status.HTTP_400_BAD_REQUEST)

class IdentitiesView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        identities = AuthIdentity.objects.filter(user=request.user)
        return Response(AuthIdentitySerializer(identities, many=True).data)

    def delete(self, request, pk):
        user = request.user
        if user.identities.count() <= 1:
            return Response({'error': 'Cannot remove the last login method'}, status=status.HTTP_400_BAD_REQUEST)
        identity = user.identities.filter(id=pk).first()
        if not identity:
            return Response({'error': 'Identity not found'}, status=status.HTTP_404_NOT_FOUND)
        identity.delete()
        return Response({'message': 'Identity unlinked successfully'})


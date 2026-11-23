from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

class AdminOrEmailBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)
        if username:
            username = str(username).strip().lower()
            if username == 'admin':
                user = UserModel.objects.filter(email='admin@seyal.app').first() or UserModel.objects.filter(email='superadmin@seyal.app').first()
                if user and user.check_password(password) and self.user_can_authenticate(user):
                    return user
            user = UserModel.objects.filter(email=username).first()
            if user and user.check_password(password) and self.user_can_authenticate(user):
                return user
        return None

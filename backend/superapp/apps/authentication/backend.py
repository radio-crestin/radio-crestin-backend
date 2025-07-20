from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

UserModel = get_user_model()


class EmailBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            user = UserModel.objects.filter(email=username).first()
            if not user:
                return None
        except UserModel.DoesNotExist:
            return None
        else:
            if user.check_password(password):
                return user
        return None

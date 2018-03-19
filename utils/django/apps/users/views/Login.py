from .. import serializers
from utils.django.auth.views import LoginView as BaseLoginView


class LoginView(BaseLoginView):
    """
    Login to the site
    """
    user_serializer_class = serializers.UserSerializer

from .. import serializers
from utils.django.auth.views import SignupView as BaseSignupView


class SignupView(BaseSignupView):
    """
    Register on the site

    It will automatically login as new user.
    """
    user_serializer_class = serializers.UserSerializer

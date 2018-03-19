from rest_framework import views
from rest_framework.response import Response
from django.contrib.auth import logout


class LogoutView(views.APIView):
    """
    Logout from the site
    """
    def post(self, request):
        logout(request)
        return Response('OK')

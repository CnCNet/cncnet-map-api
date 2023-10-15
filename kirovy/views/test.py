from django.conf import settings
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from kirovy.request import KirovyRequest


class TestJwt(APIView):
    """
    Test JWT tokens. Only for use in tests.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: KirovyRequest, format=None):
        if not settings.DEBUG:
            return Response(status=status.HTTP_403_FORBIDDEN)
        return Response(request.auth.email, status.HTTP_200_OK)

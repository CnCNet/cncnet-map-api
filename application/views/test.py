from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView


class TestJwt(APIView):
    """
    List all snippets, or create a new snippet.
    """

    def get(self, request: Request, format=None):

        return Response("hello", status.HTTP_200_OK)

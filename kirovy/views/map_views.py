from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from kirovy import permissions
from kirovy.request import KirovyRequest
from kirovy.views import base_views


class MapListCreateView(base_views.KirovyListCreateView):
    """
    The view for maps.
    """


class MapRetrieveUpdateView(base_views.KirovyRetrieveUpdateView):
    ...


class MapDeleteView(base_views.KirovyDestroyView):
    ...

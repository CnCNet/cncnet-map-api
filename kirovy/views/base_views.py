"""
Base views with common functionality for all API views in Kirovy
"""
from rest_framework import (
    exceptions as _e,
    generics as _g,
    permissions as _p,
    pagination as _pagination,
)
from rest_framework.response import Response

from kirovy import permissions
from kirovy.request import KirovyRequest


class KirovyDefaultPagination(_pagination.PageNumberPagination):
    """Default pagination values."""

    page_size = 30
    page_size_query_param = "page_size"
    max_page_size = 200


class KirovyListCreateView(_g.ListCreateAPIView):
    """Base view for listing and creating objects.

    It is up to subclasses to figure out how they want to filter large queries.
    """

    permission_classes = [permissions.CanUpload | permissions.ReadOnly]
    pagination_class = KirovyDefaultPagination


class KirovyRetrieveUpdateView(_g.RetrieveUpdateAPIView):
    """Base view for detail views and editing.

    We only allow partial updates because full updates always cause issues when two users are editing.

    e.g. Bob and Alice both have the page open. Alice updates an object, Bob doesn't refresh his page and updates
    the object. Bob's data doesn't have Alice's updates, so his stale data overwrites Alice's.
    """

    permission_classes = [permissions.CanEdit | permissions.ReadOnly]

    def put(self, request: KirovyRequest, *args, **kwargs) -> Response:
        raise _e.MethodNotAllowed(
            "PUT",
            "PUT is not allowed. Only use PATCH and only send fields that were modified.",
        )

    def delete(self, request: KirovyRequest, *args, **kwargs) -> Response:
        raise _e.MethodNotAllowed(
            "DELETE",
            "DELETE is not allowed on this endpoint. Please use the delete endpoint.",
        )


class KirovyRetrieveUpdateDestroyView(KirovyRetrieveUpdateView):
    """Prevents accidentally allowing deletes for CanEdit permissions until we allow user deletion."""

    pass


class KirovyDestroyView(_g.DestroyAPIView):
    """Base view for all delete endpoints in the app.

    For now, only admins can delete stuff.
    """

    permission_classes = [permissions.CanDelete | _p.IsAdminUser]

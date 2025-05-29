"""
Base views with common functionality for all API views in Kirovy
"""

from rest_framework import (
    exceptions as _e,
    generics as _g,
    permissions as _p,
    pagination as _pagination,
    status,
)
from rest_framework.response import Response

import kirovy.objects.ui_objects
from kirovy import permissions, typing as t
from kirovy.objects import ui_objects
from kirovy.request import KirovyRequest
from kirovy.response import KirovyResponse
from kirovy.serializers import KirovySerializer


class KirovyDefaultPagination(_pagination.LimitOffsetPagination):
    """Default pagination values."""

    default_limit = 30
    max_limit = 200

    def get_paginated_response(self, results: t.List[t.DictStrAny]) -> KirovyResponse[ui_objects.ListResponseData]:
        data = kirovy.objects.ui_objects.ListResponseData(
            results=results,
            pagination_metadata=kirovy.objects.ui_objects.PaginationMetadata(
                offset=self.offset,
                limit=self.limit,
                remaining_count=self.count,
            ),
        )

        return KirovyResponse(data, status=status.HTTP_200_OK)

    # def get_paginated_response_schema(self, schema):
    #     raise NotImplementedError()


class KirovyListCreateView(_g.ListCreateAPIView):
    """Base view for listing and creating objects.

    It is up to subclasses to figure out how they want to filter large queries.
    """

    permission_classes = [permissions.CanUpload | permissions.ReadOnly]
    pagination_class: t.Optional[t.Type[KirovyDefaultPagination]] = KirovyDefaultPagination
    _paginator: t.Optional[KirovyDefaultPagination]
    request: KirovyRequest  # Added for type hinting. Populated by DRF ``.setup()``

    def create(self, request: KirovyRequest, *args, **kwargs) -> KirovyResponse[ui_objects.ResultResponseData]:
        data = request.data
        if isinstance(data, dict) and issubclass(self.get_serializer_class(), KirovySerializer):
            data["last_modified_by_id"] = request.user.id
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        data = ui_objects.ResultResponseData(result=serializer.data)
        return KirovyResponse(data, status=status.HTTP_201_CREATED, headers=headers)

    def list(self, request, *args, **kwargs) -> KirovyResponse[ui_objects.ListResponseData]:
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        data = kirovy.objects.ui_objects.ListResponseData(results=serializer.data)
        return KirovyResponse(data, status=status.HTTP_200_OK)

    def get_paginated_response(self, data: t.List[t.DictStrAny]) -> KirovyResponse[ui_objects.ListResponseData]:
        """
        Return a paginated style `Response` object for the given output data.
        """
        return super().get_paginated_response(data)

    @property
    def paginator(self) -> t.Optional[KirovyDefaultPagination]:
        """Just here for type hinting."""
        return super().paginator


class KirovyRetrieveUpdateView(_g.RetrieveUpdateAPIView):
    """Base view for detail views and editing.

    We only allow partial updates because full updates always cause issues when two users are editing.

    e.g. Bob and Alice both have the page open. Alice updates an object, Bob doesn't refresh his page and updates
    the object. Bob's data doesn't have Alice's updates, so his stale data overwrites Alice's.
    """

    request: KirovyRequest  # Added for type hinting. Populated by DRF ``.setup()``
    permission_classes = [permissions.CanEdit | permissions.ReadOnly]

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return KirovyResponse(
            kirovy.objects.ui_objects.ResultResponseData(
                result=serializer.data,
            ),
            status=status.HTTP_200_OK,
        )

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

    request: KirovyRequest  # Added for type hinting. Populated by DRF ``.setup()``
    permission_classes = [permissions.CanDelete | _p.IsAdminUser]

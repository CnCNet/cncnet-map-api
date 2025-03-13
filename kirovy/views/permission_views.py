from rest_framework import status
from rest_framework.views import APIView

import kirovy.objects.ui_objects
from kirovy import permissions, typing as t
from kirovy.request import KirovyRequest
from kirovy.response import KirovyResponse


class ListPermissionForAuthUser(APIView):
    """End point to check which buttons / views the UI should show.

    The UI showing the buttons / views will not guarantee access. The backend still checks permissions for all
    requests. This just helps the UI know what to render. DO NOT use for permission checks within Kirovy.
    """

    permission_classes = [permissions.ReadOnly]
    http_method_names = [
        "get",
    ]

    def get(self, request: KirovyRequest, *args, **kwargs) -> KirovyResponse:
        data = kirovy.objects.ui_objects.ResultResponseData(
            result=kirovy.objects.ui_objects.UiPermissions.render_static(request, self)
        )
        return KirovyResponse(data=data, status=status.HTTP_200_OK)

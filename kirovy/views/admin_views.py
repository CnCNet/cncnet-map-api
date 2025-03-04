import pydantic
from rest_framework import status
from rest_framework.generics import get_object_or_404
from rest_framework.views import APIView

from kirovy import permissions, exceptions
from kirovy.objects import ui_objects
from kirovy.request import KirovyRequest
from kirovy.response import KirovyResponse


class BanView(APIView):
    """The view for banning things.

    ``POST /admin/ban/``

    Payload :attr:`kirovy.objects.ui_objects.BanData`.
    """

    http_method_names = ["post"]
    permission_classes = [permissions.IsStaff]

    def post(self, request: KirovyRequest, **kwargs) -> KirovyResponse:
        if not request.data:
            return KirovyResponse(
                status=status.HTTP_400_BAD_REQUEST,
                data=ui_objects.ErrorResponseData(message="no_data"),
            )
        try:
            ban_data = ui_objects.BanData(**request.data)
        except pydantic.ValidationError:
            return KirovyResponse(
                status=status.HTTP_400_BAD_REQUEST,
                data=ui_objects.ErrorResponseData(message="data_failed_validation"),
            )

        obj = get_object_or_404(ban_data.get_model().objects.filter(), id=ban_data.object_id)
        try:
            obj.set_ban(ban_data.is_banned, self.request.user)
        except exceptions.BanException as e:
            return KirovyResponse(
                status=status.HTTP_400_BAD_REQUEST,
                data=ui_objects.ErrorResponseData(message=str(e)),
            )

        return KirovyResponse(
            status=status.HTTP_200_OK,
            data=ui_objects.ResultResponseData(message="", result=ban_data.model_dump()),
        )

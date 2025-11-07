import pydantic
from rest_framework import status
from rest_framework.generics import get_object_or_404
from rest_framework.views import APIView

from kirovy import permissions, exceptions
from kirovy.exceptions.view_exceptions import KirovyValidationError
from kirovy.models.moderabile import Moderabile
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
            raise KirovyValidationError("No data")
        try:
            ban_data = ui_objects.BanData(**request.data)
        except pydantic.ValidationError:
            raise KirovyValidationError("Ban object failed validation")

        obj: Moderabile = get_object_or_404(ban_data.django_model.objects.filter(), id=ban_data.object_id)

        try:
            if ban_data.is_banned:
                obj.ban(self.request.user, ban_reason=ban_data.note, ban_expires=ban_data.ban_expires)
            else:
                obj.unban(self.request.user, note=ban_data.note)
        except exceptions.BanException as e:
            raise KirovyValidationError(
                str(e),
            )

        return KirovyResponse(
            status=status.HTTP_200_OK,
            data=ui_objects.ResultResponseData(message="Updated ban status for object", result=ban_data.model_dump()),
        )

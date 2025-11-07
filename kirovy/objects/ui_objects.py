"""
Defines custom objects to be sent between the UI and backend.

Not necessary for endpoint that take one parameter in the Post, but still recommended.
"""

import enum
from functools import cached_property
from typing import TypedDict, NotRequired, List

import pydantic
from django.apps import apps
from django.views import View

from kirovy import typing as t
from kirovy.permissions import StaticPermission, IsStaff, CanUpload, IsAdmin
from kirovy.request import KirovyRequest

from kirovy.typing import DictStrAny
from kirovy.models.moderabile import Moderabile


class BanData(pydantic.BaseModel):
    """For ban post requests.

    - View: :class:`kirovy.views.admin_views.BanView`
    - URL: ``/admin/ban``
    """

    class Meta:
        class ObjectType(str, enum.Enum):
            USER = "user"
            MAP = "map"

        OBJECT_MODEL_MAP = {
            ObjectType.MAP: "CncMap",
            ObjectType.USER: "CncUser",
        }

    @cached_property
    def django_model(self) -> t.Type[Moderabile]:
        try:
            model: t.Type[Moderabile] = apps.get_model("kirovy", self.Meta.OBJECT_MODEL_MAP[self.object_type])
        except LookupError:
            raise ValueError(f"Model not found")
        return model

    object_type: Meta.ObjectType
    is_banned: bool
    note: str | None = None
    ban_expires: pydantic.FutureDate | None = None
    object_id: str


class PaginationMetadata(TypedDict):
    """Metadata returned to the UI with paginated responses."""

    offset: int
    limit: NotRequired[int]
    remaining_count: NotRequired[int]


class BaseResponseData(TypedDict):
    """Basic response from Kirovy to the UI.

    Mostly used for post requests where the only response is some kind of success or failure message.
    """

    message: NotRequired[str]


class ListResponseData(BaseResponseData):
    """Kirovy response to the UI for ``list`` endpoints.

    e.g. listing all users.

    Pagination is not required but may be present.
    """

    results: List[DictStrAny]
    pagination_metadata: NotRequired[PaginationMetadata]


class ResultResponseData(BaseResponseData):
    """Basic response that returns a dictionary in addition to the message from ``BaseResponseData``.

    Mostly for endpoints that return object data to the UI. e.g. a ``create`` endpoint returning
    the object that was created.
    """

    result: DictStrAny


class ErrorResponseData(BaseResponseData):
    """Basic response that returns a dictionary of additional data related to an error."""

    code: str
    """attr: The same as ``code`` in :class:`rest_framework.exceptions.APIException`.

    This is a string for the UI. The human-readable error should go in ``message``.
    """

    additional: NotRequired[DictStrAny]
    """attr: Arbitrary data to return to the UI to help user's understand what they did wrong."""


class UiPermissions:
    """A class to hold permissions to send to the UI.

    Used for rendering buttons and such. Does not control anything in Kirovy itself.
    The actual backend views will use the regular
    [DRF permission workflow](https://www.django-rest-framework.org/api-guide/permissions/).
    """

    SHOW_STAFF_CONTROLS: t.Final[str] = "show_staff_controls"
    SHOW_UPLOAD_BUTTON: t.Final[str] = "show_upload_button"
    SHOW_ADMIN_CONTROLS: t.Final[str] = "show_admin_controls"

    static_permissions: t.Dict[t.UiPermissionName, StaticPermission] = {
        SHOW_STAFF_CONTROLS: IsStaff,
        SHOW_UPLOAD_BUTTON: CanUpload,
        SHOW_ADMIN_CONTROLS: IsAdmin,
    }
    """attr: The dictionary structure that gets returned to the UI.

    The UI will see e.g.:

        .. code-block:: json

            {
                "show_staff_controls": true,
                "show_upload_button": true,
                "show_admin_controls": false,
            }
    """

    @classmethod
    def render_static(cls, request: KirovyRequest, view: View) -> t.Dict[t.UiPermissionName, bool]:
        """Create a dictionary of permissions to tell the UI what to display.

        This **DOES NOT** control the backend permissions, it's just to help the UI know which buttons to show.
        If someone finds a way to show the buttons anyway, then kirovy will still block the request with the actual
        permission checks on the views.

        :param request:
            The request for the API call.
        :param view:
            The view instance itself.
        :return:
            The dictionary of permission names with a bool representing if the user has that permission.
            e.g.:

            .. code-block:: json

                {
                    "show_staff_controls": true,
                    "show_upload_button": true,
                    "show_admin_controls": false,
                }
        """
        ui_permissions: t.Dict[t.UiPermissionName, bool] = {}
        for ui_name, permission_cls in cls.static_permissions.items():
            ui_permissions[ui_name] = permission_cls().has_permission(request, view)

        return ui_permissions

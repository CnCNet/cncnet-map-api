from kirovy import typing as t
from django.db import models
from django.views import View
from rest_framework import permissions

from kirovy.models import cnc_user
from kirovy.models.cnc_base_model import CncNetBaseModel
from kirovy.request import KirovyRequest

_C = t.TypeVar("_C", bound=t.Callable)


class StaticPermission(t.Protocol[_C]):
    """Static permissions are permissions that just have a ``has_permission`` method.

    Object permissions have ``has_object_permission`` and are specific to an object.
    """

    __call__: _C  # Make callable so type checker doesn't whine about calling the classes.

    def has_permission(self, request: KirovyRequest, view: View) -> bool:
        ...


class CanUpload(permissions.IsAuthenticated):
    """
    Only users with a validated email, or special roles, can upload.
    """

    def has_permission(self, request: KirovyRequest, view: View) -> bool:
        if not super().has_permission(request, view):
            return False
        return request.user.can_upload or request.user.is_staff


class ReadOnly(permissions.BasePermission):
    """
    Anyone can call get on endpoints with this permission.
    """

    READ_METHODS = [
        "get",
    ]

    def has_permission(self, request: KirovyRequest, view: View) -> bool:
        return request.method.lower() in self.READ_METHODS


class CanEdit(CanUpload):
    """Check editing permissions.

    Users can edit their own uploads.
    Staff can edit all uploads.

    Users that have been banned cannot edit anymore. Just in case they feel like defacing content in retaliation.

    Checking if the **user** is banned happens in :func:`kirovy.permissions.CanUpload.has_permission` which runs
    *before* ``has_object_permissions``. Checking if the **object** is banned is done via checking for an `
    `is_banned`` attribute.
    [DRF permission docs](https://www.django-rest-framework.org/api-guide/permissions/#custom-permissions).

    The edit check flow for users: ``Is the user banned -> Is the object banned -> Does the user own the object``
    """

    def has_object_permission(
        self, request: KirovyRequest, view: View, obj: models.Model
    ) -> bool:
        if request.user.is_staff:
            return True

        # Check if this model type is owned by users.
        if isinstance(obj, cnc_user.CncNetUserOwnedModel):
            obj_is_banned = hasattr(obj, "is_banned") and obj.is_banned
            return request.user == obj.cnc_user and not obj_is_banned

        return False


class CanDelete(permissions.IsAdminUser):
    """Check if a user can delete an object."""

    def has_object_permission(
        self, request: KirovyRequest, view: View, obj: models.Model
    ) -> bool:
        # for now, only staff can delete.
        return request.user.is_staff


class IsStaff(permissions.IsAuthenticated):
    """Moderators, admins, and gods.

    Use this instead of the DRF ``IsAdminUser``.
    """

    def has_permission(self, request: KirovyRequest, view: View) -> bool:
        return super().has_permission(request, view) and request.user.is_staff


class IsAdmin(permissions.IsAuthenticated):
    """Admins and gods."""

    def has_permission(self, request: KirovyRequest, view: View) -> bool:

        return super().has_permission(request, view) and request.user.is_admin


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

    @classmethod
    def render_static(
        cls, request: KirovyRequest, view: View
    ) -> t.Dict[t.UiPermissionName, bool]:
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
        """
        ui_permissions: t.Dict[t.UiPermissionName, bool] = {}
        for ui_name, permission_cls in cls.static_permissions.items():
            ui_permissions[ui_name] = permission_cls().has_permission(request, view)

        return ui_permissions

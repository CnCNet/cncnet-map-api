from django.db import models
from django.views import View
from rest_framework import permissions

from kirovy.models import cnc_user
from kirovy.models.cnc_base_model import CncNetBaseModel
from kirovy.request import KirovyRequest


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
    """
    Users can edit their own uploads.
    Staff can edit user uploads.

    Users that have been banned cannot edit anymore. Just in case they feel like defacing content in retaliation.
    """

    def has_object_permission(
        self, request: KirovyRequest, view: View, obj: models.Model
    ) -> bool:
        if request.user.is_staff:
            return True

        # Check if this model type is owned by users.
        if isinstance(obj, cnc_user.CncNetUserOwnedModel):
            return request.user == obj.cnc_user

        return False


class CanDelete(permissions.IsAdminUser):
    """For now, only staff can delete things."""

    def has_object_permission(
        self, request: KirovyRequest, view: View, obj: models.Model
    ) -> bool:
        return request.user.is_staff

from rest_framework import serializers

from kirovy.models import CncUser
from kirovy import typing as t
from kirovy.request import KirovyRequest


class KirovySerializer(serializers.Serializer):
    """Base serializer for Kirovy models."""

    id = serializers.UUIDField(read_only=True)
    created = serializers.DateTimeField(read_only=True)
    modified = serializers.DateTimeField(read_only=True)

    last_modified_by_id = serializers.PrimaryKeyRelatedField(
        source="last_modified_by",
        queryset=CncUser.objects.all(),
        pk_field=serializers.UUIDField(),
    )

    class Meta:
        exclude = ["last_modified_by"]
        fields = "__all__"

    def get_fields(self):
        """Get fields based on permission level.

        Removes admin-only fields for non-admin requests. Will always remove the fields if the serializer doesn't
        have context.
        """
        fields = super().get_fields()
        request: t.Optional[KirovyRequest] = self.context.get("request")
        if not all([request, request.user.is_authenticated, request.user.is_staff]):
            fields.pop("last_modified_by_id", None)
        return fields


class CncNetUserOwnedModelSerializer(KirovySerializer):
    """Base serializer for any model that mixes in :class:`~kirovy.models.cnc_user.CncNetUserOwnedModel`"""

    cnc_user_id = serializers.PrimaryKeyRelatedField(
        source="cnc_user",
        queryset=CncUser.objects.all(),
        pk_field=serializers.UUIDField(),
    )

    class Meta:
        exclude = ["cnc_user"]
        fields = "__all__"

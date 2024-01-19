from rest_framework import serializers

from kirovy.models import CncUser
from kirovy import typing as t


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

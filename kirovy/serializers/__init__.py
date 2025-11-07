from rest_framework import serializers

from kirovy.constants import api_codes
from kirovy.exceptions.view_exceptions import KirovyValidationError
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
        editable_fields: t.ClassVar[set[str]] = set()

    def get_fields(self):
        """Get fields based on permission level.

        Removes admin-only fields for non-admin requests. Will always remove the fields if the serializer doesn't
        have context.
        """
        fields = super().get_fields()
        request: t.Optional[KirovyRequest] = self.context.get("request")
        if not (request and request.user.is_authenticated and request.user.is_staff):
            fields.pop("last_modified_by_id", None)
        return fields

    def to_internal_value(self, data: dict) -> dict:
        """Convert the raw request data into data that can be used in a django model.

        Enforces editable fields from :attr:`~kirovy.serializers.KirovySerializer.Meta.editable.fields`.
        """
        data = super().to_internal_value(data)
        # Enforce editable fields.
        if self.instance and hasattr(self.Meta, "editable_fields") and self.Meta.editable_fields:
            updated_keys = set(data.keys())
            if attempted_disallowed_updates := list(updated_keys - self.Meta.editable_fields):
                # `to_internal_value` converts `data["thing_id"]` to `data["thing"]`.
                # If you're getting this error on e.g. `thing_id`, but you specified `thing_id` as editable,
                # then you need to change the name in `editable_fields` to `thing`.
                raise KirovyValidationError(
                    "Requested fields cannot be edited after creation",
                    api_codes.GenericApiCodes.CANNOT_UPDATE_FIELD,
                    additional={
                        "can_update": list(self.Meta.editable_fields),
                        "attempted": attempted_disallowed_updates,
                    },
                )
        return data


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

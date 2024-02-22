from kirovy.serializers import KirovySerializer, CncNetUserOwnedModelSerializer
from rest_framework import serializers
from kirovy.models import cnc_map, CncGame, CncUser, MapCategory


class MapCategorySerializer(KirovySerializer):
    name = serializers.CharField(min_length=3)
    slug = serializers.CharField(min_length=2, read_only=True)

    def create(self, validated_data: dict) -> MapCategory:
        return MapCategory.objects.create(**validated_data)

    def update(self, instance: MapCategory, validated_data: dict) -> MapCategory:
        instance.name = validated_data.get("name", instance.name)
        instance.last_modified_by_id = validated_data.get("last_modified_by_id", None)
        # slug is automatically set in ``.save``.
        instance.save(update_fields=["name", "slug", "last_modified_by_id"])
        instance.refresh_from_db()
        return instance


class CncMapBaseSerializer(CncNetUserOwnedModelSerializer):
    map_name = serializers.CharField(
        required=True,
        allow_null=False,
        allow_blank=False,
        trim_whitespace=True,
        min_length=3,
    )
    description = serializers.CharField(
        required=True,
        allow_null=False,
        allow_blank=False,
        trim_whitespace=True,
        min_length=10,
    )
    cnc_game_id = serializers.PrimaryKeyRelatedField(
        source="cnc_game",
        queryset=CncGame.objects.all(),
        pk_field=serializers.UUIDField(),
    )
    category_ids = serializers.PrimaryKeyRelatedField(
        source="categories",
        queryset=cnc_map.MapCategory.objects.all(),
        pk_field=serializers.UUIDField(),
        many=True,
        allow_null=False,
        allow_empty=False,
    )
    is_published = serializers.BooleanField(
        default=False,
    )

    # This field is only set via client uploads.
    is_temporary = serializers.BooleanField(read_only=True)

    # These fields are only available for admins to set.
    is_reviewed = serializers.BooleanField(read_only=True)
    is_banned = serializers.BooleanField(read_only=True)

    # Legacy maps will be added via the legacy serializer.
    is_legacy = serializers.BooleanField(read_only=True)
    legacy_upload_date = serializers.DateTimeField(
        read_only=True,
    )

    class Meta:
        model = cnc_map.CncMap
        exclude = ["cnc_game", "categories"]
        fields = "__all__"

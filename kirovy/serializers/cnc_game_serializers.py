from rest_framework import serializers
from kirovy import typing as t
from kirovy.models import cnc_game
from kirovy.serializers import KirovySerializer


class CncFileExtensionSerializer(KirovySerializer):
    extension = serializers.CharField(
        max_length=32,
        allow_blank=False,
    )

    about = serializers.CharField(
        max_length=2048,
        allow_null=True,
        allow_blank=False,
        required=False,
    )

    extension_type = serializers.ChoiceField(
        choices=cnc_game.CncFileExtension.ExtensionTypes.choices,
    )

    def create(self, validated_data: dict[str, t.Any]) -> cnc_game.CncFileExtension:
        return cnc_game.CncFileExtension.objects.create(**validated_data)

    def update(
        self, instance: cnc_game.CncFileExtension, validated_data: dict[str, t.Any]
    ) -> cnc_game.CncFileExtension:
        # For now, don't allow editing the extension. These likely shouldn't ever need to be updated.
        # instance.extension = validated_data.get("extension", instance.extension)
        instance.about = validated_data.get("about", instance.about)
        instance.extension_type = validated_data.get("extension_type", instance.extension_type)
        instance.save(update_fields=["about", "extension_type"])
        instance.refresh_from_db()
        return instance

    class Meta:
        model = cnc_game.CncFileExtension
        exclude = ["last_modified_by"]
        fields = "__all__"


class CncGameSerializer(KirovySerializer):
    slug = serializers.CharField(read_only=True, allow_null=False, allow_blank=False)
    full_name = serializers.CharField(allow_null=False, allow_blank=False)
    is_visible = serializers.BooleanField(allow_null=False, default=True)
    allow_public_uploads = serializers.BooleanField(allow_null=False, default=False)
    compatible_with_parent_maps = serializers.BooleanField(allow_null=False, default=False)
    is_mod = serializers.BooleanField(allow_null=False, default=False)
    allowed_extension_ids = serializers.PrimaryKeyRelatedField(
        source="allowed_extensions",
        pk_field=serializers.UUIDField(),
        many=True,
        read_only=True,  # Set these manually using the ORM.
    )

    parent_game_id = serializers.PrimaryKeyRelatedField(
        source="parent_game",
        queryset=cnc_game.CncGame.objects.filter(is_visible=True),
        pk_field=serializers.UUIDField(),
        many=False,
        allow_null=True,
        allow_empty=False,
        default=None,
    )

    class Meta:
        model = cnc_game.CncGame
        # We return the ID instead of the whole object.
        exclude = ["parent_game", "allowed_extensions"]
        fields = "__all__"

    def create(self, validated_data: t.DictStrAny) -> cnc_game.CncGame:
        instance = cnc_game.CncGame(**validated_data)
        instance.save()
        return instance

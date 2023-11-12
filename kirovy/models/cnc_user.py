import uuid

from django.contrib.auth.models import AbstractBaseUser
from django.db import models
from django.utils.translation import gettext as _
from kirovy import typing as t

from kirovy.objects import CncnetUserInfo

__all__ = ["CncUser"]


class CncUser(AbstractBaseUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cncnet_id = models.IntegerField(
        unique=True,
        editable=False,
        help_text=_("The user ID from the CNCNet ladder API."),
    )

    username = models.CharField(
        null=True, help_text=_("The name from the CNCNet ladder API.")
    )
    """:attr: The username for debugging purposes. Don't rely on this field for much else."""

    verified_map_uploader = models.BooleanField(null=False, default=False)
    """:attr: This user is a map uploader verified by cncnet staff."""

    verified_email = models.BooleanField(null=False, default=False)

    group = models.CharField(
        null=False, help_text=_("The user group from the CNCNet ladder API.")
    )

    USERNAME_FIELD = "cncnet_id"

    def save(self, *args, **kwargs):
        self.set_unusable_password()
        super().save(*args, **kwargs)

    @property
    def can_upload(self) -> bool:
        return self.verified_map_uploader or self.verified_email

    @staticmethod
    def create_or_update_from_cncnet(user_dto: CncnetUserInfo) -> "CncUser":
        map_user: t.Optional[CncUser] = CncUser.objects.filter(
            cncnet_id=user_dto.id
        ).first()
        if not map_user:
            map_user = CncUser.objects.create(
                cncnet_id=user_dto.id,
                username=user_dto.name,
                verified_email=user_dto.email_verified,
                verified_map_uploader=False,
                group=user_dto.group,
            )
            map_user.save()
        else:
            map_user.verified_email = user_dto.email_verified
            map_user.username = user_dto.name
            map_user.group = user_dto.group
            map_user.save(update_fields=["verified_email", "username", "group"])

        return map_user

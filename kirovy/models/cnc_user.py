import uuid

from django.contrib.auth.models import AbstractBaseUser
from django.db import models
from django.utils.translation import gettext as _
from kirovy import typing as t

from kirovy.objects import CncnetUserInfo

__all__ = ["CncUser"]


class CncUser(AbstractBaseUser):
    STAFF_GROUPS: t.List[str] = []
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

    is_banned = models.BooleanField(
        default=False, help_text="If true, user was banned for some reason."
    )
    ban_reason = models.CharField(
        default=None, null=True, help_text="If banned, the reason the user was banned."
    )
    ban_date = models.DateTimeField(
        default=None, null=True, help_text="If banned, when the user was banned."
    )
    ban_expires = models.DateTimeField(
        default=None,
        null=True,
        help_text="If banned, when the ban expires, if temporary.",
    )
    ban_count = models.IntegerField(
        default=0, help_text="How many times this user has been banned."
    )

    USERNAME_FIELD = "cncnet_id"
    """:attr:
        This attribute controls which field Django REST Framework uses as the username field. Values must be unique.
    """

    def save(self, *args, **kwargs):
        self.set_unusable_password()
        super().save(*args, **kwargs)

    @property
    def can_upload(self) -> bool:
        """Check if a user can upload and is not banned.

        This should be checked before allowing editing too.

        :return:
            True if user can upload maps / mixes / big, or edit their existing uploads.
        """
        self.refresh_from_db(
            fields=["verified_map_uploader", "verified_email", "is_banned"]
        )
        can_upload = self.verified_map_uploader or self.verified_email or self.is_staff
        return can_upload and not self.is_banned

    @property
    def is_staff(self) -> bool:
        self.refresh_from_db(fields=["group"])
        return self.group in self.STAFF_GROUPS

    @staticmethod
    def create_or_update_from_cncnet(user_dto: CncnetUserInfo) -> "CncUser":
        """Create or Update a user object, based on the user DTO, from the CnCNet ladder API.

        If we already have the user in Kirovy's database, then we update the fields.

        This is called for every request via :func:`kirovy.authentication.CncNetAuthentication.authenticate`.

        :param user_dto:
            The user from the CnCNet ladder API.
        :return:
            The user object in Kirovy's database, updated with the data from CnCNet.
        """
        kirovy_user: t.Optional[CncUser] = CncUser.objects.filter(
            cncnet_id=user_dto.id
        ).first()
        if not kirovy_user:
            kirovy_user = CncUser.objects.create(
                cncnet_id=user_dto.id,
                username=user_dto.name,
                verified_email=user_dto.email_verified,
                verified_map_uploader=False,
                group=user_dto.group,
            )
            kirovy_user.save()
        else:
            kirovy_user.verified_email = user_dto.email_verified
            kirovy_user.username = user_dto.name
            kirovy_user.group = user_dto.group
            kirovy_user.save(update_fields=["verified_email", "username", "group"])

        return kirovy_user


class CncNetUserOwnedModel(models.Model):
    """A mixin model for any models that will be owned or modified by a user."""

    cnc_user = models.ForeignKey(CncUser, on_delete=models.PROTECT, null=True)
    """:attr: The user that owns this object, if it has an owner."""

    last_modified_by = models.ForeignKey(
        CncUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name="modified_%(class)s_set",
    )
    """:attr: The last user to modify this entry, if applicable."""

    class Meta:
        abstract = True

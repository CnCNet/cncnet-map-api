import datetime

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.html import escape

from kirovy import typing as t

if t.TYPE_CHECKING:
    from kirovy.models import CncUser


class Moderabile(models.Model):
    class Meta:
        abstract = True

    moderated_by = models.ForeignKey(
        "CncUser",
        on_delete=models.SET_NULL,
        null=True,
        related_name="moderated_%(class)ss_set",
        help_text="The most recent moderator who most recently modified this object",
    )
    is_banned = models.BooleanField(default=False, help_text="If true, object was banned for some reason.")
    ban_reason = models.CharField(default=None, null=True, help_text="If banned, the reason the object was banned.")
    ban_date = models.DateTimeField(default=None, null=True, help_text="If banned, when the object was banned.")
    ban_expires = models.DateField(
        default=None,
        null=True,
        help_text="If banned, when the ban expires, if temporary.",
    )
    ban_count = models.IntegerField(default=0, help_text="How many times this user has been banned.")
    moderator_notes = models.TextField(null=True, help_text="Notes on moderator actions.")

    def ban(
        self,
        moderated_by: "CncUser",
        *,
        ban_reason: str | None = None,
        ban_expires: datetime.date | None = None,
    ) -> None:
        """Ban an object.

        :param moderated_by:
            The moderator who performed the moderation action.
        :param ban_reason:
            The reason for the ban.
        :param ban_expires:
            When the ban will automatically expire.
        :return:
            Nothing. The instance will be updated.
        """
        self.refresh_from_db()
        self.check_is_bannable()

        self.moderated_by = moderated_by
        self.is_banned = True
        self.ban_reason = ban_reason or "Not Specified"
        self.ban_date = datetime.datetime.now(datetime.timezone.utc)
        self.ban_expires = ban_expires
        self.ban_count += 1

        moderator_note = self._moderator_note_line("Banned", self.ban_date, self.ban_reason, self.moderated_by)
        self.moderator_notes = (self.moderator_notes or "") + moderator_note

        self.save(
            update_fields=[
                "moderated_by",
                "is_banned",
                "ban_reason",
                "ban_date",
                "ban_expires",
                "ban_count",
                "moderator_notes",
            ]
        )

    def unban(
        self,
        moderated_by: "CncUser",
        *,
        note: str = "Not Specified",
    ):
        """Unban an object.

        :param moderated_by:
            The moderator who is unbanning the object.
        :param note:
            An optional unban note.
        :return:
        """
        self.refresh_from_db()
        self.check_is_bannable()
        self.moderated_by = moderated_by
        self.is_banned = False
        self.ban_reason = None
        self.ban_date = None
        self.ban_expires = None

        moderator_note = self._moderator_note_line(
            "Unbanned", datetime.datetime.now(datetime.timezone.utc), note, moderated_by
        )
        self.moderator_notes = (self.moderator_notes or "") + moderator_note

        self.save(
            update_fields=["moderated_by", "is_banned", "ban_reason", "ban_date", "ban_expires", "moderator_notes"]
        )

    @staticmethod
    def _moderator_note_line(
        action: str, action_date: datetime.datetime, action_reason: str, moderated_by: "CncUser"
    ) -> str:
        action = escape(action)
        action_reason = escape(action_reason)
        return f"- {action} [{action_date.date().isoformat()}]: {action_reason} -- by: '{moderated_by.username}'\n"

    def check_is_bannable(self) -> None:
        """Check if this instance is eligible to be banned.

        Used for things like disallowing the banning of legacy maps.

        Override for your model.

        :raises kirovy.exceptions.BanException:
            Raised if we should block this item from being banned.
        """
        return None

import uuid

from django.db import models

__all__ = ["CncNetBaseModel"]


class CncNetBaseModel(models.Model):
    """Base model for all cnc net models to inherit from."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_index=True)

    created = models.DateTimeField(auto_now_add=True, null=True)
    modified = models.DateTimeField(auto_now=True, null=True)

    last_modified_by = models.ForeignKey(
        "CncUser",
        on_delete=models.SET_NULL,
        null=True,
        related_name="modified_%(class)s_set",
        db_index=True,
    )
    """:attr: The last user to modify this entry, if applicable."""

    class Meta:
        abstract = True

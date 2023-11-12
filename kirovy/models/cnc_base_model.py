import uuid

from django.db import models

__all__ = ["CncNetBaseModel"]


class CncNetBaseModel(models.Model):
    """Base model for all cnc net models to inherit from."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True

from django.db import models
from application.models import file_base


class CncMapFile(file_base.CncNetFileBaseModel):
    UPLOAD_TO = "maps"
    ALLOWED_EXTENSIONS = ["map", "yrm", "mpr", "mmx"]

    map_name = models.CharField(max_length=1024)

    width = models.IntegerField()
    height = models.IntegerField()

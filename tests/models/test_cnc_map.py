import pytest
from django.core import validators

from application.models.cnc_map import CncMapFile


@pytest.mark.parametrize("extension", ["pdf", "mix", "ini", "exe"])
def test_cnc_map_create_model(extension):
    with pytest.raises(validators.ValidationError) as exc_info:
        CncMapFile(file_extension=extension)
    assert extension in str(exc_info.value)

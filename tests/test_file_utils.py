import pytest

from kirovy.utils import file_utils


def test_byte_sized_from_bytes():
    """Test the easiest case of converting bytes to other magnitudes."""
    total_byte = 1002456789290
    byte_sized = file_utils.ByteSized(byte=total_byte)
    assert byte_sized.tera == 1
    assert byte_sized.giga == 2
    assert byte_sized.mega == 456
    assert byte_sized.kilo == 789
    assert byte_sized.byte == 290

    assert byte_sized.total_bytes == total_byte
    assert str(byte_sized) == "1TB, 2GB, 456MB, 789KB, 290B"


def test_byte_sized_mix_and_match():
    """Test that combinations of args add up correctly, including carrying over when > 1000."""
    total_byte = 3003457790290
    # The 2002 GB should roll over into 3TB 2GB
    # The 1456 MB should roll over into 3GB 456MB
    # 1789 KB should roll over into 457MB 789KB
    # 1290 B should roll over into 790KB 290B
    byte_sized = file_utils.ByteSized(1290, kilo=1789, mega=1456, giga=2002, tera=1)
    assert byte_sized.tera == 3
    assert byte_sized.giga == 3
    assert byte_sized.mega == 457
    assert byte_sized.kilo == 790
    assert byte_sized.byte == 290

    assert byte_sized.total_bytes == total_byte
    assert str(byte_sized) == "3TB, 3GB, 457MB, 790KB, 290B"


def test_byte_sized_print_missing():
    """Test that magnitudes that are zero don't get included in the string."""
    # The 100MB should roll over into 3GB, and MB should be excluded from the string.
    byte_sized = file_utils.ByteSized(23, kilo=117, mega=1000, giga=2, tera=0)
    assert str(byte_sized) == "3GB, 117KB, 23B"

    assert str(file_utils.ByteSized(mega=25)) == "25MB"


@pytest.mark.parametrize("arg_to_negative", ["tera", "giga", "mega", "kilo", "byte"])
def test_byte_sized_lt_zero(arg_to_negative: str):
    """Test that we error out on args being negative."""
    args = {key: 1 for key in ["tera", "giga", "mega", "kilo", "byte"]}
    args[arg_to_negative] = -1
    with pytest.raises(AttributeError):
        file_utils.ByteSized(**args)


def test_byte_sized__operators():
    assert file_utils.ByteSized(1) < file_utils.ByteSized(2)
    assert file_utils.ByteSized(2) > file_utils.ByteSized(1)

    assert file_utils.ByteSized(1) == file_utils.ByteSized(1)
    assert file_utils.ByteSized(1) != file_utils.ByteSized(2)

    assert file_utils.ByteSized(1) >= file_utils.ByteSized(1)
    assert file_utils.ByteSized(2) >= file_utils.ByteSized(1)

    assert file_utils.ByteSized(1) <= file_utils.ByteSized(1)
    assert file_utils.ByteSized(1) <= file_utils.ByteSized(2)

import base64
from PIL import BmpImagePlugin, Image
import configparser
import enum
import io

import lzo

from django.conf import settings
from django.core.files import File
from kirovy import typing as t, exceptions

from django.utils.translation import gettext as _


class MapSections(enum.StrEnum):
    PREVIEW_PACK = "PreviewPack"
    PREVIEW = "Preview"
    HEADER = "Header"
    BASIC = "Basic"
    MAP = "Map"
    OVERLAY_DATA = "OverlayDataPack"
    OVERLAY_PACK = "OverlayPack"
    SPECIAL_FLAGS = "SpecialFlags"
    DIGEST = "Digest"


class MapParserService:
    file: File
    parser: configparser.ConfigParser

    required_sections: t.Set[MapSections] = {
        MapSections.HEADER.value,
        MapSections.BASIC.value,
        MapSections.MAP.value,
        MapSections.OVERLAY_PACK.value,
        MapSections.OVERLAY_DATA.value,
        MapSections.SPECIAL_FLAGS.value,
        MapSections.DIGEST.value,
    }

    class ErrorMsg(enum.StrEnum):
        NO_BINARY = _("Binary files not allowed.")
        CORRUPT_MAP = _("Could not parse map file.")
        MISSING_INI = _("Missing necessary INI sections.")

    def __init__(self, uploaded_file: File):
        self.validate_file_type(uploaded_file)
        self.file = uploaded_file
        self.parser = configparser.ConfigParser()
        self._parse_file()

    def _parse_file(self) -> None:
        """Parse ``self.file`` with ``self.parser``.

        :return:
            Nothing, but :attr:`~kirovy.services.MapParserService.parser` will be modified.
        """
        if self.file.closed:
            self.file.open("r")

        try:
            self.parser.read_file(self.file)
        except configparser.ParsingError as e:
            raise exceptions.InvalidMapFile(
                self.ErrorMsg.CORRUPT_MAP,
                code=self.ErrorMsg.CORRUPT_MAP.name,
                params={"e": e},
            )

        sections: t.Set[str] = set(self.parser.sections())
        missing_sections = self.required_sections - sections
        if missing_sections:
            raise exceptions.InvalidMapFile(
                self.ErrorMsg.MISSING_INI,
                code=self.ErrorMsg.MISSING_INI.name,
                params={"missing": missing_sections},
            )

    @property
    def python_file(self) -> t.IO:
        """Get the raw python file instead of the django one.

        :return:
            The raw file in ``self.file``
        """
        return self.file.file

    def validate_file_type(self, uploaded_file: File) -> None:
        """Validate that the map file can be parsed as a map.

        :param uploaded_file:
            A supposed map file.
        :raise exceptions.InvalidMimeType:
            Raised if file is binary.
        """
        if self.is_binary(uploaded_file):
            raise exceptions.InvalidMimeType(self.ErrorMsg.NO_BINARY)

    @classmethod
    def is_binary(cls, uploaded_file: File) -> bool:
        """Check if a file is a binary file.

        :param uploaded_file:
            A supposed map file.
        :return:
            True if the file is binary.
        """
        return not cls.is_text(uploaded_file)

    @classmethod
    def is_text(cls, uploaded_file: File) -> bool:
        """Check if a file is readable as text.

        :param uploaded_file:
            The supposed map file
        :return:
            True if readable as text.
        """
        try:
            with uploaded_file.open("tr") as check_file:
                check_file.read()
                return True
        except UnicodeDecodeError:
            return False

    def extract_preview(self):
        if not self.parser.has_section(MapSections.PREVIEW_PACK):
            return b""

        size = [
            int(x)
            for x in self.parser.get(MapSections.PREVIEW, "Size", fallback="").split(
                ","
            )
        ]
        if len(size) != 4:
            return b""

        width, height = size[2], size[3]
        decompress = width * height * 3

        preview_b64 = "".join(self.parser[MapSections.PREVIEW_PACK].values())
        preview_bytes = base64.b64decode(preview_b64)
        # Each pixel block is a header, and the block data.
        # byte[0] and [1] specify the compressed block size
        # byte[2] and [3] specify the size of the block when uncompressed.
        # The uncompressed block is Blue, green, red 8, 8, 8 bit (24bits). Each bit defines the color from 0-255.

        byte_destination = io.BytesIO()
        read_bytes = written_bytes = 0
        while True:
            if read_bytes >= decompress:
                break
            size_compressed = int.from_bytes(
                preview_bytes[read_bytes : read_bytes + 2],
                byteorder="little",
                signed=False,
            )
            read_bytes += 2
            size_uncompressed = int.from_bytes(
                preview_bytes[read_bytes : read_bytes + 2],
                byteorder="little",
                signed=False,
            )
            read_bytes += 2

            if size_compressed == 0 or size_uncompressed == 0:
                break

            compressed_size_exceeds_source = read_bytes + size_compressed > len(
                preview_bytes
            )
            uncompressed_size_exceeds_destination = (
                written_bytes + size_uncompressed > decompress
            )
            if compressed_size_exceeds_source or uncompressed_size_exceeds_destination:
                raise Exception(
                    "Preview data does not match preview size or the data is corrupted, unable to extract preview."
                )

            block = preview_bytes[read_bytes : read_bytes + size_compressed]
            uncompressed_block = lzo.decompress(block, False, size_uncompressed)
            byte_destination.write(uncompressed_block)

            read_bytes += size_compressed
            written_bytes += size_uncompressed

        byte_destination.seek(0)
        # test = byte_destination.read()
        # filename = (
        #     settings.STATICFILES_DIRS[0] / "test.bmp"
        # )  # I assume you have a way of picking unique filenames
        # img = Image.open(byte_destination, "r", formats=["BMP"])
        # with open(filename, 'wb') as f:
        #     f.write(byte_destination.read())

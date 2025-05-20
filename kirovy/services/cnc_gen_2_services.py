import base64
import logging
from functools import cached_property

import magic
from PIL import Image
import configparser
import enum
import io

import lzo

from django.core.files import File
from django.core.files.uploadedfile import UploadedFile
from rest_framework import status

from kirovy import typing as t, exceptions

from django.utils.translation import gettext as _


LOGGER = logging.getLogger("MapParserService")


class CncGen2MapSections(enum.StrEnum):
    # Todo: move to API codes.
    PREVIEW_PACK = "PreviewPack"
    PREVIEW = "Preview"
    HEADER = "Header"
    BASIC = "Basic"
    MAP = "Map"
    OVERLAY_DATA = "OverlayDataPack"
    OVERLAY_PACK = "OverlayPack"
    SPECIAL_FLAGS = "SpecialFlags"
    DIGEST = "Digest"


class ParseErrorMsg(enum.StrEnum):
    NO_BINARY = _("Binary files not allowed.")
    CORRUPT_MAP = _("Could not parse map file.")
    MISSING_INI = _("Missing necessary INI sections.")


class MapConfigParser(configparser.ConfigParser):
    """Config parser with some helpers."""

    NAME_NOT_FOUND: str = "Map name not found in file"

    @classmethod
    def from_file(cls, file: File) -> "MapConfigParser":
        parser = cls()
        parser.read_django_file(file)
        return parser

    def read_django_file(self, file: File):
        if file.closed:
            file.open("r")
        file.seek(0)
        try:
            # We can't use ConfigParser.read_file because parser expects the file to be read as a string,
            # but django uploaded files are read as bytes. So we need to convert to string first.
            # If `decode` is crashing in a test, make sure your test file is read in read-mode "rb".
            self.read_string(file.read().decode(errors="ignore"))
        except configparser.ParsingError as e:
            raise exceptions.InvalidMapFile(
                ParseErrorMsg.CORRUPT_MAP,
                code=ParseErrorMsg.CORRUPT_MAP.name,
                params={"e": e},
            )

    def optionxform(self, optionstr: str) -> str:
        """Overwrite the base class to prevent lower-casing keys."""
        return optionstr

    @cached_property
    def categories(self) -> t.List[str]:
        """Get the map categories from a map file.

        :return:
            A list of lower cased game mode strings in a map file.
            Map game modes are stored in :class:`kirovy.models.cnc_map.MapCategory`.
            These strings are not to be trusted, and are not guaranteed to exist in the map database.
            They are simply here to help autopopulate game modes on initial upload.
        """
        categories = self.get(CncGen2MapSections.BASIC, "GameMode", fallback="")
        return list(map(str.lower, categories.split(","))) if categories else []

    @cached_property
    def map_name(self) -> str:
        """Get the map name from the map file.

        The map name is set in Final Alert / World Altering Editor and is different from the filename.

        :return:
            The map name or a string saying that the map wasn't found.
        """
        return self.get(CncGen2MapSections.BASIC, "Name", fallback=_(self.NAME_NOT_FOUND))


class CncGen2MapParser:
    """Map parser for generation 2 Westwood C&C games.

    Built for Red Alert 2, but should handle Tiberian Sun too.
    Gen 2 maps are just ``ini`` files saves as a ``.map``, ``.yrm``, etc.

    Parses maps, validates them, and extracts previews if necessary.
    """

    file: UploadedFile
    """:attr: The uploaded file that we're parsing."""
    ini: MapConfigParser
    """:attr: The parser object where the ini will be parsed into."""

    required_sections: t.Set[str] = {
        CncGen2MapSections.HEADER.value,
        CncGen2MapSections.BASIC.value,
        CncGen2MapSections.MAP.value,
        CncGen2MapSections.OVERLAY_PACK.value,
        CncGen2MapSections.OVERLAY_DATA.value,
        CncGen2MapSections.SPECIAL_FLAGS.value,
        CncGen2MapSections.DIGEST.value,
    }

    def __init__(self, uploaded_file: UploadedFile | File):
        self.validate_file_type(uploaded_file)
        self.file = uploaded_file
        self.ini = MapConfigParser()
        self._parse_file()

    def _parse_file(self) -> None:
        """Parse ``self.file`` with ``self.parser``.

        2d C&C game maps are just INI files. This function parses the INI into data structure.

        Raises exceptions for the map not being parsable, or the map missing necessary sections.

        :return:
            Nothing, but :attr:`~kirovy.services.MapParserService.parser` will be modified.
        """
        self.ini.read_django_file(self.file)
        sections: t.Set[str] = set(self.ini.sections())
        missing_sections = self.required_sections - sections
        if missing_sections:
            raise exceptions.InvalidMapFile(
                ParseErrorMsg.MISSING_INI,
                code=ParseErrorMsg.MISSING_INI.name,
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
            raise exceptions.InvalidMimeType(ParseErrorMsg.NO_BINARY)

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

        Also checks for ``ini`` files if the host OS supports them.

        :param uploaded_file:
            The supposed map file
        :return:
            True if readable as text.
        """
        magic_parser = magic.Magic(mime=True)
        uploaded_file.seek(0)
        mr_mime = magic_parser.from_buffer(uploaded_file.read())
        uploaded_file.seek(0)
        return mr_mime in {"text/plain", "application/x-wine-extension-ini"}

    def extract_preview(self) -> t.Optional[Image.Image]:
        """Extract the map preview if it exists.

        Map previews are bytes that have been LZO compressed, base64 encoded, then split
        amongst all the keys in the ``PreviewPack`` section of a map.

        Each pixel in the preview is stored as 3 bytes in the order: Blue, Green, Red.
        aka, ``BGR888``.

        The width and height of the bitmap is stored in ``Preview.Size``.

        The byte size of the decompressed preview is the ``width * height * 3``
        (3 bytes per pixel for the three colors.)

        To extract a preview:
            - Get the size from ``Preview.Size``
            - Join all the values in the INI section, ``PreviewPack``.
            - Base64 decode the joined string
            - LZO decompress the decoded bytes
            - Convert the bytes from ``BGR`` to ``RGB``
            - Shove the bytes into a bitmap image.

        :return:
            The preview image if we were able to extract it.
            Will be ``None`` if there was no preview.
        :raises exceptions.MapPreviewCorrupted:
            Raised by :func:`~kirovy.services.MapParserService._decompress_preview_from_base64`
            and should be bubbled up to the user.
        """
        if not self.ini.has_section(CncGen2MapSections.PREVIEW_PACK):
            LOGGER.debug("No preview pack")
            return None

        # The map preview image size will be ``0,0,width,height``.
        # We cannot extract the preview if this section is missing, or the Size key value is invalid.
        preview_size = [int(x) for x in self.ini.get(CncGen2MapSections.PREVIEW, "Size", fallback="").split(",")]
        if len(preview_size) != 4:
            LOGGER.debug("No preview size")
            return None

        # width and height are needed to lzo decompress the preview data.
        width, height = preview_size[2], preview_size[3]
        decompressed_preview = self._decompress_preview_from_base64(width, height)
        return self._create_preview_bitmap(width, height, decompressed_preview)

    def _decompress_preview_from_base64(self, width: int, height: int) -> io.BytesIO:
        """Decode the preview bytes from Base64, then lzo decompress the bytes.

        :param width:
            The pixel width of the preview image.
        :param height:
            The pixel height of the preview image.
        :return:
            The decoded and decompressed bytes for the preview.
        :raises exceptions.MapPreviewCorrupted:
            Raised when the preview is corrupted in some way:
                - Preview data decompresses to be larger than we expected from the ``Preview.Size``
                - One of the LZO blocks causes us to read more bytes than exist in the compressed data.
                - LZO decompression fails.
        """
        # Each pixel in the bitmap should be 3 bytes: blue, green, red 0-255 color values.
        # The file size of the bitmap will be the width, times the height, times 3 bytes for each pixel.
        decompressed_expected_size = width * height * 3

        # The preview base64 is split across the keys in the preview pack section.
        preview_b64: str = "".join(self.ini[CncGen2MapSections.PREVIEW_PACK].values())
        compressed_preview: bytes = base64.b64decode(preview_b64)

        # Each pixel block is a header, and the block data.
        # byte[0] and [1] specify the compressed block size.
        # byte[2] and [3] specify the size of the block when uncompressed.
        # The header bytes are all little endian.
        # The uncompressed block is a group of pixels.
        decompressed_preview = io.BytesIO()
        read_bytes = written_bytes = 0
        while True:
            # We're done reading if we have read all the bytes as defined by ``Preview.Size``.
            if read_bytes >= decompressed_expected_size:
                break

            # Read the compressed size of the block. The size is stored as a two byte integer
            block_size_compressed, read_bytes = self._read_16bit_int_le(compressed_preview, read_bytes, 2)

            # Read the uncompressed size of the block. The size is stored as a two byte integer
            block_size_uncompressed, read_bytes = self._read_16bit_int_le(compressed_preview, read_bytes, 2)

            # If the block sizes are 0 then we reached the end of the actual pixel data.
            if block_size_compressed == 0 or block_size_uncompressed == 0:
                break

            # Reading the expected compressed bytes will exceed the size of the compressed data.
            # This means the ``Preview.Size`` was wrong, or the preview data is corrupt.
            projected_read_byte_count = read_bytes + block_size_compressed
            compressed_size_exceeds_source = projected_read_byte_count > len(compressed_preview)

            # The size of the written bytes will exceed the expected uncompressed image size.
            # This means the ``Preview.Size`` was wrong, or the preview data is corrupt.
            projected_written_byte_count = written_bytes + block_size_uncompressed
            uncompressed_size_exceeds_destination = projected_written_byte_count > decompressed_expected_size
            error_params = {
                "decompressed_expected_size": decompressed_expected_size,
                "projected_decompressed_size": projected_written_byte_count,
                "projected_read_byte_count": projected_read_byte_count,
                "preview_pack_size": len(compressed_preview),
            }
            if compressed_size_exceeds_source or uncompressed_size_exceeds_destination:
                # Raise an error instead of returning None, because we need to inform the user that their map
                # is corrupted in some way.
                raise exceptions.MapPreviewCorrupted(
                    "Preview data does not match preview size or the data is corrupted, unable to extract preview.",
                    code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    params=error_params,
                )

            # Slice off the compressed block of bytes, according to the block header.
            compressed_block = compressed_preview[read_bytes : read_bytes + block_size_compressed]

            # Decompress the block.
            try:
                # decompress without the header because we manually grabbed the necessary bytes.
                uncompressed_block = lzo.decompress(compressed_block, False, block_size_uncompressed)
            except lzo.error as e:
                raise exceptions.MapPreviewCorrupted(
                    "Could not decompress the preview. Preview data is corrupted in some way.",
                    code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    params=error_params,
                ) from e
            else:
                # Write the decompressed bytes to the returned io stream.
                decompressed_preview.write(uncompressed_block)

            # Notate how many blocks we've read and written for error checking in the next iteration.
            read_bytes += block_size_compressed
            written_bytes += block_size_uncompressed

        decompressed_preview.seek(0)
        return decompressed_preview

    @staticmethod
    def _read_16bit_int_le(compressed_preview: bytes, start: int, bytes_to_read: int) -> t.Tuple[int, int]:
        """Read a little-endian 16bit integer from bytes.

        :param compressed_preview:
            The byte stream.
        :param start:
            Which byte to start reading from.
        :return:
            - [0] The integer that was read
            - [1] The next byte position in the byte stream. The byte index after the int we just read.
        """
        stop = start + bytes_to_read
        read = int.from_bytes(
            compressed_preview[start:stop],
            byteorder="little",
            signed=False,
        )
        return read, stop

    def _create_preview_bitmap(self, width: int, height: int, decompressed_preview: io.BytesIO) -> Image.Image:
        """Create the pillow image from the decompressed preview bytes.

        :param width:
            Image pixel width.
        :param height:
            Image pixel height.
        :param decompressed_preview:
            Decompressed byte data for the preview.
        :return:
            Raw pillow image.
        """
        decompressed_preview.seek(0)
        # 0, 0 means "start drawing in the top left corner."
        img = Image.frombytes("RGB", (width, height), decompressed_preview.read(), "raw", "RGB", 0, 0)
        return img

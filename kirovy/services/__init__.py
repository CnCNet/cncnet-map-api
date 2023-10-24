import configparser
import enum

from django.core.files import File
from kirovy import typing as t, exceptions

from django.utils.translation import gettext as _


class MapParserService:
    file: File
    parser: configparser.ConfigParser

    required_sections = {
        "Header",
        "Basic",
        "Map",
        "OverlayDataPack",
        "OverlayPack",
        "SpecialFlags",
        "Digest",
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
        if self.required_sections not in sections:
            raise exceptions.InvalidMapFile(
                self.ErrorMsg.MISSING_INI,
                code=self.ErrorMsg.MISSING_INI.name,
                params={"missing": self.required_sections - sections},
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

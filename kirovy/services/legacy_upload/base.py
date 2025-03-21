import dataclasses
import pathlib
import zipfile

from cryptography.utils import cached_property
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile

from kirovy import typing as t, constants
from kirovy.constants.api_codes import LegacyUploadApiCodes
from kirovy.exceptions import view_exceptions
from kirovy.services.cnc_gen_2_services import CncGen2MapParser
from kirovy.utils import file_utils
from kirovy.utils.file_utils import ByteSized


@dataclasses.dataclass
class ExpectedFile:
    possible_extensions: t.Set[str]
    file_validator: t.Callable[[str, ContentFile, zipfile.ZipInfo], bool]
    required: bool = True
    """attr: If false, this file is not required to be present."""


class LegacyMapServiceBase:
    game_slug: t.ClassVar[constants.GameSlugs]
    _file: zipfile.ZipFile
    ini_extensions: t.ClassVar[t.Set[str]]

    def __init__(self, file: UploadedFile):
        """Initializes the class and runs the validation for the expected files.

        :param file:
            The raw uploaded file from the view.
        :raises view_exceptions.KirovyValidationError:
            Raised if the file is invalid in any way.
        """
        if not file_utils.is_zipfile(file):
            raise view_exceptions.KirovyValidationError(
                detail="Your zipfile is invalid", code=LegacyUploadApiCodes.NOT_A_VALID_ZIP_FILE
            )

        self._file = zipfile.ZipFile(file)
        if len(self.expected_files) == 1:
            self.single_file_validator()
        else:
            self.multi_file_validator()

    def multi_file_validator(self):
        file_list = self._file.infolist()
        min_files = len([x for x in self.expected_files if x.required])
        max_files = len(self.expected_files)
        if min_files > len(file_list) > max_files:
            raise view_exceptions.KirovyValidationError(
                "Incorrect file count", code=LegacyUploadApiCodes.BAD_ZIP_STRUCTURE
            )

        for file_info in file_list:
            expected_file = self._get_expected_file_for_extension(file_info)
            with self._file.open(file_info, mode="r") as file:
                expected_file.file_validator(self._file.filename, ContentFile(file), file_info)

    def single_file_validator(self):
        first_file = self._file.infolist()[0]
        if pathlib.Path(first_file.filename).suffix not in self.expected_files[0].possible_extensions:
            raise view_exceptions.KirovyValidationError(
                "Map file was not the first Zip entry.", code=LegacyUploadApiCodes.BAD_ZIP_STRUCTURE
            )
        with self._file.open(first_file, mode="r") as map_file:
            self.expected_files[0].file_validator(self._file.filename, ContentFile(map_file), first_file)

    @cached_property
    def extract_name(self) -> str:
        ini_file_info = self._find_ini_file()
        fallback = f"legacy_client_upload_{pathlib.Path(self._file.filename).stem}"
        with self._file.open(ini_file_info, mode="r") as ini_file:
            return CncGen2MapParser(ContentFile(ini_file)).ini.get("Basic", "Name", fallback=fallback)

    def _find_ini_file(self) -> zipfile.ZipInfo:
        for file in self._file.infolist():
            if pathlib.Path(file.filename).suffix in self.ini_extensions:
                return file
        raise view_exceptions.KirovyValidationError(
            "No file containing map INI was found.", LegacyUploadApiCodes.NO_VALID_MAP_FILE
        )

    @cached_property
    def expected_files(self) -> t.List[ExpectedFile]:
        raise NotImplementedError("This Game's map validator hasn't implemented the expectd file structure.")

    def _get_expected_file_for_extension(self, zip_info: zipfile.ZipInfo) -> ExpectedFile:
        extension = pathlib.Path(zip_info.filename).suffix
        for expected in self.expected_files:
            if extension in expected.possible_extensions:
                return expected
        raise view_exceptions.KirovyValidationError(
            "Unexpected file type in zip file", LegacyUploadApiCodes.INVALID_FILE_TYPE
        )

    @staticmethod
    def default_map_file_validator(zip_file_name: str, file_content: ContentFile, zip_info: zipfile.ZipInfo):
        """Legacy map file generator that works for most Westwood games.

        Won't work for Dune 2000, or Tiberian Dawn.

        :param zip_file_name:
            The name of the uploaded zip file.
        :param file_content:
            The contents of the map file extracted from the zip file.
        :param zip_info:
            The zip metadata for the extracted map file.
        :return:
            None
        :raises view_exceptions.KirovyValidationError:
            Raised for any validation errors.
        """
        if ByteSized(zip_info.file_size) > ByteSized(mega=2):
            raise view_exceptions.KirovyValidationError(
                "Map file larger than expected.", code=LegacyUploadApiCodes.MAP_TOO_LARGE
            )

        # Reaching into the new map parsers is kind of dirty, but this legacy endpoint
        # is (hopefully) just to tide us over until we can migrate everyone to the new endpoints.
        if not CncGen2MapParser.is_text(file_content):
            raise view_exceptions.KirovyValidationError(
                "No valid map file.", code=LegacyUploadApiCodes.NO_VALID_MAP_FILE
            )

        if file_utils.hash_file_sha1(file_content) != pathlib.Path(zip_file_name).stem:
            raise view_exceptions.KirovyValidationError("Map file checksum differs from Zip name, rejected.")

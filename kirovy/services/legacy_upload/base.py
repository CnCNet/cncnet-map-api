import dataclasses
import functools
import io
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

    @cached_property
    def expected_files(self) -> t.List[ExpectedFile]:
        raise NotImplementedError("This Game's map validator hasn't implemented the expectd file structure.")

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
            expected_file.file_validator(self._file.filename, ContentFile(self._file.read(file_info)), file_info)

    def single_file_validator(self):
        first_file = self._file.infolist()[0]
        if pathlib.Path(first_file.filename).suffix not in self.expected_files[0].possible_extensions:
            raise view_exceptions.KirovyValidationError(
                "Map file was not the first Zip entry.", code=LegacyUploadApiCodes.BAD_ZIP_STRUCTURE
            )
        self.expected_files[0].file_validator(self._file.filename, ContentFile(self._file.read(first_file)), first_file)

    @cached_property
    def map_sha1_from_filename(self) -> str:
        """Legacy upload endpoints need the hash for the map file, not the full zip hash.

        This should only be used after ``__init__`` has completed and the hash from the filename has been verified
        to match the internal map file's hash.
        """
        return pathlib.Path(self._file.filename).stem

    @cached_property
    def file_contents_merged(self) -> io.BytesIO:
        """The legacy map DB checks hash by extracting all zip-file contents, appending them, then hashing.

        We will mirror that behavior for legacy endpoints so that the file hashes in the database match
        what the legacy clients expect.

        This will not match the logic for the new UI upload endpoints at all, but that's fine.

        .. note::

            The order of ``self.expected_files`` will control the order that files
            are appended in. This order matter and needs to match the client, or the hahes will not match.

        :return:
            All file contents merged into one stream. Order depends on ``self.expected_files``
        """
        output = io.BytesIO()
        for expected_file in self.expected_files:
            file_info = self._find_file_info_by_extension(expected_file.possible_extensions)
            output.write(self._file.read(file_info))
        output.seek(0)
        return output

    @cached_property
    def map_name(self) -> str:
        ini_file_info = self._find_file_info_by_extension(self.ini_extensions)
        fallback = f"legacy_client_upload_{self.map_sha1_from_filename}"
        ini_file = ContentFile(self._file.read(ini_file_info))
        return CncGen2MapParser(ini_file).ini.get("Basic", "Name", fallback=fallback)

    def _find_file_info_by_extension(self, extensions: t.Set[str]) -> zipfile.ZipInfo:
        """Find the zipinfo object for a file by a set of possible file extensions.

        This is meant to be used to find specific files in the zip.
        e.g. finding the ``.ini`` file to extract the map name from.

        It's hacky, but filenames and file order within the zip aren't predictable.

        :param extensions:
            A set of possible extensions to look for.
            e.g. ``{".map", ".yro", ".yrm"}`` to find the map ini for Yuri's Revenge.
        :return:
            The zipinfo for the matching file in the archive.
        :raises view_exceptions.KirovyValidationError:
            Raised when no file matching the possible extensions was found in the zip archive.
        """
        for file in self._file.infolist():
            if pathlib.Path(file.filename).suffix in extensions:
                return file
        raise view_exceptions.KirovyValidationError(
            "No file matching the expected extensions was found",
            LegacyUploadApiCodes.NO_VALID_MAP_FILE,
            {"expected": extensions},
        )

    def _get_expected_file_for_extension(self, zip_info: zipfile.ZipInfo) -> ExpectedFile:
        """Get the ``expected_file`` class instance corresponding to the file in the zipfile.

        This is used to find the validator for a file in the uploaded zip file.
        This is hacky, but the order and filenames aren't predictable in uploaded zips,
        so it will have to do.

        :param zip_info:
            The info for a file in the uploaded zipfile. We will try to find the
            :class:`kirovy.services.legacy_upload.base.ExpectedFile` for it.
        :return:
            The :class:`kirovy.services.legacy_upload.base.ExpectedFile` for this uploaded file.
        :raises view_exceptions.KirovyValidationError:
            Raised if no corresponding `kirovy.services.legacy_upload.base.ExpectedFile` is found.
            This has a security benefit of not allowing non-c&c-map-files to sneak their way in with a legitimate map.
        """
        extension = pathlib.Path(zip_info.filename).suffix
        for expected in self.expected_files:
            if extension in expected.possible_extensions:
                return expected
        raise view_exceptions.KirovyValidationError(
            "Unexpected file type in zip file", LegacyUploadApiCodes.INVALID_FILE_TYPE
        )

    def processed_zip_file(self) -> ContentFile:
        """Returns a file to save to the database.

        This file has been processed to match the format that legacy CnCNet clients expect.

        :return:
            A django-compatible file for a legacy CnCNet-client-compatible zip file.
        """
        files_info = self._file.infolist()
        zip_bytes = io.BytesIO()
        processed_zip = zipfile.ZipFile(zip_bytes, mode="w", compresslevel=5, allowZip64=False)
        map_hash = pathlib.Path(self._file.filename).stem

        for file_info_original in files_info:
            file_name_original = pathlib.Path(file_info_original.filename)
            with self._file.open(file_info_original, mode="r") as original_file_data:
                # All files must have the map hash as the filename.
                processed_zip.writestr(
                    f"{map_hash}{file_name_original.suffix}", data=original_file_data.read(), compresslevel=4
                )

        processed_zip.close()
        zip_bytes.seek(0)
        return ContentFile(zip_bytes.read(), name=self._file.filename)


def default_map_file_validator(zip_file_name: str, file_content: ContentFile, zip_info: zipfile.ZipInfo):
    """Legacy map file generator that works for most Westwood games.

    Won't work for Dune 2000, or Tiberian Dawn.

    :param zip_file_name:
        The name of the uploaded zip file.
    :param file_content:
        The contents of the map file extracted from the zip file.
        For RA2 and YR this will be a ``.map`` file, or one of its aliases like ``.yrm``.
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
        raise view_exceptions.KirovyValidationError("No valid map file.", code=LegacyUploadApiCodes.NO_VALID_MAP_FILE)

    if file_utils.hash_file_sha1(file_content) != pathlib.Path(zip_file_name).stem:
        raise view_exceptions.KirovyValidationError("Map file checksum differs from Zip name, rejected.")

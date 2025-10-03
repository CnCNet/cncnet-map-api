import enum


class UploadApiCodes(enum.StrEnum):
    GAME_SLUG_DOES_NOT_EXIST = "game-slug-does-not-exist"
    GAME_DOES_NOT_EXIST = "game-does-not-exist"
    MISSING_GAME_SLUG = "missing-game-slug"
    FILE_TO_LARGE = "file-too-large"
    EMPTY_UPLOAD = "where-file"
    DUPLICATE_MAP = "duplicate-map"
    FILE_EXTENSION_NOT_SUPPORTED = "file-extension-not-supported"
    INVALID = "invalid-data-upload"


class LegacyUploadApiCodes(enum.StrEnum):
    NOT_A_VALID_ZIP_FILE = "invalid-zipfile"
    BAD_ZIP_STRUCTURE = "invalid-zip-structure"
    MAP_TOO_LARGE = "map-file-too-large"
    NO_VALID_MAP_FILE = "no-valid-map-file"
    HASH_MISMATCH = "file-hash-does-not-match-zip-name"
    INVALID_FILE_TYPE = "invalid-file-type-in-zip"
    GAME_NOT_SUPPORTED = "game-not-supported"
    MAP_FAILED_TO_PARSE = "map-failed-to-parse"


class FileUploadApiCodes(enum.StrEnum):
    MISSING_FOREIGN_ID = "missing-foreign-id"
    INVALID = "file-failed-validation"
    UNSUPPORTED = "parent-does-not-support-this-upload"
    """attr: Raised when the parent object for the file does not allow this upload.

    e.g. a temporary map does not support custom image uploads.
    """
    TOO_LARGE = "file-too-large"

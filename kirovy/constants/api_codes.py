import enum


class UploadApiCodes(enum.StrEnum):
    GAME_SLUG_DOES_NOT_EXIST = "game-slug-does-not-exist"
    MISSING_GAME_SLUG = "missing-game-slug"
    FILE_TO_LARGE = "file-too-large"
    EMPTY_UPLOAD = "where-file"
    DUPLICATE_MAP = "duplicate-map"
    FILE_EXTENSION_NOT_SUPPORTED = "file-extension-not-supported"

import typing_extensions
from rest_framework.response import Response

import kirovy.objects.ui_objects
from kirovy import typing as t

DataType = typing_extensions.TypeVar(
    "DataType", bound=kirovy.objects.ui_objects.BaseResponseData, default=kirovy.objects.ui_objects.BaseResponseData
)


class KirovyResponse(Response, t.Generic[DataType]):
    data: DataType

    def __init__(
        self,
        data: DataType = None,
        status: t.Optional[int] = None,
        template_name: t.Optional[str] = None,
        headers: t.Optional[t.DictStrAny] = None,
        exception: bool = False,
        content_type: t.Optional[str] = None,
    ):
        super().__init__(data, status, template_name, headers, exception, content_type)

from rest_framework.response import Response

import kirovy.objects.ui_objects
from kirovy import typing as t


class KirovyResponse(Response):
    def __init__(
        self,
        data: t.Optional[kirovy.objects.ui_objects.BaseResponseData] = None,
        status: t.Optional[int] = None,
        template_name: t.Optional[str] = None,
        headers: t.Optional[t.DictStrAny] = None,
        exception: bool = False,
        content_type: t.Optional[str] = None,
    ):
        super().__init__(data, status, template_name, headers, exception, content_type)

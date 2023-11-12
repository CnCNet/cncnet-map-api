from rest_framework.request import Request as _DRFRequest
from kirovy import models, typing as t, objects


class KirovyRequest(_DRFRequest):
    """Wraps the DRF class for typing and type hinting.

    You probably shouldn't be manually instantiating this class.
    Additionally, you should only use this class as a type hint for django-rest-framework endpoints.
    """

    user: t.Optional[models.CncUser]
    auth: t.Optional[objects.CncnetUserInfo]

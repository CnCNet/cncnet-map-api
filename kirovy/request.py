from functools import cached_property

from rest_framework.request import Request as _DRFRequest
from kirovy import models, typing as t, objects


class KirovyRequest(_DRFRequest):
    """Wraps the DRF class for typing and type hinting.

    You probably shouldn't be manually instantiating this class.
    Additionally, you should only use this class as a type hint for django-rest-framework endpoints.
    """

    user: t.Optional[models.CncUser]
    auth: t.Optional[objects.CncnetUserInfo]

    @cached_property
    def client_ip_address(self) -> str:
        if self.user.is_staff:
            return "staff"
        x_forwarded_for: str | None = self.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()

        return self.META.get("REMOTE_ADDR", "unknown")

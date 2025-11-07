from structlog import get_logger as _get_logger
import typing as t

from structlog.stdlib import BoundLogger


def default_json_encode_object(value: object) -> str:
    json_func: t.Callable[[object], str] | None = getattr(value, "__json__", None)
    if json_func and callable(json_func):
        return json_func(value)

    stringy: bool = type(value).__str__ is not object.__str__  # Check if this object implements __str__
    if stringy:
        return str(value)

    return f"cannot-json-encode--{type(value).__name__}"


def get_logger(*args: t.Any, **initial_values: t.Any) -> BoundLogger:
    return _get_logger(*args, **initial_values)

"""Value helpers shared by the coordinator and the entity platforms.

This module deliberately imports nothing from the rest of the integration:
``coordinator.py`` needs it, and ``entity.py`` imports ``coordinator.py``, so
anything living here must not close that circle.
"""

from typing import Any, Final

# Everything this integration writes back to the wallbox: booleans for the
# switches, whole ampere and second counts for the numbers. Values coming *out*
# of the API stay ``Any`` — that is untyped JSON from a cloud service.
type WritableValue = bool | int

_TRUE_VALUES: Final[frozenset[str]] = frozenset({"true", "1", "on", "yes"})
_FALSE_VALUES: Final[frozenset[str]] = frozenset({"false", "0", "off", "no"})


def coerce_bool(value: Any) -> bool | None:
    """Interpret an API property value as a boolean.

    The API reports booleans natively, but may fall back to their string form.
    Anything unrecognized yields ``None`` rather than ``False`` so the entity
    reports ``unknown`` instead of a confidently wrong ``off``.

    Args:
        value: Raw value from the API

    Returns:
        True or False if the value could be interpreted, None otherwise
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)

    text = str(value).strip().lower()
    if text in _TRUE_VALUES:
        return True
    if text in _FALSE_VALUES:
        return False
    return None


def values_match(written: WritableValue, reported: Any) -> bool:
    """Check whether the device reports back the value that was written to it.

    The API is loose about types on the way out: an integer written as ``16``
    may come back as ``16``, ``16.0`` or ``"16"``, and ``True`` as ``"true"``.
    A plain ``==`` would therefore never converge, leaving pending writes to
    expire and warn about a device that in fact obeyed.

    Args:
        written: Value sent to the API
        reported: Value the API reported afterwards

    Returns:
        True if both represent the same value
    """
    if written == reported:
        return True

    # Booleans first: ``float(True)`` is 1.0 and would take the numeric branch.
    if isinstance(written, bool):
        return coerce_bool(reported) is written

    try:
        return float(written) == float(reported)
    except TypeError, ValueError:
        return str(written) == str(reported)

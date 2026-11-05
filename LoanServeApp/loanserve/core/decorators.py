"""Small reusable guards and instrumentation."""

from functools import wraps
from numbers import Number
from time import perf_counter

from loanserve.core.exceptions import InvalidApplicationError


def reject_negative_arguments(wrapped_function):
    @wraps(wrapped_function)
    def checked_call(*positional_arguments, **keyword_arguments):
        for value in positional_arguments:
            if isinstance(value, Number) and value < 0:
                raise InvalidApplicationError(
                    f"{wrapped_function.__name__} rejects negative value {value}"
                )
        return wrapped_function(*positional_arguments, **keyword_arguments)

    return checked_call


def measure_duration(wrapped_function):
    @wraps(wrapped_function)
    def timed_call(*args, **kwargs):
        started = perf_counter()
        try:
            return wrapped_function(*args, **kwargs)
        finally:
            timed_call.last_duration_seconds = perf_counter() - started

    timed_call.last_duration_seconds = 0.0
    return timed_call

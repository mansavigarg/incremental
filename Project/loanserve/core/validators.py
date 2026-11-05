"""Canonical forms for applicant contact identifiers."""

import re

from config.constants import EMAIL_ADDRESS_PATTERN, MOBILE_NUMBER_PATTERN, PAN_NUMBER_PATTERN
from loanserve.core.exceptions import InvalidApplicationError


def validate_pan_number(pan_number):
    value = str(pan_number).strip().upper()
    if not re.fullmatch(PAN_NUMBER_PATTERN, value):
        raise InvalidApplicationError(f"PAN {value!r} must have shape AAAAA9999A")
    return value


def validate_mobile_number(mobile_number):
    value = str(mobile_number).strip().replace(" ", "")
    if not re.fullmatch(MOBILE_NUMBER_PATTERN, value):
        raise InvalidApplicationError(f"Mobile {value!r} must have ten digits led by 6 to 9")
    return value


def validate_email_address(email_address):
    value = str(email_address).strip().lower()
    if not re.fullmatch(EMAIL_ADDRESS_PATTERN, value):
        raise InvalidApplicationError(f"Invalid email address {value!r}")
    return value

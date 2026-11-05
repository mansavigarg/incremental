"""Errors raised deliberately by LoanServe."""


class LoanServeError(Exception):
    """Base error for the platform."""


class UnsupportedLoanTypeError(LoanServeError):
    """The requested loan product is unavailable."""


class StorageError(LoanServeError):
    """A stored file could not be read or written."""


class InvalidApplicationError(LoanServeError):
    """Application values are invalid."""


class LanguageModelError(LoanServeError):
    """A language model failed or returned unusable content."""

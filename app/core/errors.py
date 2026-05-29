class PsStoreTrackerError(Exception):
    """Base application exception."""


class ConfigError(PsStoreTrackerError):
    """Raised when application settings cannot be loaded or validated."""


class HttpClientError(PsStoreTrackerError):
    """Raised when an HTTP request cannot be completed."""


class AccessDeniedError(HttpClientError):
    """Raised when PlayStation blocks the current request path."""


class ParserError(PsStoreTrackerError):
    """Raised when external PlayStation data has an unexpected structure."""

class ResolutionError(Exception):
    """Base exception for all resolution failures."""


class InvalidLinkError(ResolutionError):
    """Raised when the link is invalid, empty, or not a supported URL."""


class NetworkError(ResolutionError):
    """Raised when a network error occurs during resolution."""


class TimeoutError(ResolutionError):
    """Raised when resolution times out."""

"""Exceptions for iXmanager integration."""


class IXManagerError(Exception):
    """Base exception for iXmanager integration."""


class IXManagerConnectionError(IXManagerError):
    """Exception raised when connection to iXmanager API fails."""


class IXManagerAuthenticationError(IXManagerError):
    """Exception raised when the API rejects the API key."""


class IXManagerNotFoundError(IXManagerError):
    """Exception raised when the controller or property does not exist."""

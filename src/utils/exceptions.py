"""Custom exceptions and error handling utilities for the Growatt Weather Based Charger."""

class GrowattError(Exception):
    """Base exception for Growatt-related errors."""
    pass

class GrowattAPIError(GrowattError):
    """Exception raised for errors in the API."""
    def __init__(self, message, response=None):
        self.message = message
        self.response = response
        super().__init__(self.message)

class GrowattAuthError(GrowattError):
    """Exception raised for authentication errors."""
    pass

class GrowattConfigError(GrowattError):
    """Exception raised for configuration errors."""
    pass

class GrowattDeviceError(GrowattError):
    """Exception raised for device-related errors."""
    pass
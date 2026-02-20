"""Custom exceptions for the Notifications connector (Slack / Microsoft Teams).

Defines a hierarchy of exceptions for handling errors specific to
notification delivery operations.

Exception hierarchy:
    NotificationError (base)
    ├── NotificationAuthenticationError
    ├── NotificationConfigurationError
    └── NotificationDeliveryError
"""


class NotificationError(Exception):
    """Base exception for all notification connector errors.

    Args:
        message: A human-readable description of the error.
    """

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(self.message)


class NotificationAuthenticationError(NotificationError):
    """Raised when authentication with a notification service fails.

    This typically occurs when a webhook URL is invalid, a bot token
    is expired, or an OAuth flow fails.

    Args:
        message: A human-readable description of the authentication error.
    """


class NotificationConfigurationError(NotificationError):
    """Raised when required configuration is missing or invalid.

    This occurs when environment variables such as SLACK_WEBHOOK_URL or
    TEAMS_WEBHOOK_URL are missing, empty, or contain invalid values.

    Args:
        message: A human-readable description of the configuration error.
    """


class NotificationDeliveryError(NotificationError):
    """Raised when a notification fails to be delivered.

    Wraps HTTP errors and unexpected API responses with contextual
    information about the failed delivery.

    Args:
        message: A human-readable description of the delivery error.
        status_code: The HTTP status code returned, if available.
        channel: The target channel type ('slack' or 'teams').
    """

    def __init__(
        self, message: str, status_code: int = 0, channel: str = ""
    ) -> None:
        self.status_code = status_code
        self.channel = channel
        parts = []
        if channel:
            parts.append(f"[{channel}]")
        if status_code:
            parts.append(f"HTTP {status_code}")
        prefix = " ".join(parts)
        full_message = f"Notification delivery failed {prefix}: {message}" if prefix else f"Notification delivery failed: {message}"
        super().__init__(full_message)

"""Notifications connector package — Slack & Microsoft Teams integration.

Provides unified notification delivery to Slack and Microsoft Teams,
with support for slash commands, daily summaries, and security alerts.

Feature 4.3 — Intégration Slack / Microsoft Teams.
"""

from src.connectors.notifications.connector import NotificationsConnector
from src.connectors.notifications.exceptions import (
    NotificationAuthenticationError,
    NotificationConfigurationError,
    NotificationDeliveryError,
    NotificationError,
)
from src.connectors.notifications.models import (
    DailySummary,
    NotificationChannel,
    NotificationEvent,
    NotificationPriority,
    NotificationResult,
    SlashCommand,
)

__all__ = [
    "NotificationsConnector",
    "NotificationChannel",
    "NotificationPriority",
    "NotificationEvent",
    "NotificationResult",
    "SlashCommand",
    "DailySummary",
    "NotificationError",
    "NotificationAuthenticationError",
    "NotificationConfigurationError",
    "NotificationDeliveryError",
]

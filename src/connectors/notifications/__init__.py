"""Notifications connector package — Slack & Microsoft Teams integration.

Provides unified notification delivery to Slack and Microsoft Teams,
with support for slash commands, daily summaries, and security alerts.

Feature 4.3 — Intégration Slack / Microsoft Teams.
"""

from src.connectors.notifications.exceptions import (
    NotificationError,
    NotificationAuthenticationError,
    NotificationConfigurationError,
    NotificationDeliveryError,
)
from src.connectors.notifications.models import (
    NotificationChannel,
    NotificationPriority,
    NotificationEvent,
    NotificationResult,
    SlashCommand,
    DailySummary,
)
from src.connectors.notifications.connector import NotificationsConnector

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

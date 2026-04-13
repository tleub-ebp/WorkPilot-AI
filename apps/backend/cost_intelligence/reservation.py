"""
Budget Reservation — Reserve budget before launching a spec.

Prevents concurrent specs from overshooting the project budget by
reserving an estimated amount up front.  Reservations are released
when a spec completes (actual cost replaces the reservation).
"""

from __future__ import annotations

import logging
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ReservationStatus(str, Enum):
    ACTIVE = "active"
    RELEASED = "released"
    EXPIRED = "expired"


@dataclass
class BudgetReservation:
    """A budget reservation for a spec."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    scope: str = "project"
    scope_id: str = ""
    spec_id: str = ""
    reserved_usd: float = 0.0
    actual_usd: float = 0.0
    status: ReservationStatus = ReservationStatus.ACTIVE
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    released_at: str | None = None


class ReservationManager:
    """Manage budget reservations for concurrent specs.

    Usage::

        mgr = ReservationManager(total_budget=100.0)
        res = mgr.reserve("project-1", "spec-001", estimated=5.0)
        # ... spec runs ...
        mgr.release(res.id, actual_cost=3.50)
        available = mgr.available_budget("project-1")
    """

    def __init__(self, total_budget: float = 0.0) -> None:
        self._total_budget = total_budget
        self._reservations: dict[str, BudgetReservation] = {}
        self._lock = threading.Lock()

    @property
    def total_budget(self) -> float:
        return self._total_budget

    @total_budget.setter
    def total_budget(self, value: float) -> None:
        self._total_budget = value

    def reserve(
        self,
        scope_id: str,
        spec_id: str,
        estimated_usd: float,
        scope: str = "project",
    ) -> BudgetReservation:
        """Reserve budget for a spec. Raises ValueError if insufficient budget."""
        with self._lock:
            available = self._compute_available(scope_id)
            if self._total_budget > 0 and estimated_usd > available:
                raise ValueError(
                    f"Insufficient budget: requested ${estimated_usd:.2f}, "
                    f"available ${available:.2f}"
                )
            reservation = BudgetReservation(
                scope=scope,
                scope_id=scope_id,
                spec_id=spec_id,
                reserved_usd=estimated_usd,
            )
            self._reservations[reservation.id] = reservation
            logger.info(
                "Reserved $%.2f for spec %s (id=%s)",
                estimated_usd, spec_id, reservation.id,
            )
            return reservation

    def release(self, reservation_id: str, actual_cost: float = 0.0) -> BudgetReservation:
        """Release a reservation, replacing estimated with actual cost."""
        with self._lock:
            res = self._reservations.get(reservation_id)
            if res is None:
                raise KeyError(f"Reservation '{reservation_id}' not found.")
            if res.status != ReservationStatus.ACTIVE:
                raise ValueError(
                    f"Reservation '{reservation_id}' is already {res.status.value}."
                )
            res.actual_usd = actual_cost
            res.status = ReservationStatus.RELEASED
            res.released_at = datetime.now(timezone.utc).isoformat()
            logger.info(
                "Released reservation %s: estimated=$%.2f actual=$%.2f",
                reservation_id, res.reserved_usd, actual_cost,
            )
            return res

    def available_budget(self, scope_id: str) -> float:
        """Get remaining available budget after active reservations."""
        with self._lock:
            return self._compute_available(scope_id)

    def total_reserved(self, scope_id: str) -> float:
        """Get total currently reserved amount for a scope."""
        return sum(
            r.reserved_usd
            for r in self._reservations.values()
            if r.scope_id == scope_id and r.status == ReservationStatus.ACTIVE
        )

    def total_spent(self, scope_id: str) -> float:
        """Get total actual cost from released reservations."""
        return sum(
            r.actual_usd
            for r in self._reservations.values()
            if r.scope_id == scope_id and r.status == ReservationStatus.RELEASED
        )

    def get_reservation(self, reservation_id: str) -> BudgetReservation | None:
        return self._reservations.get(reservation_id)

    def list_active(self, scope_id: str | None = None) -> list[BudgetReservation]:
        """List active reservations, optionally filtered by scope."""
        result = [
            r for r in self._reservations.values()
            if r.status == ReservationStatus.ACTIVE
        ]
        if scope_id:
            result = [r for r in result if r.scope_id == scope_id]
        return result

    def list_all(self, scope_id: str | None = None) -> list[BudgetReservation]:
        result = list(self._reservations.values())
        if scope_id:
            result = [r for r in result if r.scope_id == scope_id]
        return result

    def _compute_available(self, scope_id: str) -> float:
        """Compute available budget = total - active_reserved - spent."""
        if self._total_budget <= 0:
            return float("inf")
        reserved = sum(
            r.reserved_usd
            for r in self._reservations.values()
            if r.scope_id == scope_id and r.status == ReservationStatus.ACTIVE
        )
        spent = sum(
            r.actual_usd
            for r in self._reservations.values()
            if r.scope_id == scope_id and r.status == ReservationStatus.RELEASED
        )
        return max(0, self._total_budget - reserved - spent)

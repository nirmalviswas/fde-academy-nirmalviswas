from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class CarrierConfig:
    """Immutable carrier SLA configuration."""

    code: str
    name: str
    sla_days: int
    region: str
    active: bool = True

    def __post_init__(self) -> None:
        self.code = self.code.strip().upper()
        if self.sla_days <= 0:
            raise ValueError("sla_days must be > 0")


class ShipmentTracker:
    """Tracks a single shipment through its delivery lifecycle.

    Valid status transitions:
        pending     -> in_transit
        in_transit  -> delivered | exception
        exception   -> in_transit (after resolution)
        delivered   -> (terminal — no further transitions)

    Attributes:
        shipment_id: Unique identifier.
        carrier: CarrierConfig for this shipment.
        origin: Origin city.
        destination: Destination city.
        delay_days: Days late (>0 = delayed).
        cost_usd: Shipment cost.
    """

    TRANSITIONS: dict[str, set[str]] = {
        "pending": {"in_transit"},
        "in_transit": {"delivered", "exception"},
        "exception": {"in_transit"},
        "delivered": set(),
    }

    PENALTY_RATE_PER_DAY: float = 150.0

    def __init__(
        self,
        shipment_id: str,
        carrier: CarrierConfig,
        origin: str,
        destination: str,
        delay_days: int = 0,
        cost_usd: float = 0.0,
    ) -> None:
        if not shipment_id.strip():
            raise ValueError("shipment_id must not be empty")
        if origin == destination:
            raise ValueError("origin and destination must differ")

        self.shipment_id = shipment_id.strip().upper()
        self.carrier = carrier
        self.origin = origin.strip().title()
        self.destination = destination.strip().title()
        self.cost_usd = cost_usd

        self._delay_days = 0
        self.delay_days = delay_days
        self._status = "pending"
        self._history: list[tuple[str, str, datetime]] = []

    @property
    def status(self) -> str:
        return self._status

    @status.setter
    def status(self, new_status: str) -> None:
        if new_status not in self.TRANSITIONS:
            raise ValueError(f"Unknown status: {new_status!r}")

        allowed = self.TRANSITIONS[self._status]
        if new_status not in allowed:
            raise ValueError(
                f"Invalid transition: {self._status} -> {new_status}. "
                f"Allowed from {self._status!r}: {allowed}"
            )

        old_status = self._status
        self._status = new_status
        self._history.append((old_status, new_status, datetime.utcnow()))

    @property
    def delay_days(self) -> int:
        return self._delay_days

    @delay_days.setter
    def delay_days(self, value: int) -> None:
        if value < 0:
            raise ValueError("delay_days must be >= 0")
        self._delay_days = value

    @property
    def is_delayed(self) -> bool:
        return self._delay_days > 0

    @property
    def breached_sla(self) -> bool:
        return self._delay_days > self.carrier.sla_days

    def delay_penalty(self, rate: Optional[float] = None) -> float:
        rate = rate if rate is not None else self.PENALTY_RATE_PER_DAY
        return round(self._delay_days * rate, 2)

    def transition_to(self, new_status: str) -> None:
        self.status = new_status

    def status_history(self) -> list[str]:
        return [f"{old} -> {new} @ {ts.isoformat()}" for old, new, ts in self._history]

    def to_dict(self) -> dict:
        return {
            "shipment_id": self.shipment_id,
            "carrier_code": self.carrier.code,
            "carrier_name": self.carrier.name,
            "origin": self.origin,
            "destination": self.destination,
            "status": self.status,
            "delay_days": self.delay_days,
            "cost_usd": self.cost_usd,
            "penalty_usd": self.delay_penalty(),
            "is_delayed": self.is_delayed,
            "breached_sla": self.breached_sla,
            "transition_count": len(self._history),
        }

    def __repr__(self) -> str:
        return (
            f"ShipmentTracker(id={self.shipment_id!r}, "
            f"carrier={self.carrier.code!r}, "
            f"status={self.status!r}, delay={self.delay_days}d)"
        )


if __name__ == "__main__":
    dhl = CarrierConfig(code="dhl", name="DHL Express", sla_days=2, region="APAC")
    fedex = CarrierConfig(code="fedex", name="FedEx India", sla_days=3, region="APAC")

    s = ShipmentTracker("sh-001", dhl, "Mumbai", "Delhi", delay_days=3, cost_usd=250.0)
    print(s)

    s.transition_to("in_transit")
    s.transition_to("delivered")
    print("History:", s.status_history())
    print("Penalty: $", s.delay_penalty())
    print("Breached SLA:", s.breached_sla)
    print("Foundry record:", s.to_dict())

    try:
        s.transition_to("pending")
    except ValueError as e:
        print("Expected error:", e)

    s2 = ShipmentTracker("sh-002", fedex, "Chennai", "Bangalore")
    s2.transition_to("in_transit")
    s2.transition_to("exception")
    s2.delay_days = 5
    s2.transition_to("in_transit")
    s2.transition_to("delivered")

    print("\ns2 history:")
    for entry in s2.status_history():
        print(" ", entry)

    shipments = [
        s,
        s2,
        ShipmentTracker("sh-003", dhl, "Pune", "Hyderabad", delay_days=0),
    ]
    records = [sh.to_dict() for sh in shipments]

    print(f"\nBatch: {len(records)} records ready for Foundry ingestion")
    delayed = [r for r in records if r["is_delayed"]]
    print(
        f"Delayed: {len(delayed)} | Avg penalty: $"
        f"{sum(r['penalty_usd'] for r in delayed)/max(len(delayed),1):.2f}"
    )

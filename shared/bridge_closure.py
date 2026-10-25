"""Defines the data structure and timezone of a Renfrew-Yoker bridge closure."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from zoneinfo import ZoneInfo

LONDON_TZ = ZoneInfo("Europe/London")


class ClosedTo(StrEnum):
    """Who a bridge closure stops from crossing.

    Attributes:
        EVERYONE: Both vehicles and pedestrians.
        VEHICLES: Vehicles only.
        PEDESTRIANS: Pedestrians only.
    """

    EVERYONE = "everyone"
    VEHICLES = "vehicles"
    PEDESTRIANS = "pedestrians"


@dataclass
class BridgeClosure:
    """A single bridge closure.

    Attributes:
        start: The date and time the bridge is closed from.
        end: The date and time the bridge reopens.
        closed_to: Who the bridge is closed to.
    """

    start: datetime
    end: datetime
    closed_to: ClosedTo

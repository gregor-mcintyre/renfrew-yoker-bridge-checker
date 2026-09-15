"""Defines the data structure and timezone of a Renfrew-Yoker bridge closure."""

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

LONDON_TZ = ZoneInfo("Europe/London")


@dataclass
class BridgeClosure:
    """A single bridge closure.

    Attributes:
        start: The date and time the bridge is closed from.
        end: The date and time the bridge reopens.
    """

    start: datetime
    end: datetime

"""Defines the data structure for a Renfrew-Yoker bridge closure."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class BridgeClosure:
    """A single bridge closure.

    Attributes:
        start: The date and time the bridge is closed from.
        end: The date and time the bridge reopens.
    """

    start: datetime
    end: datetime

"""Sample bridge closure and timestamp data shared across the test suite."""

from datetime import datetime

from bridge_closure import LONDON_TZ, BridgeClosure

FETCHED_AT = datetime(2026, 9, 15, 12, tzinfo=LONDON_TZ)

# Coupled to `tests.closures_webpage_text`
BRIDGE_CLOSURE = BridgeClosure(
    start=datetime(2026, 9, 15, 9, tzinfo=LONDON_TZ),
    end=datetime(2026, 9, 15, 12, 30, tzinfo=LONDON_TZ),
)

"""Time source and sleep, injected into the runner.

The legacy script mixed ``datetime.datetime.utcnow()`` with ``time.sleep``.
Keeping both behind a single object makes the acquisition loop driveable by
a fake clock in tests.
"""

import datetime
import time
from typing import Protocol


class Clock(Protocol):
    """Wall clock plus sleep, as used by the acquisition loop."""

    def now(self) -> datetime.datetime:
        """Return the current naive UTC timestamp (mirrors ``utcnow()``)."""

    def sleep(self, seconds: float) -> None:
        """Suspend execution for ``seconds``."""


class SystemClock:
    """Production clock: naive UTC plus ``time.sleep``."""

    def now(self) -> datetime.datetime:
        return datetime.datetime.utcnow()

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)

"""The acquisition loop.

Cadence and serial protocol are reproduced from the legacy script:

* 3.0 s startup delay after the port is opened,
* per cycle: ``reset_input_buffer``, 0.1 s settle, write ``b'x'``, flush,
  5.0 s conversion delay, one ``readline``,
* the record is written after sleeping until the cycle deadline,
* cycles are 20.0 s apart.

Everything is injected so the loop can be driven by fakes.
"""

import contextlib
import datetime

from heizungslogger.clock import Clock
from heizungslogger.frame import parse_frame
from heizungslogger.serial_link import SerialLink
from heizungslogger.store import local_label

STARTUP_DELAY = 3.0
CONVERSION_DELAY = 5.0
SETTLE_DELAY = 0.1
RATE = 20

#: Command byte that asks the Arduino for a fresh conversion.
REQUEST = b"x"


class Runner:
    """Wire a serial link, a display and a store together into a loop."""

    def __init__(
        self,
        link: SerialLink,
        display,
        store,
        clock: Clock,
        rate: int = RATE,
        startup_delay: float = STARTUP_DELAY,
        conversion_delay: float = CONVERSION_DELAY,
        settle_delay: float = SETTLE_DELAY,
        emit=print,
    ) -> None:
        self.link = link
        self.display = display
        self.store = store
        self.clock = clock
        self.rate = rate
        self.startup_delay = startup_delay
        self.conversion_delay = conversion_delay
        self.settle_delay = settle_delay
        self.emit = emit

        #: Frames dropped because they were empty or undecodable.
        self.rejected_frames = 0
        #: Display updates that failed since the last successful one.
        self.display_errors = 0
        self._display_degraded = False

    def run(self) -> None:
        """Run forever, one sample per ``rate`` seconds."""
        self.clock.sleep(self.startup_delay)
        while True:
            deadline = self.clock.now() + datetime.timedelta(seconds=self.rate)
            try:
                self.sample(deadline)
            except KeyboardInterrupt:
                raise SystemExit(0) from None

    def sample(self, deadline: datetime.datetime) -> list[str]:
        """Take one sample and persist it.

        Returns the parsed fields, or an empty list when the frame was rejected.

        Fault policy:

        * transport errors propagate, so the service restarts with a fresh port
          handle -- that restart is the only reconnect mechanism there is;
        * an empty or undecodable frame is rejected: no record, one log line,
          cadence preserved (``docs/RECORDING.md`` §4);
        * a display fault is degraded mode: the record is already written by
          then, the error is logged once and the handle is dropped.
        """
        self.link.reset_input_buffer()
        self.clock.sleep(self.settle_delay)
        self.link.write(REQUEST)
        self.link.flush()
        self.clock.sleep(self.conversion_delay)
        fields = self._parse(self.link.readline())

        if fields is None:
            self._wait_for(deadline)
            return []

        self.emit(fields)
        self._wait_for(deadline)

        self.emit(local_label(deadline).isoformat())
        self.store.append(fields, deadline)
        self._show(fields)
        return fields

    def _wait_for(self, deadline: datetime.datetime) -> None:
        """Sleep until ``deadline``, never passing a negative duration to sleep."""
        remaining = (deadline - self.clock.now()).total_seconds()
        self.emit(remaining)
        self.clock.sleep(max(0.0, remaining))

    def _parse(self, raw: bytes) -> list[str] | None:
        """Return the frame's fields, or ``None`` when the frame is unusable."""
        try:
            fields = parse_frame(raw)
        except UnicodeDecodeError:
            return self._reject(raw, "undecodable")
        if not any(field.strip() for field in fields):
            return self._reject(raw, "empty")
        return fields

    def _reject(self, raw: bytes, reason: str) -> None:
        self.rejected_frames += 1
        self.emit(f"rejected frame ({reason}): {raw[:80]!r}")
        return None

    def _show(self, fields: list[str]) -> None:
        """Update the display without letting a display fault stop collection."""
        try:
            self.display.show(fields)
        except Exception as exc:
            self.display_errors += 1
            if not self._display_degraded:
                self._display_degraded = True
                self.emit(f"display unavailable: {exc!r}; continuing without it")
            close = getattr(self.display, "close", None)
            if close is not None:
                with contextlib.suppress(Exception):
                    close()
            return

        if self._display_degraded:
            self._display_degraded = False
            self.emit(f"display recovered after {self.display_errors} failed update(s)")
            self.display_errors = 0

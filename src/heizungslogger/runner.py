"""The acquisition loop.

Cadence and serial protocol are reproduced from the legacy script:

* 3.0 s startup delay after the port is opened,
* per cycle: ``reset_input_buffer``, 0.1 s settle, write ``b'x'``, flush,
  5.0 s conversion delay, one ``readline``,
* the record is written after sleeping until the cycle deadline,
* cycles are 20.0 s apart.

Everything is injected so the loop can be driven by fakes.
"""

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
        """Take one sample and persist it. Returns the parsed fields."""
        self.link.reset_input_buffer()
        self.clock.sleep(self.settle_delay)
        self.link.write(REQUEST)
        self.link.flush()
        self.clock.sleep(self.conversion_delay)
        fields = parse_frame(self.link.readline())
        self.emit(fields)
        self.display.show(fields)

        remaining = deadline - self.clock.now()
        self.emit(remaining.total_seconds())
        self.clock.sleep(remaining.total_seconds())

        self.emit(local_label(deadline).isoformat())
        self.store.append(fields, deadline)
        return fields

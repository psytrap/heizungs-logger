"""Serial transport for the Arduino link.

``SerialLink`` is the small surface the runner needs, so tests can substitute
a fake. ``PyserialLink`` imports pyserial only when it is actually opened.
"""

from typing import Protocol


class SerialLink(Protocol):
    """Minimal serial surface used by the acquisition loop."""

    def reset_input_buffer(self) -> None:
        """Discard everything currently buffered for input."""

    def write(self, data: bytes) -> object:
        """Send bytes to the device."""

    def flush(self) -> None:
        """Wait until all buffered output is written."""

    def readline(self) -> bytes:
        """Read one line, terminated by ``\\n`` or the read timeout."""

    def close(self) -> None:
        """Release the port."""


def list_ports() -> list[tuple[str, str, str]]:
    """Return ``(port, description, hwid)`` tuples, sorted by port."""
    import serial.tools.list_ports  # noqa: PLC0415 - hardware import must stay lazy

    return sorted(serial.tools.list_ports.comports())


class PyserialLink:
    """``SerialLink`` backed by pyserial, opened explicitly or on first use."""

    def __init__(self, port: str, baudrate: int = 9600, timeout: float = 1.0) -> None:
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self._serial = None

    def open(self) -> None:
        """Open the port (no-op if already open)."""
        if self._serial is not None:
            return
        import serial  # noqa: PLC0415 - hardware import must stay lazy

        self._serial = serial.Serial(self.port, self.baudrate, timeout=self.timeout)

    def _handle(self):
        if self._serial is None:
            self.open()
        return self._serial

    def reset_input_buffer(self) -> None:
        self._handle().reset_input_buffer()

    def write(self, data: bytes) -> object:
        return self._handle().write(data)

    def flush(self) -> None:
        self._handle().flush()

    def readline(self) -> bytes:
        return self._handle().readline()

    def close(self) -> None:
        if self._serial is not None:
            self._serial.close()
            self._serial = None

    def __enter__(self) -> "PyserialLink":
        self.open()
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()

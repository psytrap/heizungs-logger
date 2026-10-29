# heizungs-logger
Simple multi-channel temperature monitor

Runs on any Raspberry Pi with an Adafruit 2x16 LCD over I2C and an Arduinio UNO connected to DS1820 sensors.

## Documentation

- [`docs/RECORDING.md`](docs/RECORDING.md) — JSON recording strategy: what is on disk today, the proposed v2 record format, the reader tolerance contract, and the open decisions.
- [`docs/OPERATIONS.md`](docs/OPERATIONS.md) — the systemd unit: install/uninstall, restart semantics, journal inspection, hardening limits.
- [`docs/FIRMWARE.md`](docs/FIRMWARE.md) — firmware wire format, build provenance, host tests, and the manual hardware procedure.
- [`tickets/`](tickets/) — ticket-first workflow ([protocol](tickets/README.md), [index](tickets/INDEX.md), [completed](tickets/DONE.md)).

## Install

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
```

On the Raspberry Pi, install the hardware extras as well:

```sh
pip install -e ".[hardware]"
```

## Test

```sh
python -m pytest
python -m ruff check .
./scripts/test-firmware.sh          # C++ frame test (skips without a compiler)
```

The test suite uses fakes only: no serial device, no LCD, and no Blinka is
required. Hardware libraries are imported lazily, so the package can be
imported on any machine.

## Run

```sh
python heizungs_logger.py --list                                  # list serial ports
python heizungs_logger.py --port /dev/ttyUSB0 \\
    --log_directory ~/heizungs_logger_logs                        # log
heizungslogger --port /dev/ttyUSB0 --log_directory ./            # console script
```

`--log_directory` defaults to the current directory. One record is appended
per 20 seconds to `LOG-<local-date>.json`, one line per sample.

## Deploy

```sh
sudo scripts/install-service.sh --restart
```

See [`docs/OPERATIONS.md`](docs/OPERATIONS.md) for `--dry-run`, `--uninstall`,
and the restart semantics.

## Layout

| Path | Purpose |
| :--- | :--- |
| `src/heizungslogger/` | Package: `frame`, `display`, `serial_link`, `store`, `clock`, `runner`, `cli` |
| `tests/` | Pytest suite (fakes only) |
| `heizungs_logger.py` | Entry-point shim kept for the deployed systemd unit |
| `heizungs_logger.ino` | Arduino firmware that samples the sensors |
| `firmware/` | Host-testable frame formatter shared with the sketch |
| `heizungs_logger.service` | systemd unit for the logger |
| `scripts/` | `install-service.sh`, `test-firmware.sh` |
| `docs/` | Specifications and operations notes |

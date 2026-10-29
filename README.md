# heizungs-logger
Simple multi-channel temperature monitor

Runs on any Raspberry Pi with an Adafruit 2x16 LCD over I2C and an Arduinio UNO connected to DS1820 sensors.

## Documentation

- [`docs/RECORDING.md`](docs/RECORDING.md) — JSON recording strategy: what is on disk today, the proposed v2 record format, the reader tolerance contract, and the open decisions.
- [`tickets/`](tickets/) — ticket-first workflow ([protocol](tickets/README.md), [index](tickets/INDEX.md), [completed](tickets/DONE.md)).

## Layout

| Path | Purpose |
| :--- | :--- |
| `heizungs_logger.py` | Logger running on the Raspberry Pi |
| `heizungs_logger.ino` | Arduino firmware that samples the sensors |
| `heizungs_logger.service` | systemd unit for the logger |
| `docs/` | Specifications |

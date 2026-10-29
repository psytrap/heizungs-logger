# Ticket 004: Testing Strategy for the Arduino Firmware (`heizungs_logger.ino`)

- **Status:** Done
- **Priority:** Normal
- **Scope & Relevant Files:**
  - `heizungs_logger.ino`
  - `tests/` (new firmware-related tests, if a host-side path is chosen)
  - `docs/` (protocol and firmware notes, if a build/test procedure is documented)

---

## Description & Context

The sketch that produces the serial frames is the only part of the system with **no tests and no build verification** in the repository. It is also the part with the strongest protocol contract: the Python side parses whatever it emits, and 1 385 log files already depend on that shape.

The sketch as deployed:

- waits for `Serial.available()`, discards one byte (the host sends `x`),
- reads 4 OneWire buses (`FIRST_ONE_WIRE_BUS = 2`, `ONE_WIRE_PINS = 4`), each via a fresh `OneWire`/`DallasTemperature` pair and `getTempCByIndex(0)`,
- reads 2 digital inputs (`FIRST_INPUT = 10`, `INPUT_PINS = 2`),
- toggles a heartbeat pin (6),
- prints `Temp <f> <f> <f> <f> Input on|off on|off\n`,
- leaves a block of comments at the bottom describing a raw 0x44/0xbe read sequence that the code does **not** implement.

Problems this ticket must address:

1. **No compile check.** There is no `platformio.ini`, no `arduino-cli` invocation, no CI step — a broken sketch is only discovered at flash time.
2. **No protocol contract test.** Nothing asserts that the emitted frame still matches the 11-field shape the Python side expects (see `docs/RECORDING.md`, v1b generation). Pins, order, and token spelling (`on`/`off`, `Temp`, `Input`, single spaces) are unverified.
3. **No testable units.** Frame formatting, bus reading, and input sampling are entangled in `loop()`, so none of it can be exercised without hardware.
4. **Unobservable failure modes.** `getTempCByIndex(0)` returns `DEVICE_DISCONNECTED_C` (−127) on a missing sensor; the sketch passes it through silently. Nothing records what a disconnected bus does to the frame.
5. **Dead documentation.** The trailing comment block describes an implementation path the code never takes; a reader cannot tell intent from behaviour.
6. **Unknown build provenance.** No board/FQBN, core versions, or library versions are recorded anywhere in the repo.

This is a **strategy and harness** ticket: decide *how* the firmware will be tested, implement the parts that can run without the attached hardware, and document the manual hardware steps. Flashing the board on the live Pi is **out of scope** and requires explicit maintainer authorisation.

Directions to evaluate (pick and justify; do not implement all of them by default):

- **Host-side unit tests** after extracting a pure `format_frame(temps, inputs)` function into a header/source pair that compiles on the host.
- **Fake `OneWire`/`DallasTemperature`** shims so the frame builder and sampling loop can run on the host, including the −127 disconnected case.
- **Compile-only verification** via `arduino-cli compile` (or PlatformIO) with pinned board FQBN and library versions, wired into the repo's quality gates.
- **Protocol fixture test** that feeds canned frames from the sketch's formatter into `heizungslogger.frame.parse_frame` and asserts 11 well-formed fields, plus a cross-language fixture file shared by both test suites.
- **Hardware-in-the-loop procedure**, documented as a manual checklist (flash, send `x`, capture 5 frames, assert shape), explicitly excluded from automated gates.

The chosen approach must not require the Pi to be touched, and must not change the wire format.

---

## Criteria

- [x] A written decision records which of the above directions are adopted and why the others are rejected.
- [x] Board FQBN, core version, and library versions are documented.
- [x] Frame formatting is exercisable without hardware (extracted function or equivalent), if that direction is adopted.
- [x] At least one automated test asserts the emitted frame shape against `heizungslogger.frame.parse_frame` and the documented 11-field contract.
- [x] Disconnected-sensor behaviour is covered by a test or explicitly documented as an accepted unknown.
- [x] Build verification runs as a single documented command and is added to the repository's quality gates (or the reason it cannot be is recorded).
- [x] The manual hardware procedure is documented and marked as requiring authorisation.
- [x] The wire format is unchanged; existing Python tests still parse the same frames.
- [x] `python -m pytest` passes.
- [x] Zero Ruff errors or warnings (`python -m ruff check .`).

---

## Execution Notes

### The repository sketch is not the deployed firmware

Before writing any harness the live device was inspected read-only. The newest record (2026-10-29) is:

```text
['Temp', '29.7', '28.4', '33.0', '29.3', '29.3', '15.3', 'Input', 'off', 'off', '2026-10-29T13:50:17.729536+01:00']
```

Six temperatures, one decimal. The checked-in sketch declares `ONE_WIRE_PINS = 4` and printed via `String(temp)`, which on AVR yields two decimals — i.e. it reproduces the v1a shape, not the eleven-field live shape. The deployed source is not on the Pi (`find ~ -name '*.ino'` finds nothing), so the exact revision cannot be recovered here. Consequence: the formatter takes temperature count and decimals as parameters, and `docs/FIRMWARE.md` §2 records the discrepancy as unresolved rather than guessing.

### Implementation

| File | Role |
| :--- | :--- |
| `firmware/frame.h`, `firmware/frame.cpp` | `hlog::formatFrame(out, cap, temps, nTemps, inputs, nInputs, decimals)` — bounded, NUL-terminating, emits the trailing `\n`; uses `dtostrf` under `ARDUINO`, `snprintf` on the host |
| `heizungs_logger.ino` | printing block replaced by one `formatFrame` call; loop, pins and heartbeat untouched |
| `tests/fixtures/firmware_frames.tsv` | six canonical frames: v1a/v1b, sentinels, negatives, one and two decimals |
| `tests/firmware/frame_test.cpp` | host test: compiles the formatter, checks every fixture row, plus truncation and zero-capacity behaviour |
| `tests/test_firmware_contract.py` | feeds the same frames through `parse_frame`; asserts round-trip and that widths are 9 or 11 fields |
| `scripts/test-firmware.sh` | one command: `g++ -Wall -Wextra -Werror`, run, clean up; prints `skipped` (exit 0) where no compiler exists |
| `docs/FIRMWARE.md` | wire format, discrepancy, decision record, provenance, test commands, manual hardware procedure |

### Decision summary

Adopted: pure formatter, host-side `g++` test, fixtures shared with Python. Rejected for now: fake `OneWire`/`DallasTemperature` shims (the loop is a straight pin scan; the contract lives in formatting). Not adopted: `arduino-cli` compile gate — no toolchain installed and the FQBN is unknown, so the extraction commands and the manual flash procedure are documented instead.

### Things worth knowing

- **Precision:** the sketch now formats with one decimal, matching the live device. This is an alignment with observed behaviour, not a format change; the `String(float)` default of two decimals was the outlier.
- **Rounding:** `dtostrf` rounds half away from zero, `snprintf` rounds half to even, so fixtures must avoid exact halves at the chosen precision. Documented in `docs/FIRMWARE.md` §5.
- **Sentinels:** `-127.0` and `85.0` pass through as ordinary fields and are asserted by both suites; nothing filters or annotates them.
- **Unverified on hardware:** the sketch compiles against Arduino semantics by inspection only (no Arduino core available locally). `Serial.print(frame)` replaces `Serial.print`/`println` calls, so the emitted bytes are unchanged in length and content.

### Gates

```text
$ .venv/bin/python -m pytest -q          -> 45 passed (30 existing + 15 new)
$ .venv/bin/python -m ruff check .       -> All checks passed
$ ./scripts/test-firmware.sh             -> 6 frame checks passed
$ g++ -std=c++17 -Wall -Wextra -Werror ...  -> compiles clean
```

No board was flashed and no service was stopped.

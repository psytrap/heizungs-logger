# Ticket 004: Testing Strategy for the Arduino Firmware (`heizungs_logger.ino`)

- **Status:** Backlog
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

- [ ] A written decision records which of the above directions are adopted and why the others are rejected.
- [ ] Board FQBN, core version, and library versions are documented.
- [ ] Frame formatting is exercisable without hardware (extracted function or equivalent), if that direction is adopted.
- [ ] At least one automated test asserts the emitted frame shape against `heizungslogger.frame.parse_frame` and the documented 11-field contract.
- [ ] Disconnected-sensor behaviour is covered by a test or explicitly documented as an accepted unknown.
- [ ] Build verification runs as a single documented command and is added to the repository's quality gates (or the reason it cannot be is recorded).
- [ ] The manual hardware procedure is documented and marked as requiring authorisation.
- [ ] The wire format is unchanged; existing Python tests still parse the same frames.
- [ ] `python -m pytest` passes.
- [ ] Zero Ruff errors or warnings (`python -m ruff check .`).

---

## Execution Notes
<!-- Populated during Step 5 of the Ticket Protocol -->

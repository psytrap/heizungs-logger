# Ticket 001: Behaviour-Preserving Refactor of the Logger for Testability

- **Status:** Done
- **Priority:** 🟠 High
- **Scope & Relevant Files:**
  - `heizungs_logger.py` (legacy script, becomes a thin entry-point shim)
  - `src/heizungslogger/` (new package: `frame.py`, `display.py`, `serial_link.py`, `runner.py`, `cli.py`)
  - `tests/` (new)
  - `pyproject.toml`, `.gitignore` (new)
  - `README.md`

---

## Description & Context

The current implementation is a single script that cannot be imported and therefore cannot be tested. It executes at import time:

```python
i2c = board.I2C()
lcd = character_lcd.Character_LCD_RGB_I2C(i2c, LCD_COLUMNS, LCD_ROWS)
args = parser.parse_args()          # at module scope
with serial.Serial(args.port, 9600, timeout=1) as ser:
```

Consequences:

- Importing the module on any machine without a Pi, without Blinka, or without `/dev/ttyUSB0` fails immediately.
- Frame parsing, LCD layout, scheduling, and file writing are interleaved in one `while True` block, so none of them can be exercised independently.
- There is no test harness at all: no `pyproject.toml`, no tests, no linter configuration.

This ticket extracts the logic into importable, injectable units **without changing observable behaviour**. It is a pure refactor: the serial protocol, the LCD rendering, the log file format, the file naming, the cadence, and the CLI surface must stay identical.

**Explicitly out of scope** (do not fix here, these are separate tickets):

- The scheduled-vs-actual timestamp defect and the `next = next + RATE` dead statement (statement may be dropped, its behaviour must not change).
- Robustness work: serial reconnect, frame validation policy, failure isolation of the LCD, watchdog supervision.
- Any change to the log record format or file naming.
- Any change to alerting or the (unused) pusher.

## Target Structure

| Module | Responsibility |
| :--- | :--- |
| `src/heizungslogger/frame.py` | `parse_frame(line)` → ordered field list; pure, no I/O |
| `src/heizungslogger/display.py` | `render(fields)` → `(row0, row1)`; pure. `LcdDisplay` wrapper with lazy hardware import |
| `src/heizungslogger/serial_link.py` | `SerialLink` protocol + pyserial implementation with lazy import |
| `src/heizungslogger/runner.py` | The acquisition loop, with injected link, display, clock and sleep |
| `src/heizungslogger/cli.py` | `argparse` surface and `main()` |
| `heizungs_logger.py` | Shim preserving the deployed `ExecStart` path |

Hardware libraries (`pyserial`, `board`, `adafruit_character_lcd`) must only be imported inside the hardware implementations, never at module scope of the package.

## Criteria

- [x] `import heizungslogger` succeeds on a machine with no `pyserial`, no `board`, no `adafruit_character_lcd` and no serial device.
- [x] Serial access, display access, clock and sleep are injectable; the runner can be driven by fakes.
- [x] `parse_frame` is pure and unit-tested for a valid frame, a short frame, an empty line, non-UTF-8 bytes, and extra whitespace.
- [x] `render` is pure, unit-tested, and reproduces the legacy column mapping exactly: row 0 → indices `1, 2, 6`, row 1 → indices `3, 4, 7`, at columns `0, 6, 12`.
- [x] The runner reproduces the legacy cadence and protocol: 3.0 s startup delay, write `b'x'`, flush, 5.0 s conversion delay, one `readline`, 20.0 s period.
- [x] For a given sample, the emitted log line is **byte-identical** to the legacy output (`str(list)` with the ISO timestamp appended) and the filename pattern `LOG-<local-date>.json` is unchanged.
- [x] CLI surface unchanged: `--list`, `--port`, `--log_directory`; missing `--port` prints the help and exits non-zero.
- [x] `python heizungs_logger.py --list` still runs from a checkout without a Pi.
- [x] `python -m pytest` is green on Python 3.12 without any hardware dependency installed.
- [x] `python -m ruff check .` reports zero errors.
- [x] `README.md` documents install, test, and run instructions including the hardware extras.
- [x] `git diff` shows no change to `heizungs_logger.ino` or `heizungs_logger.service`.

---

## Execution Notes

The script is split into six modules under `src/heizungslogger/`. Splitting was
taken one step further than the table above: `clock.py` (injectable time) and
`store.py` (line formatting, day-file naming, append) were separated out so
that neither the runner nor the CLI has to know how a record is rendered.

| Module | Content |
| :--- | :--- |
| `frame.py` | `parse_frame(raw)` — the legacy decode/strip/split chain |
| `display.py` | `render(fields, layout)` plus `LcdDisplay` (lazy `board`/`adafruit_character_lcd`) |
| `serial_link.py` | `SerialLink` protocol, `PyserialLink` (lazy `pyserial`), `list_ports()` |
| `clock.py` | `Clock` protocol, `SystemClock` (naive UTC + `time.sleep`) |
| `store.py` | `local_label`, `record_path`, `format_line`, `FileStore` |
| `runner.py` | `Runner.run()` / `Runner.sample(deadline)`, all collaborators injected |
| `cli.py` | `build_parser()`, `main(argv)` returning an exit status |

`heizungs_logger.py` is now a 17-line shim: it prepends `src/` to `sys.path`
and delegates to `cli.main()`, so the deployed `ExecStart` path keeps working
from the checkout.

### Deliberate deviations

- **Exit status for a missing `--port`.** The legacy `exit()` produced status
  `0`, which made a misconfigured start indistinguishable from success. The
  ticket requires non-zero, so `main()` returns `1`. Message and help output
  are unchanged.
- **The LCD is connected on first `show()`, not at import.** The legacy script
  built the I2C display at module scope, so even `--list` needed the panel.
  Lazy connection is what makes the package importable and testable; on the Pi
  the first cycle still connects before anything is drawn.
- **`str(ser.write(b'x'))` reduced to `ser.write(b'x')`.** The return value was
  already discarded; the call itself is unchanged.
- **`next = next + RATE` dropped.** Dead assignment at the end of the loop body,
  as permitted by the ticket.

Everything else is reproduced verbatim, including the naive-`utcnow()`
timestamp labelling (`store.local_label`), the single-space `split`, the
appended ISO string, the `str(list)` line format and the `LOG-<date>.json`
name. The dead statement's removal and the timestamp defect are documented in
`docs/RECORDING.md` and remain open for the format tickets.

### Tests

30 tests, no hardware: frame edge cases (valid, short, empty, non-UTF-8,
extra and repeated whitespace), render mapping and custom layout, short-frame
`IndexError`, `LcdDisplay` cell order against a fake panel, byte-exact log line
and filename under `TZ=Europe/Berlin`, protocol/cadence assertions on the
injected clock and link, `KeyboardInterrupt` → `SystemExit(0)`, CLI exit
status and port closing, and a subprocess import check that no hardware module
ends up in `sys.modules`.

### Verification

```text
$ .venv/bin/python -m pytest -q
30 passed in 0.13s

$ .venv/bin/python -m ruff check .
All checks passed!

$ .venv/bin/python heizungs_logger.py; echo "exit=$?"
No port defined

usage: heizungs_logger.py [-h] [--list] [--log_directory LOG_DIRECTORY] [--port PORT]
...
exit=1
```

`git diff --stat` shows no change to `heizungs_logger.ino` or
`heizungs_logger.service`.

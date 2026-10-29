# Ticket 001: Behaviour-Preserving Refactor of the Logger for Testability

- **Status:** Backlog
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

- [ ] `import heizungslogger` succeeds on a machine with no `pyserial`, no `board`, no `adafruit_character_lcd` and no serial device.
- [ ] Serial access, display access, clock and sleep are injectable; the runner can be driven by fakes.
- [ ] `parse_frame` is pure and unit-tested for a valid frame, a short frame, an empty line, non-UTF-8 bytes, and extra whitespace.
- [ ] `render` is pure, unit-tested, and reproduces the legacy column mapping exactly: row 0 → indices `1, 2, 6`, row 1 → indices `3, 4, 7`, at columns `0, 6, 12`.
- [ ] The runner reproduces the legacy cadence and protocol: 3.0 s startup delay, write `b'x'`, flush, 5.0 s conversion delay, one `readline`, 20.0 s period.
- [ ] For a given sample, the emitted log line is **byte-identical** to the legacy output (`str(list)` with the ISO timestamp appended) and the filename pattern `LOG-<local-date>.json` is unchanged.
- [ ] CLI surface unchanged: `--list`, `--port`, `--log_directory`; missing `--port` prints the help and exits non-zero.
- [ ] `python heizungs_logger.py --list` still runs from a checkout without a Pi.
- [ ] `python -m pytest` is green on Python 3.12 without any hardware dependency installed.
- [ ] `python -m ruff check .` reports zero errors.
- [ ] `README.md` documents install, test, and run instructions including the hardware extras.
- [ ] `git diff` shows no change to `heizungs_logger.ino` or `heizungs_logger.service`.

---

## Execution Notes
<!-- Populated during Step 5 of the Ticket Protocol -->

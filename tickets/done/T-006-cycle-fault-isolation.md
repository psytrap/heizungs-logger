# Ticket 006: Isolate Display and Frame Faults from the Acquisition Loop

- **Status:** Done
- **Priority:** High
- **Scope & Relevant Files:**
  - `src/heizungslogger/runner.py`
  - `src/heizungslogger/display.py`
  - `tests/test_runner.py`
  - `tests/test_display.py`
  - `docs/OPERATIONS.md` (failure-behaviour section)

---

## Description & Context

Raised after the first v2 deployment, following three questions: what happens with no display, with no temperature sensor, or when a single cycle fails. The verified answers today:

1. **A display fault stops data collection.** `Runner.sample()` calls `self.display.show(fields)` unguarded, before `store.append(...)`. With no LCD at I2C address 0x21 the call raises `OSError(121)`, the exception leaves `run()` (which catches only `KeyboardInterrupt`), the process exits, systemd restarts it, and the same failure repeats forever. Reproduced with fakes: the sample wrote **zero** records even though the frame had been read successfully, because the display update ran first.
2. **An empty or undecodable frame is fatal.** `readline()` returns `b""` on its 1 s timeout, `parse_frame(b"")` yields `['']`, and `display.show([''])` then raises `IndexError` — a transient timeout costs a process restart.
3. **An overrunning cycle is fatal for a silly reason.** If a cycle exceeds the 20 s budget the remaining time is negative and `time.sleep(-1)` raises `ValueError`.

Legacy had the same display coupling (it built the LCD at import), so none of this is a v2 regression — but the v2 package is where it can be fixed cheaply.

### Intended behaviour

- A **display** fault is a degraded mode, not an outage: the record is written first, the error is logged once, repeats are counted silently, recovery is logged, and the handle is dropped so the next cycle reconnects.
- A **frame** that is empty or undecodable is *rejected*: no record, one journal line, cadence preserved. This matches the reader contract in `docs/RECORDING.md` §4 (rejections are counted and logged, not written to the data file).
- A **transport** fault (serial open/write/read) still propagates and still restarts the process. That restart is the only reconnect mechanism the service has today; swallowing it would leave a dead port handle running forever. This must be stated explicitly, not silently changed.
- A late cycle sleeps zero instead of raising.

---

## Criteria

- [x] `store.append` happens before `display.show`, so a display fault can never cost a record.
- [x] A raising display does not terminate the sample, `run()` keeps looping, and the record is still written.
- [x] Only the first display failure and the recovery are emitted; intervening failures increment a counter.
- [x] On a display failure the display handle is dropped (`LcdDisplay.close()`) so the next cycle reconnects.
- [x] Empty and undecodable frames produce no record, no exception, and keep the 20 s cadence.
- [x] A negative remaining interval sleeps 0 rather than raising.
- [x] Transport exceptions still propagate unchanged (covered by a test that pins the behaviour).
- [x] `docs/OPERATIONS.md` documents the failure behaviour for display, sensor and transport faults.
- [x] `python -m pytest` passes.
- [x] Zero Ruff errors or warnings (`python -m ruff check .`).

---

## Execution Notes

### Change

`src/heizungslogger/runner.py`:

- `sample()` now ends with `store.append(...)` followed by `_show(fields)`; the display is updated last. Since `append` is a single buffered `print`, no partial record is possible.
- `_show()` contains display exceptions, logs only the transition into and out of the degraded state (`display unavailable: ...; continuing without it`, `display recovered after N failed update(s)`), counts repeats in `display_errors`, and drops the handle through `display.close()` if the object has one.
- `_parse()` rejects frames instead of letting them reach the display: `UnicodeDecodeError` → `undecodable`, no non-blank field → `empty`. Rejections increment `rejected_frames`, emit `rejected frame (<reason>): <first 80 bytes>`, and skip the record while still waiting for the deadline.
- `_wait_for()` clamps the remaining interval with `max(0.0, remaining)`.
- Transport calls (`reset_input_buffer`, `write`, `flush`, `readline`) are deliberately left unguarded, with the reason stated in the docstring: the systemd restart is the only way the port handle is recreated.

`src/heizungslogger/display.py`: added `close()`, which sets `_lcd = None` so the next `show()` reconnects through the normal lazy path.

### Behaviour differences from the legacy script

| Situation | Legacy | Now |
| :--- | :--- | :--- |
| Display raises | process dies at import or on first update | record written, LCD skipped, journal line once |
| Empty read | `IndexError` on `data[1]`, process dies | frame rejected, cadence kept, no record |
| Overrunning cycle | `ValueError` from `time.sleep(-n)` | sleeps 0 |
| Serial error | process dies | unchanged: process dies, systemd restarts |

No record content changed: the timestamp source, ordering of fields and `str(list)` rendering are untouched, and the rejected-frame path writes nothing at all.

### Tests

Eleven new cases in `tests/test_runner.py`, including a fault display that tracks `close()` calls, a shared event log proving `store` precedes `display`, an empty and an undecodable frame, a transport error pinned as propagating, and a late cycle. `FakeLink`/`FakeDisplay` gained `read_error`, `closes` and the `FlakyDisplay` variant. One expectation was corrected during the run: interrupting at the seventh sleep lands inside cycle 2's wait, so the loop-survival test interrupts at the eighth.

### Documentation

`docs/OPERATIONS.md` §6 is a fault table (display / frame / transport) with the journal strings to grep for, plus notes on the missing-sensor sentinels and the hardcoded `ttyUSB0`.

### Gates

```text
$ .venv/bin/python -m pytest -q          -> 56 passed
$ .venv/bin/python -m ruff check .       -> All checks passed
$ ./scripts/test-firmware.sh             -> 6 frame checks passed
```

Not deployed to the Pi in this ticket.

# Ticket 007: Restart the Logger After Five Minutes Without a Meaningful Frame

- **Status:** Done
- **Priority:** High
- **Scope & Relevant Files:**
  - `src/heizungslogger/runner.py`
  - `src/heizungslogger/cli.py`
  - `tests/test_runner.py`
  - `tests/test_cli.py`
  - `docs/OPERATIONS.md` (§6 failure behaviour)
  - `docs/RECORDING.md` (§4 rejected frames)

---

## Description & Context

A rejected frame is currently harmless by design (T-006): no record, one journal
line, cadence kept. The consequence, verified in the code, is that a *persistent*
frame fault is invisible:

- `Runner.sample()` returns `[]`, `run()` loops forever, and the process never
  exits — so `Restart=always` never fires and the only reconnect mechanism the
  service has (`close()` + fresh `serial.Serial` on the next start) is never
  used, even if the fault would clear after reopening the port.
- The day file simply stops growing; if the fault starts before the first good
  frame of a day, that day's file is never created.
- The LCD keeps showing the last good values, so the panel actively lies.
- `rejected_frames` lives only in memory; nothing escalates.

Transport faults already exit and restart (T-006, deliberately). A silent frame
fault is the one failure mode with no escalation at all.

### Intended behaviour

- If **5 minutes pass without a frame that produced a record**, the logger logs
  one line and exits **cleanly** (no traceback, port closed) with a non-zero
  status; systemd `Restart=always` brings it back after `RestartSec=10`, which
  recreates the serial handle.
- Any accepted frame resets the timer, including a frame accepted after 4m59s of
  silence.
- The rule is time-based, not a frame count, so it holds for any cadence.
- Rejected frames keep their T-006 behaviour until the limit is reached: no
  record, one journal line each, cadence preserved.
- Transport exceptions still propagate unchanged.
- Exit is a controlled shutdown, not a crash: the port is closed by the existing
  `finally` in `cli.main`.

---

## Criteria

- [x] `Runner.sample()` raises `FrameTimeout` once the elapsed time since the
      last accepted frame reaches `silence_limit` (default 300 s) after a
      rejected frame.
- [x] The timeout is emitted as one journal line before the exception, naming
      the elapsed seconds.
- [x] An accepted frame resets the timer, so an intermittent fault never trips it.
- [x] The timer starts at construction, so a logger that never sees a good frame
      restarts after the limit.
- [x] `silence_limit` is injectable for tests.
- [x] `cli.main` catches `FrameTimeout`, prints the reason, closes the port and
      returns 1 instead of printing a traceback.
- [x] Other exceptions still propagate (existing CLI behaviour unchanged).
- [x] `pytest`, `ruff` and `scripts/test-firmware.sh` pass.
- [x] `docs/OPERATIONS.md` and `docs/RECORDING.md` document the escalation.

---

## Execution Notes

### Change

`src/heizungslogger/runner.py`:

- `SILENCE_LIMIT = 300.0` and a `FrameTimeout(RuntimeError)` carrying the elapsed
  seconds, whose message is `no meaningful frame for Ns`.
- `Runner.__init__` takes `silence_limit=...` and records `_last_good =
  clock.now()`, so the five minutes start at process start even if no frame is
  ever accepted.
- `sample()` sets `_last_good` immediately after `store.append(...)`: the timer
  is anchored to the last *written record*, not to the last successful read.
- After a rejected frame and its deadline wait, `_check_silence()` compares the
  elapsed time with the limit, emits `no meaningful frame for Ns; requesting a
  restart` and raises `FrameTimeout`. The check lives only on the rejection
  path, so a healthy loop never consults it and the cadence is untouched.

`src/heizungslogger/cli.py`: `FrameTimeout` is caught inside the existing
`try/finally`, prints `no meaningful frame for Ns; exiting for a clean restart`,
returns 1 and still closes the port through `finally`. Every other exception
keeps propagating as before.

### Why time, not a frame count

Five minutes is 15 cycles at the current 20 s rate, but the requirement is
about wall-clock silence. A count would silently mean a different duration if
`--rate` changes or if cycles overrun; `clock.now()` keeps it at 5 minutes.

### Behaviour differences

| Situation | Before | Now |
| :--- | :--- | :--- |
| One rejected frame | no record, cadence kept | unchanged |
| 15 consecutive rejected cycles | silent, frozen LCD, no restart | one journal line, clean exit, systemd restart after 10 s |
| Good frame after 4m59s | n/a | unchanged; timer reset, no restart |
| Transport fault | propagate, restart | unchanged, and it wins before the silence limit |

No record content changed; the reject path still writes nothing.

### Tests

Six new cases: the 15-cycle trip (45 sleeps, exactly 300 s), the single log
line, a configurable limit, a good frame resetting the timer, `run()` not
swallowing the exception, and a CLI case asserting status 1, a closed port and
no traceback. `ManualClock` (a `FakeClock` whose `now()` follows its sleeps) was
added so a cycle costs its real 20 s in fake time.

### Documentation

`docs/OPERATIONS.md` §2 (§status-1 note) and §6 (fourth fault row, silence note,
grep pattern), `docs/RECORDING.md` §4 (bounded rejection streak), `README.md`
(run section).

### Gates

```text
$ .venv/bin/python -m pytest -q          -> 62 passed
$ .venv/bin/python -m ruff check .       -> All checks passed
$ ./scripts/test-firmware.sh             -> 6 frame checks passed
```

Not deployed to the Pi in this ticket.

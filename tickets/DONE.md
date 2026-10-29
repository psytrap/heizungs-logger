# ✅ Heizungslogger Completed Ticket Register

This document is the historical register of all completed and verified tickets. Ticket files live in [**`tickets/done/`**](done/) and keep their original identifier and slug.

- For ticket development workflow and the 7-step execution protocol, see [**`tickets/README.md`**](README.md).
- For the live index of active and backlog tickets, see [**`tickets/INDEX.md`**](INDEX.md).

---

## 1. 📜 Completed Tickets

| Ticket | Title | Priority | Completed | Summary |
| :---: | :--- | :---: | :---: | :--- |
| [**T-008**](done/T-008-web-seven-day-view.md) | Read-Only Web View of the Last Seven Days | 🔵 **Normal** | Stdlib `http.server` page over the day files: six SVG charts on 10-minute min/mean/max buckets, day-locked grid, pointer readout, 600 s self-reload, 192 KB for a week; separate `heizungs_web.service` on port 80 via `CAP_NET_BIND_SERVICE`, read-only and device-less |
| [**T-007**](done/T-007-silence-restart.md) | Restart the Logger After Five Minutes Without a Meaningful Frame | 🟠 **High** | 2026-10-29 | `FrameTimeout` raised after `SILENCE_LIMIT` (300 s) of rejected frames; timer anchored to the last written record; CLI exits status 1 with a journal line and a closed port instead of a traceback, so `Restart=always` recreates the serial handle |
| [**T-006**](done/T-006-cycle-fault-isolation.md) | Isolate Display and Frame Faults from the Acquisition Loop | 🟠 **High** | 2026-10-29 | Record written before the LCD update; display faults degrade instead of restarting; empty/undecodable frames rejected with cadence kept; negative waits clamped; transport errors still restart on purpose |
| [**T-005**](done/T-005-lcd-legacy-layout.md) | Restore the Legacy LCD Layout for Six-Temperature Frames | 🟠 **High** | 2026-10-29 | `DEFAULT_LAYOUT` back to the deployed cells (`0,5,10`; temperatures 1–3 / 4–6); tests pinned to a live v1b frame and to the `Input`-marker misfire |
| [**T-004**](done/T-004-firmware-test-strategy.md) | Testing Strategy for the Arduino Firmware (`heizungs_logger.ino`) | 🔵 **Normal** | 2026-10-29 | `firmware/frame.{h,cpp}` extracted; `g++` host test; fixtures shared with `parse_frame`; recorded that the checked-in sketch emits v1a while the live board emits six temperatures |
| [**T-003**](done/T-003-reevaluate-systemd-unit.md) | Re-evaluate the systemd Unit File | 🔵 **Normal** | 2026-10-29 | Unit rewritten (`Restart=always`, `RestartSec=10`, `StartLimitIntervalSec=0`, unbuffered stdout, three hardening directives, dead `TimeoutStartSec` removed); `scripts/install-service.sh`; `docs/OPERATIONS.md` |
| [**T-002**](done/T-002-json-recording-strategy-documentation.md) | Document the JSON Recording Strategy | 🔵 **Normal** | 2026-10-29 | `docs/RECORDING.md`: measured inventory, two legacy format generations, UTC-label timestamp defect, v2 record proposal, reader contract, open decisions |
| [**T-001**](done/T-001-refactor-for-testability.md) | Behaviour-Preserving Refactor of the Logger for Testability | 🟠 **High** | 2026-10-29 | `src/heizungslogger/` split into `frame`, `display`, `serial_link`, `clock`, `store`, `runner`, `cli`; entry-point shim; 30 hardware-free tests; byte-identical log lines |

---

## 2. 📌 Register Maintenance Rules

1. An entry is added only in step 6 of the protocol, after the criteria are checked off and the quality gates pass.
2. Every row links to the ticket file in `tickets/done/`; the file retains its `T-NNN-kebab-case-slug.md` name.
3. The `Completed` column records the local date of the completion commit.
4. Entries are appended in completion order and are never renumbered or removed. Superseded work is recorded in the ticket's `## Execution Notes`, not by editing history.

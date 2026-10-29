# ✅ Heizungslogger Completed Ticket Register

This document is the historical register of all completed and verified tickets. Ticket files live in [**`tickets/done/`**](done/) and keep their original identifier and slug.

- For ticket development workflow and the 7-step execution protocol, see [**`tickets/README.md`**](README.md).
- For the live index of active and backlog tickets, see [**`tickets/INDEX.md`**](INDEX.md).

---

## 1. 📜 Completed Tickets

| Ticket | Title | Priority | Completed | Summary |
| :---: | :--- | :---: | :---: | :--- |
| [**T-002**](done/T-002-json-recording-strategy-documentation.md) | Document the JSON Recording Strategy | 🔵 **Normal** | 2026-10-29 | `docs/RECORDING.md`: measured inventory, two legacy format generations, UTC-label timestamp defect, v2 record proposal, reader contract, open decisions |
| [**T-001**](done/T-001-refactor-for-testability.md) | Behaviour-Preserving Refactor of the Logger for Testability | 🟠 **High** | 2026-10-29 | `src/heizungslogger/` split into `frame`, `display`, `serial_link`, `clock`, `store`, `runner`, `cli`; entry-point shim; 30 hardware-free tests; byte-identical log lines |

---

## 2. 📌 Register Maintenance Rules

1. An entry is added only in step 6 of the protocol, after the criteria are checked off and the quality gates pass.
2. Every row links to the ticket file in `tickets/done/`; the file retains its `T-NNN-kebab-case-slug.md` name.
3. The `Completed` column records the local date of the completion commit.
4. Entries are appended in completion order and are never renumbered or removed. Superseded work is recorded in the ticket's `## Execution Notes`, not by editing history.

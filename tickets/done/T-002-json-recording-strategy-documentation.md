# Ticket 002: Document the JSON Recording Strategy

- **Status:** Done
- **Priority:** 🔵 Normal
- **Scope & Relevant Files:**
  - `docs/RECORDING.md` (new)
  - `README.md` (link to the new document)
  - `heizungs_logger.py` (read-only reference — no code changes in this ticket)

---

## Description & Context

The project writes measurement data to files named `LOG-YYYY-MM-DD.json`, but **the content is not JSON**. Each line is the Python `repr` of a list:

```
['Temp', '31.5', '27.9', '28.6', '26.0', '28.0', '16.0', 'Input', 'off', 'off', '2026-10-29T12:32:16.014499+01:00']
```

There is no written specification of what a record is, which position means which sensor, what the timezone rule is, or what a reader may assume. The only consumer of this data (`heizungs_pusher.py` on the Pi, unversioned and not in the repository) works around the format with `line.replace("'", '"')`.

Measured facts about the current corpus on the live Pi (`heizungs-logger`, `/home/ubuntu/heizungs_logger_logs`):

| Property | Observed value |
| :--- | :--- |
| Files | 1 385, one per local day, `LOG-YYYY-MM-DD.json` |
| Volume | 646 MB total, ~501 KB/day, ~2 260 lines/day at 20 s cadence |
| Line format | `str(list)`, 10 fields + 1 appended timestamp, single quotes |
| Timestamp | ISO-8601 with local offset, but the **scheduled** time, not the sample time |
| Encoding | UTF-8 nominally; at least four files contain non-UTF-8 bytes |
| Retention | None — nothing is rotated, compressed, or deleted |
| Consumer | No in-repo reader; no schema, no version field |

Decisions must be written down before the format is changed, so the format ticket has a single source of truth.

## Criteria

- [x] `docs/RECORDING.md` inventories the **current** behaviour above with the measured numbers, including the explicit warning that the `.json` extension is misleading.
- [x] It states the storage constraint plainly: **plain files only, no database**, append-only, one record per line.
- [x] It defines the canonical record for future writes as a proposed schema: JSON object per line, UTF-8, schema/version field, UTC timestamp with explicit offset, sequence number, named sensor values with units, input/relay states — with a short worked example.
- [x] It documents the timezone rule (storage in UTC, rendering in local time) and how a record's day file is chosen.
- [x] It documents file naming and rollover rules, and states whether the extension stays `.json` or becomes `.jsonl`.
- [x] It documents what a reader must tolerate: torn final line, corrupt bytes, missing days, and the legacy `repr` format.
- [x] It documents compatibility policy: legacy files are never rewritten in place and remain readable by the new reader.
- [x] It contains an **Open Decisions** section listing every point that still needs maintainer sign-off (extension, field names, cadence, retention default), each with a recommendation and the alternatives.
- [x] `README.md` links to `docs/RECORDING.md`.
- [x] No source code, deployment, or log file is modified by this ticket.

---

## Execution Notes

**Deliverables:** `docs/RECORDING.md` (new, 9 sections), `README.md` (documentation and layout sections added). No source file, unit, or log file touched.

**Evidence gathered from the live Pi** (`heizungs-logger`, read-only SSH; nothing written):

- Corpus scan over all 1 385 files: 667.2 MB raw, span 2022-10-14 → 2026-10-29 (1 477 days), **92 missing days** (80 in 2023, 12 in 2024), median file size 500 888 B, max 502 860 B.
- **Two undocumented format generations**, cleanly separated with no mixed files: v1a = 9 fields (4 temperatures), 380 files, 2022-10-14 → 2024-01-16; v1b = 11 fields (6 temperatures), 1 005 files, 2024-01-20 → 2026-10-29. The cutover coincides with the logger rewrite on the Pi (file mtime 2024-01-20).
- **Timestamp defect confirmed and quantified**: at wall clock `13:57:13+0100` the newest record read `12:56:56+01:00`; the last record of `LOG-2026-10-28.json` is `23:59:58+01:00` while that file's mtime is `00:59:58` local on 2026-10-29. Root cause: `utcnow()` returns a naive UTC value, and `astimezone()` on a naive datetime assumes local time, so only the offset label is attached and the clock value stays UTC. Consequence: every stored instant is 1 h (winter) / 2 h (summer) earlier than reality, and **day files are UTC days**.
- Corruption characterised: exactly 4 files contain a single NUL-filled run (116 B, 116 B, 116 B, 232 B) — valid UTF-8, so a naive decode passes, but the data is not parseable. Earlier `grep` "binary file" reports had the same cause.
- Cadence verified on a complete day: 4 319 records, median interval 20.005 s, no interval > 40 s, no duplicate timestamps.

**Quality gates:**

- `python -m pytest` → exit 5, "no tests ran". No test suite exists yet; creating it is T-001.
- `python -m ruff check .` → exit 1, **7 findings, all in the untouched legacy `heizungs_logger.py`** (unsorted imports, unused `json`, `str.format`, two `exit()` calls, two `utcnow()` calls). No finding originates from this ticket. Fixing them belongs to T-001, which also introduces the `pyproject.toml` holding the lint configuration.

**Follow-ups surfaced (not created, awaiting instruction):** the v1a/v1b generation split and the UTC-label defect are both material enough to justify their own tickets.

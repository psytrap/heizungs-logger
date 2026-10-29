# 📊 JSON Recording Strategy

Status: proposal, pending maintainer sign-off on the items in §8 Open Decisions.

This document is the single source of truth for how measurement data is written to disk by the heating logger. It records what the system does **today** (measured, not assumed), states the hard constraints, proposes the record format for future writes, and lists the decisions that still need a human verdict.

---

## 1. 🛡️ Hard Constraints

1. **Plain files only.** Measurement data lives in plain text files on the Raspberry Pi's SD card. No database, no daemon, no external service is involved in acquisition or storage.
2. **Append-only.** A record, once written, is never rewritten. Corrections happen in readers, not in files.
3. **No acquisition dependency on the network.** Recording must keep working with the LAN and the internet down.
4. **Legacy data is read-only.** The existing corpus (2022-10-14 → today) is never modified in place.
5. **One record per line.** Each sample is exactly one line, so a torn write can only damage the last line of a file.

---

## 2. 📁 Current On-Disk Reality

Measured on `heizungs-logger` in `/home/ubuntu/heizungs_logger_logs` on 2026-10-29.

### 2.1 Corpus

| Property | Value |
| :--- | :--- |
| Files | 1 385 (`LOG-YYYY-MM-DD.json`) |
| Volume | 667.2 MB raw (646 MiB by `du`) |
| Span | 2022-10-14 → 2026-10-29 (1 477 calendar days) |
| Missing days | 92 (80 in 2023, 12 in 2024) — no file at all |
| File size | median 500 888 B, max 502 860 B (a complete day is ~4 319 lines) |
| Cadence | 20.005 s median interval in a sampled full day; no interval > 40 s; no duplicate timestamps |
| Line counts | 4 319 lines for 2026-10-28, 3 629 for 2022-10-14 |

### 2.2 File naming

`LOG-<date>.json`, where `<date>` is **not** the local calendar day — see [§3.2](#32-day-boundaries-are-utc-days).

### 2.3 Line format

Every line is the Python `repr` of a list, **not JSON**, despite the `.json` extension:

```
['Temp', '31.5', '27.9', '28.6', '26.0', '28.0', '16.0', 'Input', 'off', 'off', '2026-10-29T12:32:16.014499+01:00']
```

Fields are positional and unlabelled. All values are strings. The timestamp is appended by the logger after the device frame is split on spaces.

### 2.4 Format generations in the corpus

The record shape changed on the Pi without any version marker in the data:

| Generation | Field count | Layout | Files | Date range |
| :--- | :---: | :--- | :---: | :--- |
| v1a | 9 | `Temp`, 4 × temperature, `Input`, 2 × state, timestamp | 380 | 2022-10-14 → 2024-01-16 |
| v1b | 11 | `Temp`, 6 × temperature, `Input`, 2 × state, timestamp | 1 005 | 2024-01-20 → 2026-10-29 |

No file mixes generations; the cutover falls into a three-day gap (2024-01-17 → 2024-01-19). A reader that assumes a fixed field count breaks on roughly a quarter of the corpus.

### 2.5 Encoding and corruption

Files are UTF-8 in the normal case. Four files contain NUL-filled regions instead of text — a classic SD-card or power-loss hole:

| File | NUL bytes | Longest NUL run |
| :--- | :---: | :---: |
| `LOG-2024-05-24.json` | 116 | 116 |
| `LOG-2024-06-16.json` | 116 | 116 |
| `LOG-2025-01-31.json` | 116 | 116 |
| `LOG-2025-12-23.json` | 232 | 232 |

They are valid UTF-8 and therefore pass a naive decode, but they are not parseable records. Readers must discard them.

---

## 3. 🐞 Known Defects in the Current Record

These are properties of the data as written today. They are documented here so readers can compensate and so the format ticket can decide what to fix.

### 3.1 Timestamps carry a UTC clock value with a local offset label

The writer computes `next = datetime.utcnow() + 20 s` (naive UTC), then calls `next.astimezone(tzlocal)`. Because the value is naive, Python assumes it is already local time and only attaches the local offset — it does not convert.

Result: the clock value is UTC, the label is local. The recorded instant is therefore **1 hour (winter) or 2 hours (summer) earlier than reality**.

Evidence:

| Source | Value |
| :--- | :--- |
| Wall clock at check | `2026-10-29T13:57:13+0100` |
| Newest record at that moment | `2026-10-29T12:56:56+01:00` |
| Last record of `LOG-2026-10-28.json` | `23:59:58+01:00` |
| File mtime of `LOG-2026-10-28.json` | `2026-10-29T00:59:58` (local) |

**Reader rule:** for v1a and v1b records, take the clock fields literally and interpret them as **UTC**, ignoring the offset label. Do not apply an offset conversion — the value is already UTC.

### 3.2 Day boundaries are UTC days

Because the value in §3.1 is unaffected by the conversion, the date used for the file name is the **UTC** date. A file named `LOG-2026-10-28.json` therefore holds `2026-10-28T00:00Z` → `2026-10-28T23:59Z`, which is `01:00` local on the 28th to `00:59` local on the 29th (winter; `02:00` → `01:59` in summer).

### 3.3 The timestamp is the scheduled time, not the sample time

The value written is computed **before** the serial request and the 5 s conversion wait, then the record is written ~20 s later. Sample time and record time differ by up to the conversion delay.

### 3.4 No schema marker, no units, no sensor names

Nothing in a record identifies the generation, the unit (°C is assumed, never stated), or which physical sensor a position corresponds to. The mapping exists only in the Arduino firmware.

### 3.5 No version history

There is no record of which software version or firmware produced a given file.

---

## 4. 📝 Proposed Record Format (v2)

Proposal for future writes only. Nothing in this section is implemented yet.

One JSON object per line, UTF-8, newline-terminated:

```json
{"v":2,"ts":"2026-10-29T11:56:56.514910Z","seq":1234567,"temps":{"t1":29.6,"t2":27.1,"t3":27.9,"t4":25.4,"t5":27.2,"t6":16.1},"inputs":{"in1":false,"in2":false},"meta":"a1b2c3d4"}
```

| Field | Type | Meaning |
| :--- | :--- | :--- |
| `v` | integer | Schema version, currently `2` |
| `ts` | string | Sample completion time, ISO-8601, **UTC with `Z`** |
| `seq` | integer | Monotonically increasing within a process run; restarts are visible as a decrease |
| `temps` | object | Named temperatures in °C; names are config-driven, not positional |
| `inputs` | object | Boolean input/relay states |
| `meta` | string | Short hash of the configuration in effect (sensor names, thresholds, software version) |

Design notes:

- **Named, not positional.** Adding or removing a sensor must not silently reinterpret old data.
- **UTC with `Z`.** Local rendering is a display concern. A `Z` timestamp has exactly one meaning and no DST ambiguity.
- **`seq`** makes dropped samples and restarts detectable without a separate heartbeat record.
- **Unknown fields are preserved** by writers, so a newer writer does not corrupt data for an older reader.
- A **rejected frame produces no record.** Rejections are counted and logged to the journal, not into the data file.
- A **rejection streak is bounded:** five minutes without an accepted frame ends the process so the service restarts with a fresh serial handle (see [`OPERATIONS.md`](OPERATIONS.md) §6). A streak therefore shows up as a gap in the day file plus a restart, never as a silently frozen logger.

### 4.1 Day metadata sidecar

When a day file is created, write `LOG-<date>.meta.json` once, containing sensor names and units, device identity, firmware label, and software version. This makes the file self-describing years later without repeating metadata on every line.

---

## 5. 🗂️ File Naming, Rollover and Retention

Proposed rules for v2:

1. **Boundary:** roll over at **local midnight**, using the corrected timestamp. This differs from today's UTC-day behaviour ([§3.2](#32-day-boundaries-are-utc-days)) and must be decided consciously, since it changes which file a sample lands in.
2. **Naming:** `LOG-YYYY-MM-DD.jsonl` (see §8 for the extension decision).
3. **Transition day:** any change to the boundary rule creates one day whose length is not 24 h. That day must be recorded explicitly at cutover.
4. **Retention:** uncompressed for a configurable recent window, gzip beyond it, deletion only when explicitly configured and always logged. Nothing is deleted by default.

---

## 6. 🧪 Reader Tolerance Contract

Any reader of the log directory must satisfy all of the following:

1. Accept **three** record shapes: v1a (9 fields), v1b (11 fields), v2 (JSON object).
2. Never raise on malformed input. Skip the line, count it, and report the count and location.
3. Handle a **torn final line** (no trailing newline) as a normal condition — the writer was interrupted.
4. Discard NUL-filled regions ([§2.5](#25-encoding-and-corruption)) without aborting the file.
5. Interpret v1a/v1b timestamps as UTC ([§3.1](#31-timestamps-carry-a-utc-clock-value-with-a-local-offset-label)).
6. Treat missing day files as gaps, not as errors. 92 such days already exist.
7. Tolerate field-count changes over time and report the generation it detected.

---

## 7. 🔁 Compatibility & Migration Policy

1. **No in-place rewrite** of legacy files. Historical records are immutable.
2. **No bulk conversion** is required to keep reading the corpus; the reader handles legacy shapes natively.
3. **Optional normalisation** (export to v2 JSONL into a separate directory) is allowed for analysis, but the export is derived data and never the authoritative store.
4. **Writers never emit v1a/v1b again.** Once v2 ships, new data is v2 only.
5. **The offset defect is not backfilled.** Correcting four years of timestamps by rewriting them would destroy the ability to audit the original. Instead the defect is encoded as a reader rule (§3.1) and stated in every converted record's provenance.

---

## 8. ⚖️ Open Decisions

Each item needs an explicit maintainer verdict before the format is implemented.

| # | Decision | Recommendation | Alternative |
| :---: | :--- | :--- | :--- |
| 1 | File extension | `.jsonl` — accurate, since content is JSON Lines | Keep `.json` for compatibility with existing tooling |
| 2 | Sensor names (`t1`…`t6`) | Name them in config with the real physical meaning (flow, return, buffer top/bottom, outside, room) | Keep positional `t1`…`t6` |
| 3 | Sample cadence | Keep 20 s — 4 319 lines/day is already dense | Rate-limited change-of-value logging |
| 4 | Day boundary | Local midnight (matches human reading of "today") | Keep UTC days, consistent with the corpus |
| 5 | Retention default | Keep everything; compression after 90 days | Delete after N years |
| 6 | Uncompressed window | 90 days | 30 days |
| 7 | Sidecar metadata | One `.meta.json` per day, written once | Repeat metadata in every record |
| 8 | Units | °C implied for all six channels | Add per-channel units in config |

---

## 9. 📚 Related

- Ticket T-001 — refactor for testability (prerequisite for any writer change).
- `heizungs_logger.py` — current writer.
- `heizungs_logger.ino` — firmware that defines the field order and count.

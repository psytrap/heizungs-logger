# Ticket 008: Read-Only Web View of the Last Seven Days

- **Status:** Done
- **Priority:** Normal
- **Scope & Relevant Files:**
  - `src/heizungslogger/web.py` (new: loader, summaries, HTML rendering)
  - `src/heizungslogger/web_server.py` (new: stdlib HTTP handler + CLI)
  - `tests/test_web.py` (new)
  - `heizungs_web.service` (new unit) and `scripts/install-web.sh` (or an
    `--web` mode in `scripts/install-service.sh`)
  - `docs/OPERATIONS.md` (§7 web view), `README.md`

---

## Description & Context

There is no way to look at the recorded data without SSH. The request is a
*single* read-only page showing the last seven days, reloading itself every ten
minutes, with no client-side framework and no live updates.

Constraints that follow from the project:

- **Read-only.** The web process never opens a day file for writing, never
  starts or stops the logger, and never touches the serial port.
- **Plain files only.** The source of truth is `LOG-<date>.json`; no index,
  no database, no cache file.
- **Separate process.** A web bug must not be able to stop collection, so it
  runs as its own unit rather than inside `Runner`.
- **No new runtime dependencies.** Python 3.10 stdlib only (`http.server`,
  `ast`, `datetime`), so nothing new has to be installed on the Pi.

### Data-shape reality the reader must handle

1. **Day files are UTC days with a local-looking name.** `record_path()` names
   the file from a naive UTC value (defect §3.1/§3.2 of `RECORDING.md`). The
   seven-day window therefore has to be computed in **UTC**; computing it from
   `datetime.now()` would drift by one or two hours at the boundary and read a
   file that does not exist yet.
2. **Timestamps inside are UTC values carrying a local offset label.** The page
   should parse the last field, ignore the offset, treat the value as UTC, and
   render it in the Pi's local timezone. That corrects the display without
   changing the record format.
3. **Records are Python list literals**, not JSON, despite the `.json` name.
   Parse with `ast.literal_eval`, never `eval`.
4. **The last line may be mid-append.** `FileStore.append` opens, prints and
   closes per record, so this is unlikely, but a truncated trailing line must be
   skipped rather than crash the request.
5. **Line counts.** ~4 300 records/day × 7 ≈ 30 000 lines, ~2–4 MB. Fine to
   read per request, but worth a small `(path, mtime, size)` cache so a browser
   reload does not re-parse when nothing changed.

### Proposed design

- **One page**, `GET /`, server-rendered HTML, `<meta http-equiv="refresh"
  content="600">`. No JavaScript at all.
- **Header line** answering "is it alive": newest record's local time, age of
  that record, record count in the window, and the number of missing
  20 s slots per day (gap count), so a silent failure is visible at a glance.
- **Charts only** — no tables, confirmed by the request.
- **Six temperature series** (count derived from the frame, not hardcoded) as
  inline `<svg>` polylines, one chart per sensor, labelled `T1`…`T6` for now.
  Points are 10-minute min/avg/max buckets: 1 008 buckets per series, about one
  per pixel at the rendered width, so nothing is lost to the screen and the page
  stays around a third of a megabyte.
- **X axis locked to days:** a fixed seven-column grid, a vertical rule and a
  `dd.mm` label at every local midnight, so one column is one day of the house.
- **Pointer readout:** a vanilla-JS crosshair (~50 lines, no library) snaps to
  the nearest bucket and prints `dd.mm hh:mm  27.3 °C (min 26.9, max 27.5)`.
  Snapping is required: at 1 008 buckets a hover band is about one pixel wide,
  so native `<title>` tooltips would be unusable.
- **One status line** above the charts: newest sample's local time, its age,
  the window's record count and the number of empty buckets, so a silent freeze
  is visible without reading a chart.

### Deliberately out of scope

- Authentication, TLS, internet exposure. The page is for the LAN; bind and
  port are configuration.
- Any database, aggregation job, or generated HTML file on disk.
- Live/streaming updates, alerting, historical queries beyond the fixed window.

---

## Decisions (from review)

1. **Bind `0.0.0.0:80`**, LAN access. Port 80 needs `CAP_NET_BIND_SERVICE`; the
   unit grants exactly that ambient capability instead of running as root.
2. **Labels `T1`…`T6`** for now. Real sensor names stay an open decision in
   `RECORDING.md` §8; they will be a config change, not a code change.
3. **Charts only.** No per-day table, no last-record table.
4. **X axis grid locked to days**, vertical rule and label at each local
   midnight inside the window.
5. **Separate `heizungs_web.service`** rather than a second process in the
   logger unit: failure isolation, independent restarts, and a sandbox the
   logger cannot have (read-only filesystem, no device access).

Pointer behaviour: hovering a chart moves a crosshair to the nearest 10-minute
bucket and prints the time and value inline. Implemented with plain JavaScript
in the page, no library, and it degrades to a static chart if scripting is off.

---

## Criteria

- [x] `GET /` renders the last seven days from the day files, with no writes and
      no new dependency.
- [x] Six charts, one per temperature, 10-minute min/avg/max buckets, x axis
      gridded and labelled at every local midnight.
- [x] Hovering a chart shows time, mean, min and max for the nearest bucket.
- [x] The page reloads itself every 600 s via `<meta http-equiv="refresh">`.
- [x] Non-record lines, undecodable lines and a truncated final line are skipped
      without an error.
- [x] The loader is hardware-free and tested against fixture files, including a
      missing-day file and a directory with records on one day only.
- [x] Timestamps are rendered in local time, converted from the UTC values in the
      files, and the conversion is documented.
- [x] The response carries `Content-Type: text/html; charset=utf-8` and
      `Cache-Control: no-store`.
- [x] A missing log directory returns an explanatory page with status 503, not a
      traceback.
- [x] `pytest`, `ruff` and `scripts/test-firmware.sh` pass.
- [x] `docs/OPERATIONS.md` documents the unit, the port, and the read-only
      guarantee; `README.md` links to it.
- [x] Charts only, port 80, labels `T1`…`T6`, day-locked grid, separate unit —
      the five review decisions.

---

## Execution Notes

### Files

| File | Role |
| :--- | :--- |
| `src/heizungslogger/web.py` | Pure loader, bucketing, SVG and page rendering |
| `src/heizungslogger/web_server.py` | `http.server` adapter, page cache, CLI |
| `tests/test_web.py` | 13 cases over fixture day files |
| `heizungs_web.service` | Second unit, port 80 via `CAP_NET_BIND_SERVICE` |
| `scripts/install-web.sh` | install / refresh / uninstall, same shape as the logger installer |

### Data handling

- `parse_line` uses `ast.literal_eval`, returns `None` for anything that is not
  a list, and drops a truncated final line instead of raising.
- `parse_moment` keeps the literal clock value and discards the offset label:
  the writer stores UTC values labelled with the local offset, so converting
  would subtract an hour. This is documented in the ticket and in §7 of
  `OPERATIONS.md`.
- The window is seven UTC days from `window_start`, built with the existing
  `store.record_path`, so the viewer can never disagree with the writer about a
  filename.
- `sensor_count` takes the dominant temperature count, so a mixed corpus still
  renders one chart per sensor instead of splitting or crashing.

### Rendering

- 10-minute buckets: seven days is 1 008 buckets, roughly one per pixel at the
  rendered width, and each holds ~30 samples reduced to min/mean/max. The
  synthetic 7-day render (28 531 records) is 192 KB of HTML.
- Gaps break the polyline instead of drawing a straight line across them.
- The overlay payload is a single JSON block (`labels` + per-sensor
  `[mean, low, high]`); the readout script snaps the pointer to the nearest
  non-empty bucket within 40 steps and hides itself when there is nothing near.
- Without JavaScript the charts still render; only the readout is absent.

### Caching

`App.page()` keys the built HTML on `(path, mtime_ns, size)` of the seven day
files and rebuilds when the signature changes or 60 s have passed. A 10-minute
browser reload therefore costs one parse, not six.

### Behaviour outside the happy path

| Situation | Response |
| :--- | :--- |
| Log directory missing | `503` with the path, no traceback |
| Fewer than seven day files | renders the days that exist, gaps elsewhere |
| No parsable record | status line says so, charts say `nothing to plot yet` |
| Port 80 without the capability | clear message on stdout, exit 1 |
| Path other than `/` | `404` |

### Gates

```text
$ .venv/bin/python -m pytest -q          -> 76 passed (14 new)
$ .venv/bin/python -m ruff check .       -> All checks passed
$ ./scripts/test-firmware.sh             -> 6 frame checks passed
$ install-web.sh --dry-run               -> unit parsing and warnings correct
```

Synthetic render: 28 531 records, 6 charts, 192 149 bytes. Not deployed yet.

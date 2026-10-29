# Ticket 003: Re-evaluate the systemd Unit File

- **Status:** Done
- **Priority:** Normal
- **Scope & Relevant Files:**
  - `heizungs_logger.service`
  - `scripts/install-service.sh` (new)
  - `docs/` (new operations note, if the review concludes one is warranted)

---

## Description & Context

The unit file in the repository has not been reviewed since the v1 era and was copied verbatim to the live Pi. This ticket is a **review and proposal** ticket: inspect the current unit against what the service actually needs, record every finding with a recommendation, and only then change the file.

The repo copy (`heizungs_logger.service`) currently reads:

```ini
[Unit]
Description = Heizungslogger
After = network.target

[Service]
Type = simple
ExecStart = python3 /home/ubuntu/heizungs_logger/heizungs_logger.py --port /dev/ttyUSB0 --log_directory /home/ubuntu/heizungs_logger_logs
User = ubuntu
Group = ubuntu
Restart = on-failure
SyslogIdentifier = heizungs_logger.py
RestartSec = 5
TimeoutStartSec = infinity

[Install]
WantedBy = multi-user.target
```

Findings to evaluate (record a verdict and a recommendation for each — do not assume any of them must change):

1. **Interpreter:** `python3` is ambient; there is no pinned interpreter, no virtualenv, and no dependency manifest wiring. Compare against the `src/` layout and the `pyproject.toml` extras introduced in T-001.
2. **Entry point:** `ExecStart` targets the `sys.path` shim `heizungs_logger.py` rather than the package entry point. Decide whether the shim remains the deployment contract.
3. **`TimeoutStartSec = infinity`:** has no useful effect for `Type=simple`. Confirm and recommend removal or replacement.
4. **`Restart = on-failure`:** does not restart after a clean exit or a watchdog timeout. Evaluate `Restart = always` and the resulting restart-storm risk when `/dev/ttyUSB0` is absent or re-enumerated.
5. **`RestartSec = 5`** without `StartLimitBurst` / `StartLimitIntervalSec`: unbounded rapid restart loop when the USB adapter is missing.
6. **No `WatchdogSec`:** no liveness supervision beyond process exit (relates to the already-known supervision gap; this ticket only records the option, it does not implement it).
7. **No `WorkingDirectory`:** relative-path behaviour is undefined if anything ever writes a relative path.
8. **`After = network.target`:** the logger does not use the network. Note the correct ordering if the USB device or a mount ever needs to precede startup.
9. **No journald / stdout policy:** `StandardOutput`, `StandardError`, rate limiting, and whether the journal is the intended diagnostics sink alongside the JSONL files.
10. **No hardening directives:** `NoNewPrivileges`, `ProtectSystem`, `PrivateTmp`, `ProtectHome` trade-offs, given that the service must write to `/home/ubuntu/heizungs_logger_logs`.
11. **Syntax nits:** whitespace around `=` (tolerated, but inconsistent with systemd convention) and the stray trailing comment in `[Install]`.
12. **Drift:** the deployed unit on the Pi may differ from the repo copy. Inspect it read-only (`systemctl cat`, `systemctl show`) and note any divergence.

The installed unit on the Pi is production. Reading it is in scope; installing, restarting, stopping, or reloading it is **not** — that needs explicit maintainer authorisation.

### Deliverable: install script

Add `scripts/install-service.sh` that installs the unit file from this repository in a reproducible, idempotent way. It must:

- run as root or via `sudo`, and refuse clearly otherwise,
- copy `heizungs_logger.service` to `/etc/systemd/system/heizungs_logger.service`,
- run `systemctl daemon-reload` and `systemctl enable` (and only *offer* `restart`, never perform it implicitly),
- be dry-run capable (`--dry-run`) and support `--uninstall`,
- verify the target paths (`ExecStart` script, log directory, device) exist and warn instead of failing silently,
- be `sh`/POSIX or `bash` with `set -eu`, no `$(...)` interpolation in documented agent usage, and shellcheck-clean if shellcheck is available.

---

## Criteria

- [x] Deployed unit inspected read-only and compared with the repository copy; drift recorded.
- [x] Each finding 1–11 marked as *keep*, *change*, or *out of scope*, with a one-line rationale.
- [x] A concrete proposed unit file is included in `## Execution Notes` (or in an operations note under `docs/`).
- [x] Every proposed directive is justified by an observed behaviour of the application, not by generic hardening advice.
- [x] Any item that needs code or runtime support (watchdog, USB ordering, venv) is named as follow-up work and **not** silently implemented.
- [x] `scripts/install-service.sh` exists, is executable, idempotent, supports `--dry-run` and `--uninstall`, and does not restart the service without explicit confirmation.
- [x] The script is exercised in `--dry-run` mode locally without touching the filesystem outside the repository.
- [x] No change is deployed to the Pi in this ticket.
- [x] `python -m pytest` passes.
- [x] Zero Ruff errors or warnings (`python -m ruff check .`).

---

## Execution Notes

### Inspection

`systemctl cat` on the Pi shows the deployed unit is **byte-identical** to the repository copy (13 Oct 2022, 535 bytes) — no unit drift. `systemctl show` confirms the effective values: `Restart=on-failure`, `RestartUSec=5s`, `TimeoutStartUSec=infinity`, `WatchdogUSec=0`.

There is **entry-point drift**, however: the deployed `/home/ubuntu/heizungs_logger/heizungs_logger.py` is 2 722 bytes dated 20 Jan 2024 and contains no `sys.path` handling, i.e. it is the v1 monolith, not the shim in this repository. Installing the new unit alone would not deliver the v2 package; the installer warns about exactly this.

### Verdicts

| # | Finding | Verdict | Rationale |
| :---: | :--- | :--- | :--- |
| 1 | Ambient `python3` | **Keep**, now absolute | The runtime package is standard-library only; a venv adds a moving part with no current benefit. Absolute `/usr/bin/python3` removes PATH ambiguity. |
| 2 | `ExecStart` targets the shim | **Keep** | The shim is the deployment contract and keeps `ExecStart` stable across the v2 move. |
| 3 | `TimeoutStartSec=infinity` | **Remove** | Applies to startup readiness of `Type=oneshot`/`notify`, not to `Type=simple`; it was a no-op. |
| 4 | `Restart=on-failure` | **Change to `always`** | The runner can exit cleanly (schedule slip, future `--once` mode); `on-failure` would leave collection stopped silently. |
| 5 | `RestartSec=5`, no start limit | **Change to `RestartSec=10`, `StartLimitIntervalSec=0`** | Ten seconds is long enough not to hammer a missing adapter; unbounded retries are deliberate, because the default five-attempts-then-give-up would end logging until a human notices. |
| 6 | No `WatchdogSec` | **Out of scope** | Needs `sd_notify` in the application; recorded as follow-up in `docs/OPERATIONS.md` §5. |
| 7 | No `WorkingDirectory` | **Add** | Any future relative path now has a defined base. |
| 8 | `After=network.target` | **Keep** | Harmless and historically accurate; the logger needs no network, and device ordering is left to the restart loop because `After=dev-ttyUSB0.device` would not wait without a `Wants=`. |
| 9 | No journal policy | **Add explicit journal + `PYTHONUNBUFFERED=1`** | Python block-buffers stdout when it is not a terminal, so `print` output would reach the journal late or at exit. Retention stays with journald defaults. |
| 10 | No hardening | **Add `NoNewPrivileges`, `PrivateTmp`, `ProtectSystem=full`** | Safe: the process writes only under `/home/ubuntu`. `ProtectHome` is deliberately left unrestricted because the log directory lives there. |
| 11 | Syntax nits | **Normalise** | `Description=` without padding, comments moved out of `[Install]`, consistent `Key=Value`. `SyslogIdentifier=heizungs_logger.py` is kept so historical journal queries still match. |

### Resulting unit

`heizungs_logger.service` now reads:

```ini
[Unit]
Description=Heizungslogger (heat pump temperature logger)
Documentation=file:///home/ubuntu/heizungs_logger/README.md
After=network.target
StartLimitIntervalSec=0

[Service]
Type=simple
WorkingDirectory=/home/ubuntu/heizungs_logger
ExecStart=/usr/bin/python3 /home/ubuntu/heizungs_logger/heizungs_logger.py --port /dev/ttyUSB0 --log_directory /home/ubuntu/heizungs_logger_logs
User=ubuntu
Group=ubuntu
Environment=PYTHONUNBUFFERED=1
Restart=always
RestartSec=10
SyslogIdentifier=heizungs_logger.py
StandardOutput=journal
StandardError=journal
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=full

[Install]
WantedBy=multi-user.target
```

### Install script

`scripts/install-service.sh` (POSIX `sh`, `set -eu`):

- refuses to run without root unless `--dry-run` is given;
- parses `ExecStart` out of the unit and warns when the interpreter, entry-point script, log directory or device is missing, and when the deployed entry point does not contain `sys.path` (the v1/v2 drift above);
- copies the unit, `daemon-reload`, `enable`, and only restarts with an explicit `--restart`;
- `--uninstall` disables, stops, removes the unit and reloads — never touching log files;
- `UNIT_DIR` and `SYSTEMCTL` are overridable, which is how the dry run below was exercised without touching `/etc`.

```text
$ UNIT_DIR=/tmp/t3 SYSTEMCTL=/tmp/t3/systemctl ./scripts/install-service.sh --dry-run --restart
warning: ExecStart script not found: /home/ubuntu/heizungs_logger/heizungs_logger.py
         the repository ships heizungs_logger.py; deploy it to that path first
...
  would run: cp .../heizungs_logger.service /tmp/t3/heizungs_logger.service
  would run: /tmp/t3/systemctl daemon-reload
  would run: /tmp/t3/systemctl enable heizungs_logger.service
  would run: /tmp/t3/systemctl restart heizungs_logger.service
$ ./scripts/install-service.sh --nope
error: unknown argument: --nope (try --help)        # exit 1
```

The warnings for the log directory and `/dev/ttyUSB0` are expected off-Pi. `shellcheck` is not installed in this environment, so the script was not linted with it.

### Documentation

`docs/OPERATIONS.md` records install usage, the restart-semantics table, inspection commands, the hardening trade-off around `ProtectHome`, and the three things the unit does **not** cover (watchdog, device ordering, log retention).

### Gates

```text
$ .venv/bin/python -m pytest -q          -> 45 passed
$ .venv/bin/python -m ruff check .       -> All checks passed
$ ./scripts/test-firmware.sh             -> 6 frame checks passed
```

No deployment, no `daemon-reload`, and no restart was performed on the Pi.

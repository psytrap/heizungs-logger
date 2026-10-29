# Ticket 003: Re-evaluate the systemd Unit File

- **Status:** Backlog
- **Priority:** Normal
- **Scope & Relevant Files:**
  - `heizungs_logger.service`
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

---

## Criteria

- [ ] Deployed unit inspected read-only and compared with the repository copy; drift recorded.
- [ ] Each finding 1–11 marked as *keep*, *change*, or *out of scope*, with a one-line rationale.
- [ ] A concrete proposed unit file is included in `## Execution Notes` (or in an operations note under `docs/`).
- [ ] Every proposed directive is justified by an observed behaviour of the application, not by generic hardening advice.
- [ ] Any item that needs code or runtime support (watchdog, USB ordering, venv) is named as follow-up work and **not** silently implemented.
- [ ] No change is deployed to the Pi in this ticket.
- [ ] `python -m pytest` passes.
- [ ] Zero Ruff errors or warnings (`python -m ruff check .`).

---

## Execution Notes
<!-- Populated during Step 5 of the Ticket Protocol -->

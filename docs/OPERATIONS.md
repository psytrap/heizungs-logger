# 🛠️ Operations: the systemd Unit

How the logger is supervised on the Pi, what the unit guarantees, and how to install, inspect and remove it.

- Unit file: [`heizungs_logger.service`](../heizungs_logger.service) (repository root, single source of truth)
- Installer: [`scripts/install-service.sh`](../scripts/install-service.sh)

---

## 1. 📦 Installing

```sh
sudo scripts/install-service.sh            # install, daemon-reload, enable
sudo scripts/install-service.sh --restart  # ... and restart the running instance
sudo scripts/install-service.sh --dry-run  # print actions, change nothing
sudo scripts/install-service.sh --uninstall
```

The script warns — without failing — when `ExecStart` points at a missing script, a missing log directory, or an absent serial device, and when the deployed entry point does not look like the repository's `sys.path` shim. Log files and the log directory are never touched on uninstall.

## 2. 🔁 Restart semantics

| Directive | Value | Why |
| :--- | :--- | :--- |
| `Restart` | `always` | A clean exit or a schedule slip must not end collection; `on-failure` would leave the logger dead after a graceful stop of the loop. |
| `RestartSec` | `10` | Long enough that a missing `/dev/ttyUSB0` does not hammer the port or the journal. |
| `StartLimitIntervalSec` | `0` | Unbounded retries. The device is usually re-plugged within minutes; giving up permanently after five attempts would silently stop logging until someone notices. |
| `TimeoutStartSec` | *(removed)* | Has no effect for `Type=simple`; it was carried over from the v1 unit. |

Consequence: while the adapter is absent the service is in an endless 10 s restart loop. That is intentional and visible in the journal.

A deliberate self-restart (5 minutes without a record, see §6) exits with status 1. `Restart=always` restarts it anyway; the status only makes the cause visible in `systemctl status`.

## 3. 🔍 Inspecting

```sh
systemctl status heizungs_logger.service
systemctl cat heizungs_logger.service
systemctl show heizungs_logger.service -p Restart -p RestartUSec -p WatchdogUSec
journalctl -u heizungs_logger.service -n 50 --no-pager
journalctl -u heizungs_logger.service --since "1 hour ago" | grep -i "traceback\|error"
```

`SyslogIdentifier` stays `heizungs_logger.py` so historical `journalctl -t heizungs_logger.py` queries keep working. `PYTHONUNBUFFERED=1` is set so journal lines appear as the logger writes them instead of at process exit or buffer flush.

## 4. 🛡️ Hardening and its limits

`NoNewPrivileges=yes`, `PrivateTmp=yes` and `ProtectSystem=full` are enabled — the logger writes only to its log directory under `/home/ubuntu`, so read-only `/usr`, `/boot` and `/etc` are safe.

`ProtectHome` is deliberately **not** restricted: the log directory lives in `/home/ubuntu/heizungs_logger_logs`, so `ProtectHome=read-only` or `yes` would break collection. A future move of the log directory outside `/home` would allow tightening this.

## 5. ⚠️ Not covered

- **No watchdog.** `WatchdogUSec=0`: the unit supervises process exit only. A wedged process that still holds the serial port is not detected. Enabling this needs `sd_notify` support in the application, so it is out of scope for the unit file alone.
- **No device ordering.** The unit does not wait for `dev-ttyUSB0.device`; the restart loop covers enumeration delays instead. Re-enumeration to a different device name is an application-level concern.
- **Log retention.** `StandardOutput=journal` uses journald defaults; the JSONL files under the log directory are not rotated by the unit.

---

## 6. 🚦 Failure behaviour

The loop distinguishes four kinds of fault, deliberately:

| Fault | Behaviour | Cost |
| :--- | :--- | :--- |
| **Display** (no LCD at 0x21, I2C error) | The record is written *before* the display update, so nothing is lost. One journal line `display unavailable: ...; continuing without it`, repeats are counted silently, the handle is dropped and reconnected on the next cycle, and recovery is logged as `display recovered after N failed update(s)`. | None. The LCD stays dark or stale until the fault clears. |
| **Frame** (empty read, undecodable bytes) | Rejected: no record, one `rejected frame (empty|undecodable): ...` line, and the 20 s cadence is preserved. This follows the reader contract in [`RECORDING.md`](RECORDING.md) §4. | One missing sample. |
| **Transport** (port open/write/read error) | Propagates out of the loop, the process exits and systemd restarts it after `RestartSec`. That restart is the *only* reconnect mechanism, so it is intentional. | One or two samples, plus a 3 s startup delay. |
| **Silence** (5 min without a frame that produced a record) | One line `no meaningful frame for Ns; requesting a restart`, then `Runner.sample` raises `FrameTimeout`. `cli.main` prints `... exiting for a clean restart`, closes the port and returns **status 1** instead of a traceback. `Restart=always` restarts the unit 10 s later with a fresh serial handle. | Up to 5 min of lost samples, once per streak. |

Additional notes:

- **Late cycle:** if a cycle overruns its 20 s budget the remaining wait is clamped to zero instead of raising `ValueError`.
- **Silence is a streak, not a sample:** the timer runs from the last written record and is only consulted after a rejected frame, so an occasional bad frame never restarts anything. The limit is `runner.SILENCE_LIMIT` (300 s) and is injectable as `Runner(silence_limit=...)`. A restart is deliberate: a persistent frame fault is usually a port that only recovers when it is reopened.
- **Missing sensor:** the firmware emits `-127.0` (`DEVICE_DISCONNECTED_C`) or `85.0` (power-on value); those are recorded verbatim. Nothing raises an alarm, so check the values, not the service state.
- **Repeated transport failures** show up as a restart loop (`systemctl show -p NRestarts`) in the journal. The unit hardcodes `/dev/ttyUSB0`, so a device that re-enumerates as `ttyUSB1` is not followed.

```sh
journalctl -u heizungs_logger.service --since "1 hour ago" | grep -E "display|rejected frame|no meaningful frame"
systemctl show heizungs_logger.service -p NRestarts
```

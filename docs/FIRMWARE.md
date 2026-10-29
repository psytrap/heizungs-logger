# 🧩 Firmware: Protocol, Build and Testing

The sketch produces the serial frames the Python logger parses. This note records what it emits, how that is tested without hardware, and what is still unknown.

- Sketch: [`heizungs_logger.ino`](../heizungs_logger.ino)
- Formatter: [`firmware/frame.h`](../firmware/frame.h), [`firmware/frame.cpp`](../firmware/frame.cpp)
- Host test: [`tests/firmware/frame_test.cpp`](../tests/firmware/frame_test.cpp)
- Shared fixtures: [`tests/fixtures/firmware_frames.tsv`](../tests/fixtures/firmware_frames.tsv)
- Parser contract test: [`tests/test_firmware_contract.py`](../tests/test_firmware_contract.py)

---

## 1. 📡 Wire format

One line per request, LF-terminated, single-space separated, no labels beyond the two section words:

```
Temp <t0> <t1> ... Input <on|off> ...
```

The sketch writes whatever the sensors return, including the DallasTemperature sentinels `-127.0` (`DEVICE_DISCONNECTED_C`) and `85.0` (power-on reset value). The Python side appends the timestamp, so the record width on disk is:

| Shape | Temperatures | On-wire fields | Record fields | Generation |
| :--- | :---: | :---: | :---: | :--- |
| 4 sensors | 4 | 8 | 9 | v1a |
| 6 sensors | 6 | 10 | 11 | v1b |

## 2. 🐞 The repository sketch does not match the live device

This is the most important finding of T-004 and it is unresolved:

- The checked-in sketch declares `ONE_WIRE_PINS = 4` and printed floats with `String(temp)`, which on AVR yields **two** decimals.
- The live board emits **six** temperatures with **one** decimal. Newest frame observed on 2026-10-29:

  ```
  ['Temp', '29.7', '28.4', '33.0', '29.3', '29.3', '15.3', 'Input', 'off', 'off', '2026-10-29T13:50:17.729536+01:00']
  ```

So the deployed firmware is a later revision than the sketch in this repository, and the sketch alone would reproduce the older v1a shape. The formatter therefore takes the sensor count and the decimal count as parameters instead of hardcoding either. **The sketch's own sensor count and precision are unverified against hardware** and must be settled when the board is next flashed.

## 3. ✅ Decision record (T-004)

| Direction | Verdict | Reason |
| :--- | :--- | :--- |
| Extract a pure `formatFrame()` | **Adopted** | Frame building is the only part with a contract; it is now testable on any host. |
| Host-side test with the system C++ compiler | **Adopted** | `g++` exists on the dev machine, needs no Arduino core, and runs in milliseconds. |
| Shared fixture used by C++ and Python | **Adopted** | Catches drift on either side of the wire instead of testing each end in isolation. |
| Fake `OneWire`/`DallasTemperature` shims | **Rejected for now** | The sampling loop is a straight loop over pins; extracting the formatter already covers the part that can break the consumer. Revisit if the loop grows logic. |
| `arduino-cli compile` as a gate | **Not adopted yet** | No Arduino toolchain is installed and the board FQBN is unknown (§4). The command and the manual step are documented instead. |
| Hardware-in-the-loop in CI | **Rejected** | The board is attached to the live Pi; collection must not be disturbed. |

## 4. ❓ Build provenance (unknown)

Nothing in the repository pins the board type, core version, or library versions. The sketch was previously built outside the repo (no `platformio.ini`, no `sketch.yaml`).

To capture it when the board is next connected:

```sh
arduino-cli board list                 # port -> FQBN
arduino-cli board details -b <FQBN>    # core version
arduino-cli lib list                   # OneWire, DallasTemperature versions
```

Observed constraint: the device appears as `/dev/ttyUSB0` at 9600 baud, i.e. a USB-serial bridge rather than native USB, despite the `while (!Serial)` guard in `setup()`.

## 5. 🧪 Running the tests

```sh
./scripts/test-firmware.sh                  # compile + run the C++ frame test
python -m pytest tests/test_firmware_contract.py -q
python -m pytest -q                         # full suite
```

`./scripts/test-firmware.sh` prints `skipped` and exits 0 on machines without a C++ compiler (the Pi has none).

**Rounding caveat:** `dtostrf` (AVR) rounds half away from zero, `snprintf` (host) rounds half to even. Frames that land exactly on a half at the chosen precision would compare unequal in the host test, so the fixtures avoid such values. This is a test-fixture rule, not a protocol difference: real sensor readings are not exact halves.

## 6. 🔌 Manual hardware procedure

Requires explicit maintainer authorisation; it flashes the board that is currently serving production.

1. Capture the current sketch from the board or confirm which revision is deployed (§2).
2. Compile against the recorded FQBN and library versions (§4).
3. Flash, then `sudo systemctl restart heizungs_logger.service`.
4. Send `x` once and capture five consecutive frames:

   ```sh
   sudo systemctl stop heizungs_logger.service
   python3 - <<'PY'
   import serial
   link = serial.Serial("/dev/ttyUSB0", 9600, timeout=10)
   for _ in range(5):
       link.write(b"x"); link.flush()
       print(link.readline())
   PY
   sudo systemctl start heizungs_logger.service
   ```

5. Assert: six temperature tokens, two input tokens, one decimal place, sentinels unchanged for a disconnected sensor.
6. Record the observed frame in this document and add it to the fixtures.

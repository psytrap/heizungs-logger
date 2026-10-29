# Ticket 005: Restore the Legacy LCD Layout for Six-Temperature Frames

- **Status:** Done
- **Priority:** High
- **Scope & Relevant Files:**
  - `src/heizungslogger/display.py`
  - `tests/test_display.py`

---

## Description & Context

Found while preparing the first v2 deployment to the Pi. The refactor in T-001 assumed the v1a frame shape (four temperatures followed by two input states) and hardcoded:

```python
COLUMNS = (0, 6, 12)
ROW0_INDICES = (1, 2, 6)
ROW1_INDICES = (3, 4, 7)
```

The script actually deployed on the Pi — read from `/home/ubuntu/heizungs_logger/heizungs_logger.py` — renders six temperatures at columns `0, 5, 10`:

```python
lcd.cursor_position(0,0);  lcd.message = data[1]
lcd.cursor_position(5,0);  lcd.message = data[2]
lcd.cursor_position(10,0); lcd.message = data[3]
lcd.cursor_position(0,1);  lcd.message = data[4]
lcd.cursor_position(5,1);  lcd.message = data[5]
lcd.cursor_position(10,1); lcd.message = data[6]
```

Live frames carry six temperatures (`['Temp', '29.7', '28.4', '33.0', '29.3', '29.3', '15.3', 'Input', ...]`), so the v2 layout would print temperature 6 at row 0 column 12 and the literal string `Input` at row 1 column 12 — a visible regression on the device.

The tests in `tests/test_display.py` encode the wrong layout and must be corrected with the code, not kept as a description of it.

---

## Criteria

- [x] `DEFAULT_LAYOUT` reproduces the deployed script: columns `(0, 5, 10)`, row 0 indices `(1, 2, 3)`, row 1 indices `(4, 5, 6)`.
- [x] Tests assert the legacy cell order against a six-temperature frame and fail if the layout drifts.
- [x] A test pins the six-temperature frame shape so a future four-temperature assumption cannot silently return.
- [x] `python -m pytest` passes.
- [x] Zero Ruff errors or warnings (`python -m ruff check .`).

---

## Execution Notes

### Change

`src/heizungslogger/display.py`:

```python
COLUMNS = (0, 5, 10)
ROW0_INDICES = (1, 2, 3)
ROW1_INDICES = (4, 5, 6)
```

with a comment naming the deployed script as the source of truth. Nothing else changed: `render()` stays pure, `LcdDisplay` still connects lazily, and the backlight colour is untouched.

### Tests

`tests/test_display.py` was rewritten around a **live v1b frame** (`Temp 29.7 28.4 33.0 29.3 29.3 15.3 Input off off`) instead of a synthetic nine-field list:

- default layout equality and legacy cell order (`0,5,10` on both rows, temperatures 1–3 / 4–6),
- `test_layout_addresses_temperature_cells_only` — every rendered index must be `< FIELDS.index("Input")`, so indices that reach the marker (the old `7`) fail,
- `test_layout_would_misfire_on_a_four_temperature_frame` — documents the concrete damage of a v1a assumption: row 1 shows `24.5`, `Input`, `on`,
- an explicit custom-layout test that no longer duplicates the default.

One attempted assertion was dropped: a four-temperature frame does **not** raise `IndexError`, because the list still has eight elements — it renders the marker instead. That is exactly the silent failure the new index test catches.

### Gates

```text
$ .venv/bin/python -m pytest -q          -> 47 passed
$ .venv/bin/python -m ruff check .       -> All checks passed
$ ./scripts/test-firmware.sh             -> 6 frame checks passed
```

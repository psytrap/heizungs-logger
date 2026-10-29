import pytest

from heizungslogger.display import LcdDisplay, render

# A live v1b frame: six temperatures, two inputs.
FIELDS = ["Temp", "29.7", "28.4", "33.0", "29.3", "29.3", "15.3", "Input", "off", "off"]


def test_render_uses_legacy_indices():
    row0, row1 = render(FIELDS)
    assert row0 == ("29.7", "28.4", "33.0")
    assert row1 == ("29.3", "29.3", "15.3")


def test_render_default_columns_are_zero_five_ten():
    # The deployed script places cells at 0, 5 and 10 on both rows.
    assert LcdDisplay().layout == ((0, 5, 10), (1, 2, 3), (4, 5, 6))


def test_render_accepts_a_custom_layout():
    layout = ((0, 8), (1, 2), (5, 6))
    row0, row1 = render(FIELDS, layout)
    assert row0 == ("29.7", "28.4")
    assert row1 == ("29.3", "15.3")


def test_layout_addresses_temperature_cells_only():
    # Pins the six-temperature shape: every rendered index must be a temperature,
    # never the `Input` marker. A four-temperature frame would place `Input` on
    # the display and fail here.
    _columns, row0, row1 = LcdDisplay().layout
    input_index = FIELDS.index("Input")
    for index in (*row0, *row1):
        assert 0 < index < input_index, index
        assert FIELDS[index] not in {"Input", "off"}


def test_layout_would_misfire_on_a_four_temperature_frame():
    # Documents why the live firmware's six temperatures are a hard requirement:
    # with four, the row 1 cells land on the `Input` marker and a state.
    v1a = ["Temp", "21.5", "22.3", "23.0", "24.5", "Input", "on", "off"]
    row0, row1 = render(v1a)
    assert row0 == ("21.5", "22.3", "23.0")
    assert row1 == ("24.5", "Input", "on")


def test_render_raises_on_short_frame():
    with pytest.raises(IndexError):
        render(["t", "a", "b"])


class FakeLcd:
    def __init__(self):
        self.calls = []
        self._message = None
        self.color = None

    def clear(self):
        self.calls.append(("clear",))

    def cursor_position(self, column, row):
        self.calls.append(("cursor", column, row))

    @property
    def message(self):
        return self._message

    @message.setter
    def message(self, value):
        self._message = value
        self.calls.append(("message", value))


def test_show_writes_each_cell_in_legacy_order():
    lcd = FakeLcd()
    display = LcdDisplay()
    display._lcd = lcd
    display.show(FIELDS)

    assert [call for call in lcd.calls if call[0] == "cursor"] == [
        ("cursor", 0, 0),
        ("cursor", 5, 0),
        ("cursor", 10, 0),
        ("cursor", 0, 1),
        ("cursor", 5, 1),
        ("cursor", 10, 1),
    ]
    assert [call[1] for call in lcd.calls if call[0] == "message"] == [
        "29.7",
        "28.4",
        "33.0",
        "29.3",
        "29.3",
        "15.3",
    ]
    assert lcd.calls[0] == ("clear",)


def test_show_connects_lazily_only_when_needed():
    display = LcdDisplay()
    assert display._lcd is None

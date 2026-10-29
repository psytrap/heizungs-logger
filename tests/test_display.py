import pytest

from heizungslogger.display import LcdDisplay, render

FIELDS = ["t", "21.5", "35.0", "40.1", "22.0", "18.4", "61.0", "55.0", "12"]


def test_render_uses_legacy_indices():
    row0, row1 = render(FIELDS)
    assert row0 == ("21.5", "35.0", "61.0")
    assert row1 == ("40.1", "22.0", "55.0")


def test_render_default_columns_are_zero_six_twelve():
    assert LcdDisplay().layout[0] == (0, 6, 12)


def test_render_accepts_a_custom_layout():
    layout = ((0, 5, 10), (1, 2, 3), (4, 5, 6))
    row0, row1 = render(FIELDS, layout)
    assert row0 == ("21.5", "35.0", "40.1")
    assert row1 == ("22.0", "18.4", "61.0")


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
        ("cursor", 6, 0),
        ("cursor", 12, 0),
        ("cursor", 0, 1),
        ("cursor", 6, 1),
        ("cursor", 12, 1),
    ]
    assert [call[1] for call in lcd.calls if call[0] == "message"] == [
        "21.5",
        "35.0",
        "61.0",
        "40.1",
        "22.0",
        "55.0",
    ]
    assert lcd.calls[0] == ("clear",)


def test_show_connects_lazily_only_when_needed():
    display = LcdDisplay()
    assert display._lcd is None

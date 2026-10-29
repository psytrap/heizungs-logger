"""LCD rendering: a pure layout function plus a lazily connected display.

``render`` holds the whole layout and is hardware-free. Only ``LcdDisplay``
touches ``board`` / ``adafruit_character_lcd``, and it imports them inside
``connect`` so that importing this module never requires a Pi.
"""

LCD_COLUMNS = 16
LCD_ROWS = 2

#: Column positions shared by both rows.
COLUMNS = (0, 5, 10)
#: Field indices shown in row 0 / row 1, paired with ``COLUMNS``. The deployed
#: script shows the six temperatures of a v1b frame: ``data[1:4]`` on row 0 and
#: ``data[4:7]`` on row 1.
ROW0_INDICES = (1, 2, 3)
ROW1_INDICES = (4, 5, 6)
#: Backlight colour, applied once at startup by the legacy script.
COLOR = (100, 0, 0)

Layout = tuple[tuple[int, ...], tuple[int, ...], tuple[int, ...]]

DEFAULT_LAYOUT: Layout = (COLUMNS, ROW0_INDICES, ROW1_INDICES)


def render(fields: list[str], layout: Layout = DEFAULT_LAYOUT) -> tuple[tuple[str, ...], ...]:
    """Map frame ``fields`` onto two LCD rows.

    Returns ``(row0, row1)`` with one entry per column. A frame that is too
    short raises ``IndexError``, as the legacy script did.
    """
    _columns, row0, row1 = layout
    return tuple(fields[i] for i in row0), tuple(fields[i] for i in row1)


class LcdDisplay:
    """Character LCD over I2C. Connects on first use, not on import."""

    def __init__(
        self,
        layout: Layout = DEFAULT_LAYOUT,
        columns: int = LCD_COLUMNS,
        rows: int = LCD_ROWS,
        color: tuple[int, int, int] = COLOR,
    ) -> None:
        self.layout = layout
        self.columns = columns
        self.rows = rows
        self.color = color
        self._lcd = None

    def connect(self) -> None:
        """Create the I2C LCD and apply the startup state."""
        import adafruit_character_lcd.character_lcd_rgb_i2c as character_lcd
        import board  # hardware imports stay lazy: no Pi needed to import this module

        i2c = board.I2C()
        self._lcd = character_lcd.Character_LCD_RGB_I2C(i2c, self.columns, self.rows)
        self._lcd.clear()
        self._lcd.color = list(self.color)

    def close(self) -> None:
        """Forget the handle so the next ``show`` reconnects.

        The runner calls this after a failed update; the I2C object cannot be
        relied on once a write raised.
        """
        self._lcd = None

    def show(self, fields: list[str]) -> None:
        """Write ``fields`` to the display, one cell at a time."""
        if self._lcd is None:
            self.connect()
        row0, row1 = render(fields, self.layout)
        self._lcd.clear()
        for row, values in enumerate((row0, row1)):
            for column, text in zip(self.layout[0], values, strict=False):
                self._lcd.cursor_position(column, row)
                self._lcd.message = text

"""Plain-file record store: one ``LOG-<local-date>.json`` file per day.

Each line is a Python list literal produced by ``str(list)``, exactly as the
legacy script wrote it. Records stay append-only and human-greppable.
"""

import datetime
import os

import dateutil.tz


def local_label(moment: datetime.datetime) -> datetime.datetime:
    """Attach the local timezone to a naive UTC timestamp.

    This reproduces the legacy ``next.astimezone(tzlocal())`` call. Note that
    the legacy loop passed a *naive* ``utcnow()`` value, so this only labels
    the timestamp, it does not convert it. Preserved verbatim on purpose; the
    conversion defect is tracked in ``docs/RECORDING.md``.
    """
    return moment.astimezone(dateutil.tz.tzlocal())


def record_path(log_directory: str, moment: datetime.datetime) -> str:
    """Return the day-file path for ``moment`` (``LOG-<iso-date>.json``)."""
    day = local_label(moment).date().isoformat()
    return os.path.join(log_directory, f"LOG-{day}.json")


class FileStore:
    """Append-only writer for the day files."""

    def __init__(self, log_directory: str) -> None:
        self.log_directory = log_directory

    def append(self, fields: list[str], moment: datetime.datetime) -> str:
        """Append one record and return the line that was written."""
        line = format_line(fields, moment)
        with open(record_path(self.log_directory, moment), "a") as file:
            print(line, file=file)
        return line


def format_line(fields: list[str], moment: datetime.datetime) -> str:
    """Render one record exactly like the legacy ``str(data)`` call."""
    data = [*fields, local_label(moment).isoformat()]
    return str(data)

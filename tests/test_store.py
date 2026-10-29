import ast
import datetime
import time

import pytest

from heizungslogger.store import FileStore, format_line, local_label, record_path

FIELDS = ["0", "21.5", "35.0", "40.1", "22.0", "18.4", "61", "55", "12", "0", "a"]
MOMENT = datetime.datetime(2026, 10, 29, 12, 0, 0)


@pytest.fixture
def berlin_timezone(monkeypatch):
    monkeypatch.setenv("TZ", "Europe/Berlin")
    time.tzset()
    yield
    monkeypatch.delenv("TZ", raising=False)
    time.tzset()


def test_line_is_a_list_literal_with_appended_timestamp(berlin_timezone):
    line = format_line(FIELDS, MOMENT)
    assert line == (
        "['0', '21.5', '35.0', '40.1', '22.0', '18.4', '61', '55', '12', '0', 'a', "
        "'2026-10-29T12:00:00+01:00']"
    )


def test_line_survives_literal_eval(berlin_timezone):
    values = ast.literal_eval(format_line(FIELDS, MOMENT))
    assert values[:-1] == FIELDS
    assert datetime.datetime.fromisoformat(values[-1]).tzinfo is not None


def test_naive_timestamp_is_labelled_not_converted(berlin_timezone):
    # Legacy defect preserved on purpose: the naive UTC value is only stamped
    # with the local offset, it is not shifted.
    assert local_label(MOMENT).isoformat() == "2026-10-29T12:00:00+01:00"


def test_record_path_is_a_daily_json_file(berlin_timezone):
    assert record_path("/logs", MOMENT) == "/logs/LOG-2026-10-29.json"


def test_append_writes_one_line_to_the_day_file(tmp_path, berlin_timezone):
    store = FileStore(str(tmp_path))
    store.append(FIELDS, MOMENT)

    written = (tmp_path / "LOG-2026-10-29.json").read_text(encoding="utf-8")
    assert written == format_line(FIELDS, MOMENT) + "\n"


def test_append_is_additive(tmp_path, berlin_timezone):
    store = FileStore(str(tmp_path))
    store.append(FIELDS, MOMENT)
    store.append(FIELDS, MOMENT)

    lines = (tmp_path / "LOG-2026-10-29.json").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2

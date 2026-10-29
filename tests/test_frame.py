import pytest

from heizungslogger.frame import parse_frame

VALID = b"0 21.5 35.0 40.1 22.0 18.4 61 55 12 0 a\r\n"


def test_valid_frame_splits_on_single_spaces():
    fields = parse_frame(VALID)
    assert fields == ["0", "21.5", "35.0", "40.1", "22.0", "18.4", "61", "55", "12", "0", "a"]


def test_short_frame_is_returned_as_is():
    assert parse_frame(b"0 21.5 35.0\n") == ["0", "21.5", "35.0"]


def test_empty_line_yields_single_empty_field():
    assert parse_frame(b"\r\n") == [""]
    assert parse_frame(b"") == [""]


def test_non_utf8_bytes_raise():
    with pytest.raises(UnicodeDecodeError):
        parse_frame(b"0 \xff\xfe 21.5\r\n")


def test_surrounding_whitespace_is_stripped():
    assert parse_frame(b"  0 21.5 35.0  \r\n") == ["0", "21.5", "35.0"]


def test_inner_repeated_space_becomes_empty_field():
    assert parse_frame(b"0  21.5\r\n") == ["0", "", "21.5"]

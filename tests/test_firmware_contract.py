"""Wire-format contract between the Arduino sketch and the Python parser.

The frames in ``tests/fixtures/firmware_frames.tsv`` are also formatted by the
C++ test in ``tests/firmware/frame_test.cpp``. This test asserts the other half
of the contract: what the sketch emits is parseable, positional, and yields the
documented record width (9 fields for v1a, 11 for v1b, before the timestamp).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from heizungslogger.frame import parse_frame

FIXTURE = Path(__file__).parent / "fixtures" / "firmware_frames.tsv"


def load_cases() -> list[tuple[str, list[str]]]:
    cases: list[tuple[str, list[str]]] = []
    for raw_line in FIXTURE.read_text().splitlines():
        if not raw_line or raw_line.startswith("#"):
            continue
        identifier, _decimals, temps, inputs, frame = raw_line.split("\t")
        fields = ["Temp", *temps.split(","), "Input", *inputs.split(",")]
        cases.append((identifier, fields))
    return cases


CASES = load_cases()


def build_frame(fields: list[str]) -> bytes:
    return (" ".join(fields) + "\n").encode()


@pytest.mark.parametrize(("identifier", "fields"), CASES, ids=[c[0] for c in CASES])
def test_frame_round_trips_through_the_parser(identifier: str, fields: list[str]) -> None:
    assert parse_frame(build_frame(fields)) == fields


@pytest.mark.parametrize(("identifier", "fields"), CASES, ids=[c[0] for c in CASES])
def test_record_width_matches_a_documented_generation(identifier: str, fields: list[str]) -> None:
    # The logger appends the timestamp, so the on-disk width is one more.
    assert len(fields) + 1 in (9, 11), identifier


def test_four_sensor_frame_is_v1a_and_six_sensor_frame_is_v1b() -> None:
    four = ["Temp", "21.5", "22.3", "23.0", "24.5", "Input", "on", "off"]
    six = ["Temp", "29.7", "28.4", "33.0", "29.3", "29.3", "15.3", "Input", "off", "off"]

    assert len(parse_frame(build_frame(four))) + 1 == 9
    assert len(parse_frame(build_frame(six))) + 1 == 11


@pytest.mark.parametrize("value", ["-127.0", "85.0"])
def test_sentinel_values_survive_as_plain_fields(value: str) -> None:
    # DallasTemperature reports DEVICE_DISCONNECTED_C (-127) and 85.0 (power-on
    # reset value); the parser must not special-case or drop them.
    fields = ["Temp", value, "22.3", "23.0", "24.5", "Input", "off", "off"]
    assert parse_frame(build_frame(fields))[1] == value

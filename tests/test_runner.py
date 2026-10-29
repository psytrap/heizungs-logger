import datetime

import pytest

from heizungslogger.runner import Runner

MOMENT = datetime.datetime(2026, 10, 29, 12, 0, 0)
LINE = b"0 21.5 35.0 40.1 22.0 18.4 61 55 12 0 a\r\n"


class FakeClock:
    def __init__(self, moment=MOMENT, interrupt_after=None):
        self.moment = moment
        self.sleeps = []
        self.interrupt_after = interrupt_after

    def now(self):
        return self.moment

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        if self.interrupt_after is not None and len(self.sleeps) >= self.interrupt_after:
            raise KeyboardInterrupt


class FakeLink:
    def __init__(self, line=LINE):
        self.events = []
        self.line = line
        self.closed = False

    def reset_input_buffer(self):
        self.events.append("reset")

    def write(self, data):
        self.events.append(("write", data))

    def flush(self):
        self.events.append("flush")

    def readline(self):
        self.events.append("readline")
        return self.line

    def close(self):
        self.closed = True


class FakeDisplay:
    def __init__(self):
        self.shown = []

    def show(self, fields):
        self.shown.append(fields)


class FakeStore:
    def __init__(self):
        self.appended = []

    def append(self, fields, moment):
        self.appended.append((fields, moment))
        return "line"


def build_runner(**kwargs):
    clock = kwargs.pop("clock", FakeClock())
    link = FakeLink()
    display = FakeDisplay()
    store = FakeStore()
    emitted = []
    runner = Runner(link, display, store, clock, emit=emitted.append, **kwargs)
    return runner, clock, link, display, store, emitted


def test_sample_follows_the_legacy_protocol():
    runner, clock, link, display, store, emitted = build_runner()

    fields = runner.sample(MOMENT + datetime.timedelta(seconds=20))

    assert link.events == ["reset", ("write", b"x"), "flush", "readline"]
    assert clock.sleeps == [0.1, 5.0, 20.0]
    assert display.shown == [fields]
    assert store.appended == [(fields, MOMENT + datetime.timedelta(seconds=20))]


def test_sample_emits_fields_then_delta_then_timestamp():
    runner, _clock, _link, _display, _store, emitted = build_runner()

    runner.sample(MOMENT + datetime.timedelta(seconds=20))

    assert isinstance(emitted[0], list), "legacy print(data) emits the field list"
    assert emitted[1] == 20.0
    assert isinstance(emitted[2], str)
    assert emitted[2].startswith("2026-10-29T12:00:20")


def test_run_waits_for_startup_before_the_first_cycle():
    clock = FakeClock(interrupt_after=2)
    runner, _clock, _link, _display, _store, _emitted = build_runner(clock=clock)

    with pytest.raises(SystemExit) as excinfo:
        runner.run()

    assert excinfo.value.code == 0
    assert clock.sleeps == [3.0, 0.1]


def test_keyboard_interrupt_stops_the_loop_with_status_zero():
    clock = FakeClock(interrupt_after=3)
    runner, _clock, _link, _display, _store, _emitted = build_runner(clock=clock)

    with pytest.raises(SystemExit) as excinfo:
        runner.run()

    assert excinfo.value.code == 0
    assert clock.sleeps == [3.0, 0.1, 5.0]

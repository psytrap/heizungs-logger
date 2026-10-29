import datetime

import pytest

from heizungslogger.runner import FrameTimeout, Runner

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


class ManualClock(FakeClock):
    """A clock that follows its own sleeps, so a cycle takes its real 20 s."""

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.moment += datetime.timedelta(seconds=seconds)


class FakeLink:
    def __init__(self, line=LINE, read_error=None):
        self.events = []
        self.line = line
        self.read_error = read_error
        self.closed = False

    def reset_input_buffer(self):
        self.events.append("reset")

    def write(self, data):
        self.events.append(("write", data))

    def flush(self):
        self.events.append("flush")

    def readline(self):
        self.events.append("readline")
        if self.read_error is not None:
            raise self.read_error
        return self.line

    def close(self):
        self.closed = True


class FakeDisplay:
    def __init__(self):
        self.shown = []
        self.closes = 0

    def show(self, fields):
        self.shown.append(fields)

    def close(self):
        self.closes += 1


class FlakyDisplay(FakeDisplay):
    """Fails ``failures`` times, then behaves."""

    def __init__(self, failures=0, error=None):
        super().__init__()
        self.failures = failures
        self.error = error or OSError(121, "Remote I/O error")

    def show(self, fields):
        if self.failures > 0:
            self.failures -= 1
            raise self.error
        super().show(fields)


class FakeStore:
    def __init__(self):
        self.appended = []

    def append(self, fields, moment):
        self.appended.append((fields, moment))
        return "line"


def build_runner(**kwargs):
    clock = kwargs.pop("clock", FakeClock())
    link = kwargs.pop("link", FakeLink())
    display = kwargs.pop("display", FakeDisplay())
    store = kwargs.pop("store", FakeStore())
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


def test_display_failure_does_not_stop_the_cycle_and_keeps_the_record():
    display = FlakyDisplay(failures=1)
    runner, _clock, _link, _display, store, emitted = build_runner(display=display)

    fields = runner.sample(MOMENT + datetime.timedelta(seconds=20))

    assert fields
    assert store.appended == [(fields, MOMENT + datetime.timedelta(seconds=20))]
    assert display.shown == []
    assert runner.display_errors == 1
    assert display.closes == 1, "the handle is dropped so the next cycle reconnects"
    assert any("display unavailable" in str(item) for item in emitted)


def test_repeated_display_failures_are_counted_not_spammed():
    display = FlakyDisplay(failures=10)
    runner, _clock, _link, _display, store, emitted = build_runner(display=display)

    for _ in range(3):
        runner.sample(MOMENT + datetime.timedelta(seconds=20))

    messages = [item for item in emitted if "display unavailable" in str(item)]
    assert len(messages) == 1
    assert runner.display_errors == 3
    assert len(store.appended) == 3
    assert display.closes == 3


def test_display_recovery_is_announced_and_the_counter_resets():
    display = FlakyDisplay(failures=1)
    runner, _clock, _link, _display, _store, emitted = build_runner(display=display)

    runner.sample(MOMENT + datetime.timedelta(seconds=20))
    runner.sample(MOMENT + datetime.timedelta(seconds=20))

    assert any("display recovered after 1 failed update" in str(item) for item in emitted)
    assert runner.display_errors == 0
    assert len(display.shown) == 1


def test_the_record_is_written_before_the_display_is_updated():
    order = []

    class OrderDisplay(FakeDisplay):
        def show(self, fields):
            order.append("display")
            super().show(fields)

    class OrderStore(FakeStore):
        def append(self, fields, moment):
            order.append("store")
            return super().append(fields, moment)

    runner, _clock, _link, _display, _store, _emitted = build_runner(
        display=OrderDisplay(), store=OrderStore()
    )
    runner.sample(MOMENT + datetime.timedelta(seconds=20))

    assert order == ["store", "display"]


def test_a_display_fault_does_not_end_the_loop():
    # Sleeps per cycle: settle, conversion, wait. Interrupt during cycle 3.
    clock = FakeClock(interrupt_after=8)
    display = FlakyDisplay(failures=10)
    runner, _clock, _link, _display, store, _emitted = build_runner(
        clock=clock, display=display
    )

    with pytest.raises(SystemExit) as excinfo:
        runner.run()

    assert excinfo.value.code == 0
    assert len(store.appended) == 2, "two full cycles recorded despite the fault"
    assert runner.display_errors == 2


def test_empty_frame_is_rejected_without_a_record():
    runner, clock, _link, display, store, emitted = build_runner(link=FakeLink(line=b""))

    fields = runner.sample(MOMENT + datetime.timedelta(seconds=20))

    assert fields == []
    assert store.appended == []
    assert display.shown == []
    assert runner.rejected_frames == 1
    assert clock.sleeps == [0.1, 5.0, 20.0], "cadence is preserved"
    assert any("rejected frame (empty)" in str(item) for item in emitted)


def test_undecodable_frame_is_rejected_without_a_record():
    runner, _clock, _link, _display, store, emitted = build_runner(
        link=FakeLink(line=b"\xff\xfe\n")
    )

    assert runner.sample(MOMENT + datetime.timedelta(seconds=20)) == []
    assert store.appended == []
    assert runner.rejected_frames == 1
    assert any("rejected frame (undecodable)" in str(item) for item in emitted)


def test_transport_errors_still_propagate():
    runner, _clock, _link, _display, store, _emitted = build_runner(
        link=FakeLink(read_error=OSError("port closed"))
    )

    with pytest.raises(OSError):
        runner.sample(MOMENT + datetime.timedelta(seconds=20))

    assert store.appended == []


def test_a_late_cycle_sleeps_zero_instead_of_raising():
    runner, clock, _link, _display, _store, _emitted = build_runner()

    runner.sample(MOMENT - datetime.timedelta(seconds=5))

    assert clock.sleeps == [0.1, 5.0, 0.0]


def bad_cycles(runner, clock, count):
    for _ in range(count):
        runner.sample(clock.now() + datetime.timedelta(seconds=20))


def test_fifteen_rejected_cycles_request_a_restart():
    clock = ManualClock()
    runner, _clock, _link, _display, _store, _emitted = build_runner(
        clock=clock, link=FakeLink(line=b"")
    )

    with pytest.raises(FrameTimeout) as excinfo:
        bad_cycles(runner, clock, 20)

    assert excinfo.value.seconds == pytest.approx(300.0)
    assert len(clock.sleeps) == 45, "15 cycles, 3 sleeps each"


def test_the_restart_request_is_logged_once_before_exiting():
    clock = ManualClock()
    runner, _clock, _link, _display, _store, emitted = build_runner(
        clock=clock, link=FakeLink(line=b"")
    )

    with pytest.raises(FrameTimeout):
        bad_cycles(runner, clock, 20)

    messages = [item for item in emitted if "no meaningful frame" in str(item)]
    assert len(messages) == 1
    assert "300s" in messages[0]


def test_the_silence_limit_is_configurable():
    clock = ManualClock()
    runner, _clock, _link, _display, _store, _emitted = build_runner(
        clock=clock, link=FakeLink(line=b""), silence_limit=40.0
    )

    with pytest.raises(FrameTimeout) as excinfo:
        bad_cycles(runner, clock, 5)

    assert excinfo.value.seconds == pytest.approx(40.0)


def test_a_good_frame_resets_the_silence_timer():
    clock = ManualClock()
    link = FakeLink(line=b"")
    runner, _clock, _link, _display, _store, _emitted = build_runner(
        clock=clock, link=link
    )

    bad_cycles(runner, clock, 14)
    link.line = LINE
    bad_cycles(runner, clock, 1)
    link.line = b""
    bad_cycles(runner, clock, 14)

    with pytest.raises(FrameTimeout):
        bad_cycles(runner, clock, 1)



def test_run_does_not_swallow_the_silence_timeout():
    clock = ManualClock()
    runner, _clock, _link, _display, _store, _emitted = build_runner(
        clock=clock, link=FakeLink(line=b"")
    )

    with pytest.raises(FrameTimeout):
        runner.run()

import pytest

from heizungslogger import cli
from heizungslogger.runner import FrameTimeout


def test_missing_port_prints_help_and_fails(capsys):
    status = cli.main([])

    captured = capsys.readouterr()
    assert status != 0
    assert captured.out.startswith("No port defined\n\n")
    assert "usage:" in captured.out


def test_list_prints_sorted_ports(monkeypatch, capsys):
    monkeypatch.setattr(
        cli,
        "list_ports",
        lambda: [("/dev/ttyACM0", "Arduino", "USB VID:PID=1234"), ("/dev/ttyUSB0", "FTDI", "x")],
    )

    assert cli.main(["--list"]) == 0

    assert capsys.readouterr().out == (
        "/dev/ttyACM0: Arduino [USB VID:PID=1234]\n"
        "/dev/ttyUSB0: FTDI [x]\n"
    )


class FakeLink:
    def __init__(self, port):
        self.port = port
        self.opened = False
        self.closed = False

    def open(self):
        self.opened = True

    def close(self):
        self.closed = True


def run_with_fakes(monkeypatch, argv):
    links = []
    runners = []

    def make_link(port):
        link = FakeLink(port)
        links.append(link)
        return link

    class FakeRunner:
        def __init__(self, link, display, store, clock):
            runners.append((link, store.log_directory))

        def run(self):
            return None

    monkeypatch.setattr(cli, "PyserialLink", make_link)
    monkeypatch.setattr(cli, "Runner", FakeRunner)
    monkeypatch.setattr(cli, "LcdDisplay", lambda: "display")

    status = cli.main(argv)
    return status, links, runners


def test_port_is_opened_and_closed(monkeypatch):
    status, links, runners = run_with_fakes(monkeypatch, ["--port", "/dev/ttyUSB0"])

    assert status == 0
    assert links[0].port == "/dev/ttyUSB0"
    assert links[0].opened is True
    assert links[0].closed is True


def test_log_directory_defaults_to_current_directory(monkeypatch):
    _status, _links, runners = run_with_fakes(monkeypatch, ["--port", "/dev/ttyUSB0"])

    assert runners[0][1] == "./"


def test_log_directory_flag_is_honoured(monkeypatch):
    _status, _links, runners = run_with_fakes(
        monkeypatch, ["--port", "/dev/ttyUSB0", "--log_directory", "/var/log/heizung"]
    )

    assert runners[0][1] == "/var/log/heizung"


def test_link_is_closed_when_the_runner_raises(monkeypatch):
    class ExplodingRunner:
        def __init__(self, *args):
            pass

        def run(self):
            raise RuntimeError("boom")

    monkeypatch.setattr(cli, "PyserialLink", lambda port: FakeLink(port))
    monkeypatch.setattr(cli, "Runner", ExplodingRunner)
    monkeypatch.setattr(cli, "LcdDisplay", lambda: "display")
    links = []
    original = FakeLink.__init__

    def record(self, port):
        original(self, port)
        links.append(self)

    monkeypatch.setattr(FakeLink, "__init__", record)

    with pytest.raises(RuntimeError):
        cli.main(["--port", "/dev/ttyUSB0"])

    assert links[0].closed is True


def test_silence_timeout_exits_cleanly(monkeypatch, capsys):
    links = []

    def make_link(port):
        link = FakeLink(port)
        links.append(link)
        return link

    class SilentRunner:
        def __init__(self, *args):
            pass

        def run(self):
            raise FrameTimeout(300.0)

    monkeypatch.setattr(cli, "PyserialLink", make_link)
    monkeypatch.setattr(cli, "Runner", SilentRunner)
    monkeypatch.setattr(cli, "LcdDisplay", lambda: "display")

    status = cli.main(["--port", "/dev/ttyUSB0"])

    captured = capsys.readouterr()
    assert status == 1
    assert links[0].closed is True
    assert captured.out == (
        "no meaningful frame for 300s; exiting for a clean restart\n"
    )
    assert "Traceback" not in captured.out + captured.err

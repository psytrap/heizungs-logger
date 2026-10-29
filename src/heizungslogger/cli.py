"""Command-line surface.

Flags and messages match the legacy script. The one deliberate difference is
the exit status when ``--port`` is missing: the legacy ``exit()`` returned 0,
this returns 1 so that callers and supervisors can detect the misconfiguration.
"""

import argparse

from heizungslogger.clock import SystemClock
from heizungslogger.display import LcdDisplay
from heizungslogger.runner import FrameTimeout, Runner
from heizungslogger.serial_link import PyserialLink, list_ports
from heizungslogger.store import FileStore


def build_parser() -> argparse.ArgumentParser:
    """Return the argument parser with the legacy flags."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--list", help="List available serial devices", action="store_true")
    parser.add_argument("--log_directory", help="Directory to place the logs", type=str)
    parser.add_argument("--port", help="Send message to the serial port", type=str)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the logger. Returns the process exit status."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list is True:
        for port, desc, hwid in list_ports():
            print(f"{port}: {desc} [{hwid}]")
        return 0

    if args.port is None:
        print("No port defined")
        print()
        parser.print_help()
        return 1

    log_directory = args.log_directory if args.log_directory is not None else "./"

    link = PyserialLink(args.port)
    link.open()
    try:
        try:
            Runner(link, LcdDisplay(), FileStore(log_directory), SystemClock()).run()
        except FrameTimeout as exc:
            # A frame streak, not a crash: exit so systemd reopens the port.
            print(f"{exc}; exiting for a clean restart")
            return 1
    finally:
        link.close()
    return 0

#!/usr/bin/env python3
"""Entry point for the deployed systemd unit.

The unit's ``ExecStart`` points at this file, so it keeps working unchanged
while the implementation lives in the ``src/heizungslogger`` package.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from heizungslogger.cli import main  # noqa: E402 - path bootstrap must run first

if __name__ == "__main__":
    sys.exit(main())

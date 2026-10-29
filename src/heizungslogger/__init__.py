"""Multi-channel temperature logger for a heat pump.

Reads measurement frames from an Arduino over a serial line and appends them
to plain-text day files. Hardware libraries are imported lazily so that the
package can be imported (and tested) on any machine.
"""

from heizungslogger.frame import parse_frame
from heizungslogger.runner import Runner

__all__ = ["Runner", "parse_frame"]
__version__ = "0.1.0"

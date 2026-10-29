"""Frame parsing: bytes from the serial line to a list of fields.

Pure functions only, no I/O and no hardware import.
"""


def parse_frame(raw: bytes) -> list[str]:
    """Split one raw serial line into fields.

    Mirrors the legacy ``line.decode("utf-8").strip().split(" ")`` exactly,
    including its failure modes: undecodable bytes raise ``UnicodeDecodeError``
    and an empty line yields ``['']``.
    """
    return raw.decode("utf-8").strip().split(" ")

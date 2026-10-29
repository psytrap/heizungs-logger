#!/bin/sh
#
# Compile and run the host-side firmware frame test.
#
# No Arduino toolchain is required: the formatter is plain C++ and the sketch's
# Arduino-specific code paths are compiled out. Exits 0 with a "skipped" message
# when no C++ compiler is available (the Pi has none).
#
set -eu

REPO_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$REPO_ROOT"

CXX=${CXX:-g++}

if ! command -v "$CXX" >/dev/null 2>&1; then
	echo "skipped: no C++ compiler ($CXX) available"
	exit 0
fi

BINARY=$(mktemp "${TMPDIR:-/tmp}/frame_test.XXXXXX")
trap 'rm -f "$BINARY"' EXIT INT TERM

"$CXX" -std=c++17 -Wall -Wextra -Werror -I firmware \
	firmware/frame.cpp tests/firmware/frame_test.cpp -o "$BINARY"
"$BINARY" tests/fixtures/firmware_frames.tsv

#!/bin/sh
#
# Install, refresh or remove the heizungs_web systemd unit.
#
# The unit is copied verbatim from the repository root, so the checked-in file
# stays the single source of truth. Nothing is restarted unless --restart is
# given explicitly.
#
# Usage: scripts/install-web.sh [--dry-run] [--restart] [--uninstall]
#
# Environment overrides (used for testing):
#   UNIT_DIR    target unit directory      (default /etc/systemd/system)
#   SYSTEMCTL   systemctl binary or stub   (default systemctl)
#
set -eu

UNIT_NAME=heizungs_web.service
REPO_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
UNIT_SRC=$REPO_ROOT/$UNIT_NAME
UNIT_DIR=${UNIT_DIR:-/etc/systemd/system}
SYSTEMCTL=${SYSTEMCTL:-systemctl}

DRY_RUN=0
UNINSTALL=0
DO_RESTART=0

usage() {
	cat <<'EOF'
Install, refresh or remove the heizungs_web systemd unit.

Options:
  --dry-run     print the actions instead of performing them
  --restart     restart the service after installing (default: do not)
  --uninstall   disable, stop and remove the unit
  -h, --help    show this help

The script needs root for anything that touches the system (use sudo).
Use --dry-run as a normal user to preview.
EOF
}

say() { printf '%s\n' "$*"; }
warn() { printf 'warning: %s\n' "$*" >&2; }
die() { printf 'error: %s\n' "$*" >&2; exit 1; }

run() {
	if [ "$DRY_RUN" -eq 1 ]; then
		say "  would run: $*"
	else
		"$@"
	fi
}

while [ $# -gt 0 ]; do
	case $1 in
		--dry-run) DRY_RUN=1 ;;
		--restart) DO_RESTART=1 ;;
		--uninstall) UNINSTALL=1 ;;
		-h|--help) usage; exit 0 ;;
		*) die "unknown argument: $1 (try --help)" ;;
	esac
	shift
done

[ -f "$UNIT_SRC" ] || die "unit file not found: $UNIT_SRC"

if [ "$DRY_RUN" -eq 0 ] && [ "$(id -u)" -ne 0 ]; then
	die "must run as root (try: sudo $0)"
fi

exec_start=$(sed -n 's/^[[:space:]]*ExecStart[[:space:]]*=[[:space:]]*//p' "$UNIT_SRC" | head -n 1)
[ -n "$exec_start" ] || die "no ExecStart line in $UNIT_SRC"

log_dir=$(printf '%s\n' "$exec_start" | awk '{for (i = 2; i <= NF; i++) if ($(i - 1) == "--log_directory") {print $i; exit}}')
listen_port=$(printf '%s\n' "$exec_start" | awk '{for (i = 2; i <= NF; i++) if ($(i - 1) == "--port") {print $i; exit}}')
user_name=$(sed -n 's/^[[:space:]]*User[[:space:]]*=[[:space:]]*//p' "$UNIT_SRC" | head -n 1)

say "unit:        $UNIT_SRC"
say "destination: $UNIT_DIR/$UNIT_NAME"
say "exec:        $exec_start"
say "mode:        $([ "$UNINSTALL" -eq 1 ] && echo uninstall || echo install)$([ "$DRY_RUN" -eq 1 ] && echo ' (dry run)')"

if [ "$UNINSTALL" -eq 0 ]; then
	[ -n "$user_name" ] || warn "no User= in the unit"
	[ -n "$log_dir" ] || warn "--log_directory missing from ExecStart"
	if [ -n "$log_dir" ] && [ ! -d "$log_dir" ]; then
		warn "log directory does not exist: $log_dir (the page will answer 503)"
	fi
	if [ -n "$listen_port" ] && [ "$listen_port" -lt 1024 ]; then
		say "         port $listen_port is privileged; the unit grants CAP_NET_BIND_SERVICE"
	fi
fi

if [ "$UNINSTALL" -eq 1 ]; then
	say "disabling and stopping the unit"
	run "$SYSTEMCTL" disable --now "$UNIT_NAME" || warn "disable/stop reported an error (unit may already be gone)"
	say "removing $UNIT_DIR/$UNIT_NAME"
	run rm -f "$UNIT_DIR/$UNIT_NAME"
	run "$SYSTEMCTL" daemon-reload
	say "done; unit removed (log files are untouched)"
	exit 0
fi

say "installing unit"
run mkdir -p "$UNIT_DIR"
run cp "$UNIT_SRC" "$UNIT_DIR/$UNIT_NAME"
run chmod 0644 "$UNIT_DIR/$UNIT_NAME"
run "$SYSTEMCTL" daemon-reload
run "$SYSTEMCTL" enable "$UNIT_NAME"

if [ "$DO_RESTART" -eq 1 ]; then
	say "restarting the unit"
	run "$SYSTEMCTL" restart "$UNIT_NAME"
else
	say "not restarting (pass --restart to do so)"
fi

say "done"

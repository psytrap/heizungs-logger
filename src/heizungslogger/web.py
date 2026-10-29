"""Read-only seven-day view over the day files.

Everything here is pure: no sockets, no hardware, no writes. ``web_server`` is
the only module that speaks HTTP, so the rendering can be tested from fixture
files alone.

Two data-shape facts drive the design (see ``docs/RECORDING.md`` §3):

* a day file is named after a **naive UTC value**, so the seven-day window is
  computed in UTC and the labels are rendered in local time;
* the timestamp inside a record is a **UTC clock value carrying a local offset
  label**, so the literal value is used as UTC and the label is ignored.
"""

import ast
import datetime
import html
import json
from dataclasses import dataclass

from heizungslogger.store import record_path

DAYS = 7
BUCKET = datetime.timedelta(minutes=10)
BUCKETS_PER_DAY = 24 * 60 // 10
BUCKET_COUNT = DAYS * BUCKETS_PER_DAY
REFRESH_SECONDS = 600

CHART_WIDTH = 960
CHART_HEIGHT = 150
PAD_LEFT = 46
PAD_RIGHT = 10
PAD_TOP = 10
PAD_BOTTOM = 22
PLOT_WIDTH = CHART_WIDTH - PAD_LEFT - PAD_RIGHT
PLOT_HEIGHT = CHART_HEIGHT - PAD_TOP - PAD_BOTTOM

COLORS = ("#c0392b", "#e67e22", "#b7950b", "#1e8449", "#2471a3", "#7d3c98")
NICE_STEPS = (0.5, 1.0, 2.0, 5.0, 10.0, 20.0)


@dataclass(frozen=True)
class Sample:
    """One record: a naive UTC instant plus its temperatures."""

    moment: datetime.datetime
    temps: tuple[float, ...]


@dataclass(frozen=True)
class Bucket:
    """One 10-minute cell of the window."""

    start: datetime.datetime
    count: int
    low: tuple[float | None, ...]
    mean: tuple[float | None, ...]
    high: tuple[float | None, ...]


def parse_moment(text: str) -> datetime.datetime | None:
    """Return the instant stored in ``text``, ignoring its offset label.

    The writer labels a naive UTC value with the local offset, so the literal
    clock reading *is* UTC. ``fromisoformat`` parses the label and dropping the
    tzinfo keeps the value instead of shifting it by an hour.
    """
    try:
        return datetime.datetime.fromisoformat(text).replace(tzinfo=None)
    except ValueError:
        return None


def parse_line(line: str) -> Sample | None:
    """Parse one day-file line. Anything unexpected returns ``None``."""
    text = line.strip()
    if not text.startswith("["):
        return None
    try:
        fields = ast.literal_eval(text)
    except (ValueError, SyntaxError):
        return None
    if not isinstance(fields, list) or len(fields) < 3:
        return None

    values = [str(item) for item in fields]
    moment = parse_moment(values[-1])
    if moment is None:
        return None

    end = values.index("Input") if "Input" in values else len(values) - 1
    start = 1 if values[0] == "Temp" else 0
    try:
        temps = tuple(float(value) for value in values[start:end])
    except ValueError:
        return None
    if not temps:
        return None
    return Sample(moment, temps)


def window_start(now: datetime.datetime) -> datetime.datetime:
    """UTC midnight of the oldest day in the window."""
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return midnight - datetime.timedelta(days=DAYS - 1)


def window_paths(log_directory: str, start: datetime.datetime) -> list[str]:
    """The seven day-file paths for a window starting at ``start``."""
    return [
        record_path(log_directory, start + datetime.timedelta(days=offset))
        for offset in range(DAYS)
    ]


def load_samples(paths: list[str]) -> list[Sample]:
    """Read every parsable record; missing files and bad lines are skipped."""
    samples = []
    for path in paths:
        try:
            with open(path, encoding="utf-8", errors="replace") as handle:
                for line in handle:
                    sample = parse_line(line)
                    if sample is not None:
                        samples.append(sample)
        except OSError:
            continue
    return samples


def sensor_count(samples: list[Sample]) -> int:
    """The dominant temperature count, i.e. the frame shape in use."""
    counts: dict[int, int] = {}
    for sample in samples:
        counts[len(sample.temps)] = counts.get(len(sample.temps), 0) + 1
    if not counts:
        return 0
    return max(counts, key=lambda size: (counts[size], size))


def bucketize(
    samples: list[Sample],
    start: datetime.datetime,
    count: int = BUCKET_COUNT,
) -> list[Bucket]:
    """Aggregate samples into ``count`` equal buckets from ``start``."""
    size = BUCKET.total_seconds()
    width = sensor_count(samples)
    sums = [[0.0] * width for _ in range(count)]
    lows: list[list[float | None]] = [[None] * width for _ in range(count)]
    highs: list[list[float | None]] = [[None] * width for _ in range(count)]
    seen = [0] * count

    for sample in samples:
        index = int((sample.moment - start).total_seconds() // size)
        if not 0 <= index < count:
            continue
        seen[index] += 1
        for column, value in enumerate(sample.temps[:width]):
            sums[index][column] += value
            low = lows[index][column]
            high = highs[index][column]
            lows[index][column] = value if low is None else min(low, value)
            highs[index][column] = value if high is None else max(high, value)

    buckets = []
    for index in range(count):
        taken = seen[index]
        mean = tuple(sums[index][column] / taken if taken else None for column in range(width))
        buckets.append(
            Bucket(
                start + datetime.timedelta(seconds=index * size),
                taken,
                tuple(lows[index]),
                mean,
                tuple(highs[index]),
            )
        )
    return buckets


def day_grid(start: datetime.datetime, tz) -> list[tuple[float, str]]:
    """Local midnights inside the window as ``(bucket_index, label)``."""
    span = datetime.timedelta(days=DAYS).total_seconds()
    first_day = start.replace(tzinfo=datetime.timezone.utc).astimezone(tz).date()
    lines = []
    for offset in range(DAYS + 1):
        day = first_day + datetime.timedelta(days=offset)
        midnight = datetime.datetime.combine(day, datetime.time.min, tzinfo=tz)
        utc = midnight.astimezone(datetime.timezone.utc).replace(tzinfo=None)
        seconds = (utc - start).total_seconds()
        if 0.0 <= seconds <= span:
            index = seconds / span * BUCKET_COUNT
            lines.append((index, f"{day.day:02d}.{day.month:02d}"))
    return lines


def value_range(buckets: list[Bucket], column: int) -> tuple[float, float] | None:
    """Padded y range for one sensor, or ``None`` when it has no data."""
    values = [bucket.mean[column] for bucket in buckets if bucket.mean[column] is not None]
    if not values:
        return None
    low, high = min(values), max(values)
    if high - low < 1.0:
        middle = (high + low) / 2
        low, high = middle - 0.5, middle + 0.5
    pad = (high - low) * 0.08
    return low - pad, high + pad


def tick_step(low: float, high: float) -> float:
    """Smallest nice step that yields at most five horizontal lines."""
    for step in NICE_STEPS:
        if (high - low) / step <= 4.5:
            return step
    return NICE_STEPS[-1]


def x_center(index: float, count: int) -> float:
    return PAD_LEFT + (index + 0.5) * PLOT_WIDTH / count


def x_edge(index: float, count: int) -> float:
    return PAD_LEFT + index * PLOT_WIDTH / count


def y_position(value: float, low: float, high: float) -> float:
    return PAD_TOP + (high - value) / (high - low) * PLOT_HEIGHT


def segments(buckets: list[Bucket], column: int, low: float, high: float) -> list[str]:
    """Polyline point lists, one per contiguous run of data."""
    count = len(buckets)
    runs: list[str] = []
    points: list[str] = []
    for index, bucket in enumerate(buckets):
        value = bucket.mean[column]
        if value is None:
            if len(points) > 1:
                runs.append(" ".join(points))
            points = []
            continue
        points.append(f"{x_center(index, count):.1f},{y_position(value, low, high):.1f}")
    if len(points) > 1:
        runs.append(" ".join(points))
    return runs


def _chart(chart_index: int, name: str, buckets: list[Bucket], column: int, tz) -> str:
    bounds = value_range(buckets, column)
    if bounds is None:
        return (
            f'<section><h2>{html.escape(name)}</h2>'
            '<p class="hint">no data in this window</p></section>'
        )
    low, high = bounds
    step = tick_step(low, high)
    count = len(buckets)

    parts = [
        (
            f'<svg class="chart" viewBox="0 0 {CHART_WIDTH} {CHART_HEIGHT}" '
            f'data-chart="{chart_index}" data-left="{PAD_LEFT}" '
            f'data-width="{PLOT_WIDTH}" data-count="{count}" role="img" '
            f'aria-label="{html.escape(name)} over seven days">'
        )
    ]

    tick = (int(low / step) + 1) * step
    while tick < high:
        y = y_position(tick, low, high)
        parts.append(
            f'<line class="axis" x1="{PAD_LEFT}" x2="{PAD_LEFT + PLOT_WIDTH}" '
            f'y1="{y:.1f}" y2="{y:.1f}"/>'
        )
        parts.append(f'<text x="{PAD_LEFT - 6}" y="{y + 3:.1f}" text-anchor="end">{tick:g}</text>')
        tick += step

    for index, label in day_grid(buckets[0].start if buckets else low, tz):
        x = x_edge(index, count)
        parts.append(
            f'<line class="dayline" x1="{x:.1f}" x2="{x:.1f}" y1="{PAD_TOP}" '
            f'y2="{PAD_TOP + PLOT_HEIGHT}"/>'
        )
        parts.append(
            f'<text x="{x + 2:.1f}" y="{CHART_HEIGHT - 6}" text-anchor="start">{label}</text>'
        )

    color = COLORS[chart_index % len(COLORS)]
    for run in segments(buckets, column, low, high):
        parts.append(f'<polyline class="line" stroke="{color}" points="{run}"/>')

    parts.append(
        f'<g class="readout" hidden><line class="crosshair" x1="0" x2="0" '
        f'y1="{PAD_TOP}" y2="{PAD_TOP + PLOT_HEIGHT}"/><text x="0" y="18"></text></g>'
    )
    parts.append("</svg>")
    return f'<section><h2>{html.escape(name)}</h2>{"".join(parts)}</section>'


def _format_local(moment: datetime.datetime, tz) -> str:
    return moment.replace(tzinfo=datetime.timezone.utc).astimezone(tz).strftime("%d.%m. %H:%M")


def _labels(start: datetime.datetime, count: int, tz) -> list[str]:
    return [
        _format_local(start + BUCKET * index, tz)
        for index in range(count)
    ]


def render_page(
    buckets: list[Bucket],
    samples: list[Sample],
    start: datetime.datetime,
    now: datetime.datetime,
    tz,
) -> str:
    """Build the whole page. Pure string work, no I/O."""
    width = sensor_count(samples)
    newest = max((sample.moment for sample in samples), default=None)
    age = int((now - newest).total_seconds()) if newest is not None else None
    empty = sum(1 for bucket in buckets if not bucket.count)

    if newest is None:
        status = "no records in the last seven days"
    else:
        status = (
            f"newest record {_format_local(newest, tz)} "
            f"({age} s ago) &middot; {len(samples)} records &middot; "
            f"{empty} of {len(buckets)} buckets empty"
        )

    charts = "".join(
        _chart(column, f"T{column + 1}", buckets, column, tz) for column in range(max(width, 0))
    )
    if not charts:
        charts = '<p class="hint">nothing to plot yet</p>'

    series = {
        "labels": _labels(start, len(buckets), tz),
        "charts": [
            {
                "values": [
                    None
                    if bucket.mean[column] is None
                    else [
                        round(bucket.mean[column], 2),
                        round(bucket.low[column], 2),
                        round(bucket.high[column], 2),
                    ]
                    for bucket in buckets
                ]
            }
            for column in range(width)
        ],
    }
    payload = json.dumps(series, separators=(",", ":")).replace("</", "<\\/")

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="{REFRESH_SECONDS}">
<title>Heizungslogger &middot; last seven days</title>
<style>
:root {{ color-scheme: light dark; }}
body {{ font: 14px/1.45 system-ui, sans-serif; margin: 0 auto; max-width: 1000px; padding: 16px; }}
h1 {{ font-size: 19px; margin: 0 0 2px; }}
h2 {{ font-size: 13px; font-weight: 600; margin: 0 0 2px; }}
#status {{ color: #777; margin: 0 0 18px; }}
.grid {{ display: grid; gap: 16px; }}
.chart {{ width: 100%; height: auto; display: block; touch-action: none; }}
svg text {{ font-size: 10px; fill: currentColor; }}
.axis {{ stroke: currentColor; stroke-opacity: .22; stroke-width: 1; }}
.dayline {{ stroke: currentColor; stroke-opacity: .15; stroke-dasharray: 2 3; }}
.line {{ fill: none; stroke-width: 1.4; }}
.crosshair {{ stroke: currentColor; stroke-opacity: .5; stroke-dasharray: 3 3; }}
.readout text {{ font-size: 11px; font-weight: 600; }}
.hint {{ color: #777; font-size: 12px; margin: 4px 0; }}
footer {{ color: #777; font-size: 12px; margin-top: 18px; }}
</style>
</head>
<body>
<h1>Heizungslogger</h1>
<p id="status">{status}</p>
<div class="grid">
{charts}
</div>
<footer>Point at a chart to read the nearest 10-minute value. Times are local;
records are stored in UTC. Page reloads every {REFRESH_SECONDS // 60} minutes.</footer>
<script type="application/json" id="chart-data">{payload}</script>
<script>
(function () {{
  var data = JSON.parse(document.getElementById("chart-data").textContent);
  function nearest(values, index) {{
    if (values[index]) return index;
    for (var step = 1; step < 40; step += 1) {{
      if (index - step >= 0 && values[index - step]) return index - step;
      if (index + step < values.length && values[index + step]) return index + step;
    }}
    return -1;
  }}
  Array.prototype.forEach.call(document.querySelectorAll("svg.chart"), function (svg) {{
    var series = data.charts[Number(svg.dataset.chart)].values;
    var left = Number(svg.dataset.left);
    var width = Number(svg.dataset.width);
    var count = Number(svg.dataset.count);
    var group = svg.querySelector(".readout");
    var rule = svg.querySelector(".crosshair");
    var label = svg.querySelector(".readout text");
    svg.addEventListener("pointermove", function (event) {{
      var frame = svg.getBoundingClientRect();
      var x = (event.clientX - frame.left) * 960 / frame.width;
      var guess = Math.round((x - left) / width * count - 0.5);
      var index = nearest(series, Math.max(0, Math.min(count - 1, guess)));
      if (index < 0) {{ group.setAttribute("hidden", ""); return; }}
      var point = series[index];
      var cx = left + (index + 0.5) * width / count;
      rule.setAttribute("x1", cx);
      rule.setAttribute("x2", cx);
      var onRight = cx > left + width * 0.55;
      label.setAttribute("text-anchor", onRight ? "end" : "start");
      label.setAttribute("x", onRight ? cx - 6 : cx + 6);
      label.textContent = data.labels[index] + "   " + point[0].toFixed(1) + " \u00b0C   (" +
        point[1].toFixed(1) + " \u2013 " + point[2].toFixed(1) + ")";
      group.removeAttribute("hidden");
    }});
    svg.addEventListener("pointerleave", function () {{
      group.setAttribute("hidden", "");
    }});
  }});
}})();
</script>
</body>
</html>"""
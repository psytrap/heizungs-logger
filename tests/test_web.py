import datetime

import dateutil.tz

from heizungslogger import web, web_server
from heizungslogger.store import FileStore

TZ = dateutil.tz.gettz("Europe/Berlin")
BASE = datetime.datetime(2026, 10, 29, 12, 0, 0)
LINE = (
    "['Temp', '27.1', '28.6', '29.3', '26.6', '28.8', '15.7', "
    "'Input', 'off', 'off', '2026-10-29T14:18:42.213722+01:00']"
)


def write(directory, moment, temps=("21.5", "22.0", "23.0", "24.0", "25.0", "26.0")):
    FileStore(str(directory)).append(["Temp", *temps, "Input", "off", "off"], moment)


def test_parse_line_reads_a_live_record():
    sample = web.parse_line(LINE)

    assert sample is not None
    assert sample.temps == (27.1, 28.6, 29.3, 26.6, 28.8, 15.7)


def test_parse_line_treats_the_value_as_utc_not_as_the_label():
    # The writer labels a UTC value with the local offset; the value is UTC.
    assert web.parse_line(LINE).moment == datetime.datetime(2026, 10, 29, 14, 18, 42, 213722)


def test_parse_line_skips_junk_and_truncated_lines():
    for line in ("", "garbage\n", "['Temp', '1.0'", "['Temp', '1.0', 'x']", "[]\n"):
        assert web.parse_line(line) is None


def test_window_paths_are_seven_utc_days():
    start = web.window_start(BASE)
    paths = web.window_paths("/logs", start)

    assert start == datetime.datetime(2026, 10, 23)
    assert len(paths) == 7
    assert paths[0].endswith("LOG-2026-10-23.json")
    assert paths[-1].endswith("LOG-2026-10-29.json")


def test_load_samples_skips_missing_files_and_bad_lines(tmp_path):
    (tmp_path / "LOG-2026-10-29.json").write_text(LINE + "\nnot a record\n")
    paths = [
        str(tmp_path / "LOG-2026-10-28.json"),
        str(tmp_path / "LOG-2026-10-29.json"),
    ]

    samples = web.load_samples(paths)

    assert len(samples) == 1


def test_bucketize_keeps_min_mean_and_max():
    start = web.window_start(BASE)
    samples = [
        web.Sample(BASE, (20.0, 1.0, 1.0, 1.0, 1.0, 1.0)),
        web.Sample(BASE + datetime.timedelta(minutes=5), (24.0, 1.0, 1.0, 1.0, 1.0, 1.0)),
        web.Sample(BASE + datetime.timedelta(minutes=20), (22.0, 1.0, 1.0, 1.0, 1.0, 1.0)),
    ]

    buckets = web.bucketize(samples, start)

    assert len(buckets) == web.BUCKET_COUNT
    index = int((BASE - start).total_seconds() // 600)
    assert buckets[index].count == 2
    assert buckets[index].low[0] == 20.0
    assert buckets[index].mean[0] == 22.0
    assert buckets[index].high[0] == 24.0
    assert buckets[index + 1].count == 0
    assert buckets[index + 1].mean[0] is None


def test_sensor_count_picks_the_dominant_shape():
    six = web.Sample(BASE, (1.0,) * 6)
    four = web.Sample(BASE, (1.0,) * 4)

    assert web.sensor_count([six, six, four]) == 6
    assert web.sensor_count([]) == 0


def test_day_grid_is_locked_to_local_midnights():
    start = web.window_start(BASE)
    grid = web.day_grid(start, TZ)

    # Local midnights sit at 22:00 UTC while CEST is in force (until 25.10) and
    # at 23:00 UTC afterwards, so the grid is not evenly spaced across the DST
    # change: 132 buckets for 24.10, then 23:00 UTC for the rest.
    assert len(grid) == 7
    assert [label for _index, label in grid] == [
        "24.10",
        "25.10",
        "26.10",
        "27.10",
        "28.10",
        "29.10",
        "30.10",
    ]
    assert grid[0][0] == 132.0
    assert grid[-1][0] == 1002.0


def test_render_page_draws_one_chart_per_sensor():
    start = web.window_start(BASE)
    samples = [web.Sample(BASE, (20.0, 21.0, 22.0, 23.0, 24.0, 25.0))]
    buckets = web.bucketize(samples, start)

    page = web.render_page(buckets, samples, start, BASE, TZ)

    assert page.count('<svg class="chart"') == 6
    assert page.count('http-equiv="refresh" content="600"') == 1
    assert "<table" not in page
    assert "<h2>T6</h2>" in page
    assert "newest record" in page


def test_render_page_says_so_when_there_is_nothing():
    start = web.window_start(BASE)
    page = web.render_page([], [], start, BASE, TZ)

    assert "no records in the last seven days" in page
    assert "nothing to plot yet" in page


def test_app_returns_503_for_a_missing_directory(tmp_path):
    app = web_server.App(str(tmp_path / "gone"), tz=TZ)

    status, body = app.page(BASE)

    assert status == 503
    assert b"log directory not found" in body


def test_app_serves_the_day_files(tmp_path):
    write(tmp_path, BASE)
    app = web_server.App(str(tmp_path), tz=TZ)

    status, body = app.page(BASE)

    assert status == 200
    assert b"T1" in body
    assert b"newest record" in body


def test_app_reuses_the_page_until_a_file_changes(tmp_path):
    write(tmp_path, BASE)
    app = web_server.App(str(tmp_path), tz=TZ)
    first = app.page(BASE)[1]

    assert app.page(BASE + datetime.timedelta(seconds=30))[1] is first

    write(tmp_path, BASE + datetime.timedelta(seconds=20))
    assert app.page(BASE + datetime.timedelta(seconds=40))[1] is not first


def test_app_rebuilds_when_the_result_is_older_than_the_ttl(tmp_path):
    write(tmp_path, BASE)
    app = web_server.App(str(tmp_path), tz=TZ, refresh_seconds=0)
    first = app.page(BASE)[1]

    assert app.page(BASE + datetime.timedelta(seconds=1))[1] is not first

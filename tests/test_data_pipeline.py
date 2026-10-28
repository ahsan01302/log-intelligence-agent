from datetime import UTC, datetime

from log_intel.chunking import build_chunks
from log_intel.generator import generate, load_labels, write_dataset
from log_intel.parsing import parse_file, parse_line


def test_generator_is_deterministic():
    assert generate(seed=3) == generate(seed=3)
    assert generate(seed=3)[0] != generate(seed=4)[0]


def test_labels_point_at_the_injected_lines():
    lines, labels = generate(seed=11)
    assert len(labels.incidents) == 4
    for inc in labels.incidents:
        assert len(inc.root_cause_lines) == 2
        root_text = " ".join(lines[n - 1] for n in inc.root_cause_lines).lower()
        assert any(kw in root_text for kw in inc.keywords), inc.kind
    assert "Ignore previous instructions" in lines[labels.injection_lines[0] - 1]


def test_write_and_load_dataset_round_trip(tmp_path):
    log_path, labels_path = write_dataset(tmp_path, seed=5, minutes=20)
    labels = load_labels(labels_path)
    assert log_path.name == labels.file
    total = len(log_path.read_text(encoding="utf-8").splitlines())
    assert all(n <= total for inc in labels.incidents for n in inc.root_cause_lines)


def test_parse_structured_line():
    rec = parse_line("a.log", 7, "2026-03-14T09:00:01.250Z ERROR orders [req=ab12] pool exhausted")
    assert rec.timestamp == datetime(2026, 3, 14, 9, 0, 1, 250000, tzinfo=UTC)
    assert (rec.level, rec.service, rec.request_id, rec.message) == (
        "ERROR",
        "orders",
        "ab12",
        "pool exhausted",
    )
    assert (rec.file, rec.line_no) == ("a.log", 7)


def test_parse_other_formats_without_failing():
    rec = parse_line("b.log", 1, "2026-03-14 09:00:01,123 WARNING something happened")
    assert rec.timestamp is not None and rec.level == "WARN"
    rec = parse_line("b.log", 2, "    at com.example.Foo.bar(Foo.java:42)")
    assert rec.timestamp is None and rec.level is None


def test_parse_file_tolerates_non_utf8_and_keeps_line_numbers(tmp_path):
    p = tmp_path / "latin1.log"
    p.write_bytes(
        b"2026-03-14T09:00:00Z INFO svc caf\xe9 ok\n\n2026-03-14T09:00:01Z ERROR svc boom\n"
    )
    records = list(parse_file(p))
    assert [r.line_no for r in records] == [1, 3]  # blank line skipped, numbering kept
    assert "�" in records[0].raw


def _records(lines):
    return [parse_line("x.log", i, line) for i, line in enumerate(lines, start=1)]


def test_time_chunks_split_on_window_and_keep_line_ranges():
    recs = _records(
        [
            "2026-03-14T09:00:00Z INFO a one",
            "2026-03-14T09:00:10Z INFO a two",
            "    continuation without timestamp",
            "2026-03-14T09:01:00Z INFO a three",
        ]
    )
    chunks = build_chunks(recs, window_seconds=30)
    assert [(c.start_line, c.end_line) for c in chunks] == [(1, 3), (4, 4)]
    assert chunks[0].id == "C1" and "continuation" in chunks[0].text


def test_chunks_respect_max_lines_and_file_boundaries():
    recs = _records([f"2026-03-14T09:00:0{i}Z INFO a l{i}" for i in range(5)])
    other = [parse_line("y.log", 1, "2026-03-14T09:00:05Z INFO a other")]
    chunks = build_chunks(recs + other, max_lines=2)
    assert [(c.file, c.start_line, c.end_line) for c in chunks] == [
        ("x.log", 1, 2),
        ("x.log", 3, 4),
        ("x.log", 5, 5),
        ("y.log", 1, 1),
    ]


def test_request_chunks_group_by_request_id():
    recs = _records(
        [
            "2026-03-14T09:00:00Z INFO a [req=r1] start",
            "2026-03-14T09:00:01Z INFO a [req=r2] other",
            "2026-03-14T09:00:02Z ERROR a [req=r1] failed",
        ]
    )
    chunks = build_chunks(recs, strategy="request")
    r1 = next(c for c in chunks if c.request_ids == ["r1"])
    assert "start" in r1.text and "failed" in r1.text

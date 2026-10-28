"""Group log records into chunks that span an incident instead of a single line."""

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Literal

from log_intel.parsing import LogRecord

Strategy = Literal["time", "request"]


@dataclass
class Chunk:
    id: str
    file: str
    start_line: int
    end_line: int
    start_ts: str | None
    end_ts: str | None
    text: str
    request_ids: list[str] = field(default_factory=list)

    def overlaps(self, file: str, lines: Iterable[int]) -> bool:
        return file == self.file and any(self.start_line <= n <= self.end_line for n in lines)


def _make_chunk(index: int, records: list[LogRecord]) -> Chunk:
    stamps = [r.timestamp for r in records if r.timestamp]
    return Chunk(
        id=f"C{index}",
        file=records[0].file,
        start_line=records[0].line_no,
        end_line=records[-1].line_no,
        start_ts=min(stamps).isoformat() if stamps else None,
        end_ts=max(stamps).isoformat() if stamps else None,
        text="\n".join(r.raw for r in records),
        request_ids=sorted({r.request_id for r in records if r.request_id}),
    )


def chunk_by_time(
    records: Iterable[LogRecord], window_seconds: int = 30, max_lines: int = 40
) -> list[list[LogRecord]]:
    """Consecutive lines of one file within a time window. Lines without a timestamp join
    the current group, so stack traces stay with the line that raised them."""
    window = timedelta(seconds=window_seconds)
    groups: list[list[LogRecord]] = []
    current: list[LogRecord] = []
    anchor = None
    for rec in records:
        new_file = bool(current) and rec.file != current[-1].file
        expired = (
            rec.timestamp is not None and anchor is not None and rec.timestamp - anchor > window
        )
        if current and (new_file or expired or len(current) >= max_lines):
            groups.append(current)
            current, anchor = [], None
        current.append(rec)
        if anchor is None and rec.timestamp is not None:
            anchor = rec.timestamp
    if current:
        groups.append(current)
    return groups


def chunk_by_request(records: Iterable[LogRecord], max_lines: int = 40) -> list[list[LogRecord]]:
    """Lines sharing a request id; lines without one fall back to time grouping."""
    by_req: dict[tuple[str, str], list[LogRecord]] = {}
    loose: list[LogRecord] = []
    for rec in records:
        if rec.request_id:
            by_req.setdefault((rec.file, rec.request_id), []).append(rec)
        else:
            loose.append(rec)
    groups = [g[i : i + max_lines] for g in by_req.values() for i in range(0, len(g), max_lines)]
    groups += chunk_by_time(loose, max_lines=max_lines)
    return sorted(groups, key=lambda g: (g[0].file, g[0].line_no))


def build_chunks(
    records: Iterable[LogRecord],
    strategy: Strategy = "time",
    window_seconds: int = 30,
    max_lines: int = 40,
) -> list[Chunk]:
    if strategy == "request":
        groups = chunk_by_request(records, max_lines)
    else:
        groups = chunk_by_time(records, window_seconds, max_lines)
    return [_make_chunk(i, g) for i, g in enumerate(groups, start=1)]

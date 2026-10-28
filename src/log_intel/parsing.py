"""Turn raw log files into records that keep their file and line number."""

import re
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

# 2026-03-14T09:00:00.123Z ERROR orders [req=ab12cd34] message
STRUCTURED = re.compile(
    r"^(?P<ts>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?(?:Z|[+-]\d{2}:?\d{2})?)\s+"
    r"(?P<level>TRACE|DEBUG|INFO|WARN|WARNING|ERROR|FATAL|CRITICAL)\s+"
    r"(?P<service>[\w.-]+)\s+"
    r"(?:\[req=(?P<req>[\w-]+)\]\s+)?"
    r"(?P<msg>.*)$"
)
# Fallback for other formats: a leading ISO-like timestamp and a level word anywhere.
LEADING_TS = re.compile(r"^\[?(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?)")
LEVEL_WORD = re.compile(r"\b(TRACE|DEBUG|INFO|WARN|WARNING|ERROR|FATAL|CRITICAL)\b")


@dataclass(frozen=True)
class LogRecord:
    file: str
    line_no: int
    timestamp: datetime | None
    level: str | None
    service: str | None
    request_id: str | None
    message: str
    raw: str


def _parse_ts(text: str) -> datetime | None:
    text = text.replace(",", ".").replace(" ", "T", 1)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        ts = datetime.fromisoformat(text)
    except ValueError:
        return None
    return ts if ts.tzinfo else ts.replace(tzinfo=UTC)


def parse_line(file: str, line_no: int, raw: str) -> LogRecord:
    m = STRUCTURED.match(raw)
    if m:
        return LogRecord(
            file=file,
            line_no=line_no,
            timestamp=_parse_ts(m["ts"]),
            level=m["level"].replace("WARNING", "WARN"),
            service=m["service"],
            request_id=m["req"],
            message=m["msg"],
            raw=raw,
        )
    ts = LEADING_TS.match(raw)
    level = LEVEL_WORD.search(raw)
    return LogRecord(
        file=file,
        line_no=line_no,
        timestamp=_parse_ts(ts[1]) if ts else None,
        level=level[1].replace("WARNING", "WARN") if level else None,
        service=None,
        request_id=None,
        message=raw,
        raw=raw,
    )


def parse_file(path: Path, display_name: str | None = None) -> Iterator[LogRecord]:
    """Stream records from a file. Undecodable bytes are replaced, never fatal."""
    name = display_name or path.name
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line_no, line in enumerate(f, start=1):
            raw = line.rstrip("\r\n")
            if raw.strip():
                yield parse_line(name, line_no, raw)

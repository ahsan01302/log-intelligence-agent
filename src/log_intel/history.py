"""Past investigations, kept in a local SQLite file next to the index."""

import sqlite3
import uuid
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel

from log_intel.answer import Answer


class HistoryItem(BaseModel):
    id: str
    created_at: str
    question: str
    status: str
    model: str | None
    top_cause: str | None


class Investigation(HistoryItem):
    answer: Answer


class HistoryStore:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as db, db:
            db.execute(
                """CREATE TABLE IF NOT EXISTS investigations (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    question TEXT NOT NULL,
                    status TEXT NOT NULL,
                    model TEXT,
                    top_cause TEXT,
                    answer_json TEXT NOT NULL
                )"""
            )

    def _connect(self) -> sqlite3.Connection:
        # One short-lived connection per call: API requests run on worker threads.
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        return db

    def add(self, answer: Answer) -> HistoryItem:
        item = HistoryItem(
            id=uuid.uuid4().hex[:12],
            created_at=datetime.now(UTC).isoformat(timespec="seconds"),
            question=answer.question,
            status=answer.status,
            model=answer.model,
            top_cause=answer.hypotheses[0].cause if answer.hypotheses else None,
        )
        with closing(self._connect()) as db, db:
            db.execute(
                "INSERT INTO investigations VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    item.id,
                    item.created_at,
                    item.question,
                    item.status,
                    item.model,
                    item.top_cause,
                    answer.model_dump_json(),
                ),
            )
        return item

    def list(self, limit: int = 50) -> list[HistoryItem]:
        with closing(self._connect()) as db:
            rows = db.execute(
                "SELECT id, created_at, question, status, model, top_cause FROM investigations "
                "ORDER BY created_at DESC, rowid DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [HistoryItem(**dict(r)) for r in rows]

    def get(self, item_id: str) -> Investigation | None:
        with closing(self._connect()) as db:
            row = db.execute("SELECT * FROM investigations WHERE id = ?", (item_id,)).fetchone()
        if row is None:
            return None
        data = dict(row)
        answer = Answer.model_validate_json(data.pop("answer_json"))
        return Investigation(**data, answer=answer)

    def delete(self, item_id: str) -> bool:
        with closing(self._connect()) as db, db:
            return db.execute("DELETE FROM investigations WHERE id = ?", (item_id,)).rowcount > 0

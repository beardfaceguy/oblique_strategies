import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

from sidestep.store import (
    Card,
    DataStore,
    Draw,
    Outcome,
    SaveCardsResult,
    StoreError,
    UnknownDrawError,
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS cards (
    deck TEXT NOT NULL,
    id TEXT NOT NULL,
    text TEXT NOT NULL,
    PRIMARY KEY (deck, id)
);

CREATE TABLE IF NOT EXISTS draws (
    id TEXT PRIMARY KEY,
    time TEXT NOT NULL,
    deck TEXT NOT NULL,
    card_id TEXT NOT NULL,
    card_text TEXT NOT NULL,
    context TEXT NOT NULL,
    project TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS outcomes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    draw_id TEXT NOT NULL REFERENCES draws (id),
    time TEXT NOT NULL,
    helped INTEGER NOT NULL,
    note TEXT NOT NULL,
    code_diff TEXT NOT NULL,
    commit_sha TEXT NOT NULL,
    test_command TEXT NOT NULL,
    tests_failing_before INTEGER,
    tests_failing_after INTEGER,
    test_output TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS outcomes_draw_id ON outcomes (draw_id);
"""

OUTCOME_COLUMNS = (
    "draw_id",
    "time",
    "helped",
    "note",
    "code_diff",
    "commit_sha",
    "test_command",
    "tests_failing_before",
    "tests_failing_after",
    "test_output",
)


class SQLiteStore(DataStore):
    def __init__(self, path: Path):
        self.path = path
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with self._connect() as connection:
                connection.executescript(SCHEMA)
        except (OSError, sqlite3.Error) as error:
            raise StoreError(f"cannot open SQLite database {path}: {error}") from error

    def location(self) -> str:
        return str(self.path)

    def _connect(self):
        # A connection per operation: MCP runs sync tools on worker threads, and
        # sqlite3 connections must not be shared across threads.
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return closing(connection)

    def save_cards(self, cards: list[Card]) -> SaveCardsResult:
        added = updated = unchanged = 0
        try:
            with self._connect() as connection, connection:
                for card in cards:
                    row = connection.execute(
                        "SELECT text FROM cards WHERE deck = ? AND id = ?", (card.deck, card.id)
                    ).fetchone()
                    if row is None:
                        connection.execute(
                            "INSERT INTO cards (deck, id, text) VALUES (?, ?, ?)",
                            (card.deck, card.id, card.text),
                        )
                        added += 1
                    elif row["text"] != card.text:
                        connection.execute(
                            "UPDATE cards SET text = ? WHERE deck = ? AND id = ?",
                            (card.text, card.deck, card.id),
                        )
                        updated += 1
                    else:
                        unchanged += 1
        except sqlite3.Error as error:
            raise StoreError(f"cannot save cards: {error}") from error
        return SaveCardsResult(added=added, updated=updated, unchanged=unchanged)

    def get_cards(self, deck: str | None = None) -> list[Card]:
        query = "SELECT deck, id, text FROM cards"
        parameters = ()
        if deck is not None:
            query += " WHERE deck = ?"
            parameters = (deck,)
        try:
            with self._connect() as connection:
                rows = connection.execute(query + " ORDER BY deck, id", parameters).fetchall()
        except sqlite3.Error as error:
            raise StoreError(f"cannot read cards: {error}") from error
        return [Card(**dict(row)) for row in rows]

    def record_draw(self, draw: Draw) -> None:
        try:
            with self._connect() as connection, connection:
                connection.execute(
                    "INSERT INTO draws (id, time, deck, card_id, card_text, context, project)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        draw.id,
                        draw.time.isoformat(),
                        draw.deck,
                        draw.card_id,
                        draw.card_text,
                        draw.context,
                        draw.project,
                    ),
                )
        except sqlite3.Error as error:
            raise StoreError(f"cannot record draw {draw.id}: {error}") from error

    def record_outcome(self, outcome: Outcome) -> None:
        placeholders = ", ".join("?" for _ in OUTCOME_COLUMNS)
        try:
            with self._connect() as connection, connection:
                if not connection.execute(
                    "SELECT 1 FROM draws WHERE id = ?", (outcome.draw_id,)
                ).fetchone():
                    raise UnknownDrawError(f"no draw with id '{outcome.draw_id}'")
                connection.execute(
                    f"INSERT INTO outcomes ({', '.join(OUTCOME_COLUMNS)}) VALUES ({placeholders})",
                    (
                        outcome.draw_id,
                        outcome.time.isoformat(),
                        outcome.helped,
                        outcome.note,
                        outcome.code_diff,
                        outcome.commit_sha,
                        outcome.test_command,
                        outcome.tests_failing_before,
                        outcome.tests_failing_after,
                        outcome.test_output,
                    ),
                )
        except sqlite3.Error as error:
            raise StoreError(
                f"cannot record outcome for draw {outcome.draw_id}: {error}"
            ) from error

    def get_draw(self, draw_id: str) -> Draw | None:
        try:
            with self._connect() as connection:
                row = connection.execute(
                    "SELECT * FROM draws WHERE id = ?", (draw_id,)
                ).fetchone()
        except sqlite3.Error as error:
            raise StoreError(f"cannot read draw {draw_id}: {error}") from error
        if row is None:
            return None
        return Draw(
            id=row["id"],
            time=datetime.fromisoformat(row["time"]),
            deck=row["deck"],
            card_id=row["card_id"],
            card_text=row["card_text"],
            context=row["context"],
            project=row["project"],
        )

    def get_outcomes(self, draw_id: str) -> list[Outcome]:
        try:
            with self._connect() as connection:
                rows = connection.execute(
                    f"SELECT {', '.join(OUTCOME_COLUMNS)} FROM outcomes"
                    " WHERE draw_id = ? ORDER BY id",
                    (draw_id,),
                ).fetchall()
        except sqlite3.Error as error:
            raise StoreError(f"cannot read outcomes for draw {draw_id}: {error}") from error
        return [
            Outcome(
                **{
                    **dict(row),
                    "time": datetime.fromisoformat(row["time"]),
                    "helped": bool(row["helped"]),
                }
            )
            for row in rows
        ]

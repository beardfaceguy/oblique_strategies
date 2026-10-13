"""The storage interface for draws and their outcomes.

Code outside the concrete stores depends only on `DataStore`, `Draw`, `Outcome`
and `open_store`. Adding a backend means subclassing `DataStore` and teaching
`open_store` its URL scheme.
"""

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


class StoreError(Exception):
    pass


class UnknownDrawError(StoreError):
    pass


@dataclass(frozen=True)
class Draw:
    id: str
    time: datetime
    deck: str
    card_id: str
    # The card text at draw time, so later edits to a card don't rewrite history.
    card_text: str
    context: str = ""
    project: str = ""


@dataclass(frozen=True)
class Outcome:
    draw_id: str
    time: datetime
    helped: bool
    note: str = ""
    code_diff: str = ""
    commit_sha: str = ""
    test_command: str = ""
    tests_failing_before: int | None = None
    tests_failing_after: int | None = None
    test_output: str = ""


class DataStore(ABC):
    @abstractmethod
    def record_draw(self, draw: Draw) -> None: ...

    @abstractmethod
    def record_outcome(self, outcome: Outcome) -> None:
        """Raise `UnknownDrawError` if `outcome.draw_id` was never recorded."""

    @abstractmethod
    def get_draw(self, draw_id: str) -> Draw | None: ...

    @abstractmethod
    def get_outcomes(self, draw_id: str) -> list[Outcome]:
        """Return every outcome recorded for the draw, oldest first."""

    def close(self) -> None:
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exception_info):
        self.close()


DEFAULT_DATABASE_PATH = Path.home() / ".sidestep" / "sidestep.db"


def open_store(url: str | None = None) -> DataStore:
    """Open the store named by `url`, `SIDESTEP_DATABASE_URL`, or the default SQLite file.

    Supported: `sqlite:///absolute/path.db`, `sqlite:relative/path.db`.
    """
    url = url or os.environ.get("SIDESTEP_DATABASE_URL")
    if not url:
        from sidestep.sqlite_store import SQLiteStore

        return SQLiteStore(DEFAULT_DATABASE_PATH)

    scheme, separator, rest = url.partition(":")
    if separator and scheme == "sqlite":
        from sidestep.sqlite_store import SQLiteStore

        path = rest[2:] if rest.startswith("//") else rest
        if not path:
            raise StoreError(f"no database path in '{url}'")
        return SQLiteStore(Path(path))

    raise StoreError(f"unsupported database URL '{url}' (supported schemes: sqlite)")

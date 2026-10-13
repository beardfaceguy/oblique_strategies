import os
import tempfile
import unittest
from pathlib import Path

from sidestep.sqlite_store import SQLiteStore
from sidestep.store import StoreError, open_store
from tests.store_contract import DataStoreContract, make_draw


class SQLiteStoreTest(DataStoreContract, unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.path = Path(self.temporary_directory.name) / "nested" / "sidestep.db"
        super().setUp()

    def tearDown(self):
        super().tearDown()
        self.temporary_directory.cleanup()

    def make_store(self):
        return SQLiteStore(self.path)

    def test_data_survives_reopening(self):
        self.store.record_draw(make_draw())
        with SQLiteStore(self.path) as reopened:
            self.assertEqual(reopened.get_draw("draw-1"), make_draw())


class OpenStoreTest(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary_directory.name)

    def tearDown(self):
        os.environ.pop("SIDESTEP_DATABASE_URL", None)
        self.temporary_directory.cleanup()

    def test_sqlite_url(self):
        path = self.directory / "a.db"
        with open_store(f"sqlite://{path}") as store:
            self.assertIsInstance(store, SQLiteStore)
            self.assertEqual(store.path, path)

    def test_url_from_environment(self):
        path = self.directory / "b.db"
        os.environ["SIDESTEP_DATABASE_URL"] = f"sqlite://{path}"
        with open_store() as store:
            self.assertEqual(store.path, path)

    def test_unsupported_scheme(self):
        with self.assertRaisesRegex(StoreError, "unsupported"):
            open_store("postgresql://localhost/sidestep")


if __name__ == "__main__":
    unittest.main()

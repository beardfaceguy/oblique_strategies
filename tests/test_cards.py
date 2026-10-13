import tempfile
import unittest
from pathlib import Path

from sidestep.cards import DEFAULT_DECKS_DIR, Card, DeckError, load_decks


class LoadDecksTest(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary_directory.name)

    def tearDown(self):
        self.temporary_directory.cleanup()

    def write(self, name, content):
        (self.directory / name).write_text(content)

    def test_loads_cards_and_skips_empty_decks(self):
        self.write("alpha.toml", '[[card]]\nid = "one"\ntext = "  First.  "\n')
        self.write("empty.toml", "# nothing yet\n")
        self.assertEqual(
            load_decks(self.directory), {"alpha": [Card(deck="alpha", id="one", text="First.")]}
        )

    def test_duplicate_id_is_rejected(self):
        self.write("alpha.toml", '[[card]]\nid = "one"\ntext = "A"\n[[card]]\nid = "one"\ntext = "B"\n')
        with self.assertRaisesRegex(DeckError, "duplicate card id 'one'"):
            load_decks(self.directory)

    def test_missing_text_is_rejected(self):
        self.write("alpha.toml", '[[card]]\nid = "one"\n')
        with self.assertRaisesRegex(DeckError, "has no text"):
            load_decks(self.directory)

    def test_invalid_toml_is_rejected(self):
        self.write("alpha.toml", "[[card]\n")
        with self.assertRaisesRegex(DeckError, "cannot read deck"):
            load_decks(self.directory)

    def test_shipped_decks_load(self):
        self.assertEqual(len(load_decks(DEFAULT_DECKS_DIR)["debugging"]), 18)


if __name__ == "__main__":
    unittest.main()

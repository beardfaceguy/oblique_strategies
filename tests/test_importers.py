import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from sidestep import importers
from sidestep.import_cli import main
from sidestep.importers import (
    CardImporter,
    CardImportError,
    TomlImporter,
    importer_for,
    read_cards,
)
from sidestep.sqlite_store import SQLiteStore
from sidestep.store import Card

REPOSITORY = Path(__file__).resolve().parent.parent

ONE_CARD = '[[card]]\nid = "one"\ntext = "  First.  "\n'
TWO_CARDS = ONE_CARD + '[[card]]\nid = "two"\ntext = "Second."\n'


class TomlImporterTest(unittest.TestCase):
    def parse(self, content):
        return TomlImporter().parse(content, "deck")

    def test_single_card(self):
        self.assertEqual(self.parse(ONE_CARD), [Card(deck="deck", id="one", text="  First.  ")])

    def test_multiple_cards(self):
        self.assertEqual([card.id for card in self.parse(TWO_CARDS)], ["one", "two"])

    def test_invalid_toml(self):
        with self.assertRaisesRegex(CardImportError, "invalid TOML"):
            self.parse("[[card]\n")

    def test_no_cards(self):
        with self.assertRaisesRegex(CardImportError, "no \\[\\[card\\]\\] entries"):
            self.parse('title = "nothing"\n')

    def test_missing_text(self):
        with self.assertRaisesRegex(CardImportError, "card 1 needs a string `id` and `text`"):
            self.parse('[[card]]\nid = "one"\n')


class ReadCardsTest(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary_directory.name)

    def tearDown(self):
        self.temporary_directory.cleanup()

    def write(self, name, content):
        path = self.directory / name
        path.write_text(content)
        return path

    def test_deck_defaults_to_file_name_and_text_is_stripped(self):
        path = self.write("alpha.toml", ONE_CARD)
        self.assertEqual(read_cards(path), [Card(deck="alpha", id="one", text="First.")])

    def test_deck_can_be_given(self):
        path = self.write("alpha.toml", ONE_CARD)
        self.assertEqual(read_cards(path, deck="beta")[0].deck, "beta")

    def test_duplicate_id_is_rejected(self):
        path = self.write("alpha.toml", ONE_CARD + ONE_CARD)
        with self.assertRaisesRegex(CardImportError, "'one' appears twice in deck 'alpha'"):
            read_cards(path)

    def test_blank_text_is_rejected(self):
        path = self.write("alpha.toml", '[[card]]\nid = "one"\ntext = "  "\n')
        with self.assertRaisesRegex(CardImportError, "has no text"):
            read_cards(path)

    def test_unknown_extension_needs_a_format(self):
        path = self.write("alpha.txt", ONE_CARD)
        with self.assertRaisesRegex(CardImportError, "cannot tell the format"):
            read_cards(path)
        self.assertEqual(len(read_cards(path, format_name="toml")), 1)

    def test_new_format_only_needs_a_parser(self):
        class LinesImporter(CardImporter):
            format_name = "lines"
            extensions = (".lines",)

            def parse(self, content, default_deck):
                return [
                    Card(deck=default_deck, id=card_id, text=text)
                    for card_id, text in (line.split("|") for line in content.splitlines())
                ]

        original = list(importers.IMPORTERS)
        importers.IMPORTERS.append(LinesImporter())
        try:
            path = self.write("alpha.lines", "one| First. \n")
            self.assertIsInstance(importer_for(path), LinesImporter)
            self.assertEqual(read_cards(path), [Card(deck="alpha", id="one", text="First.")])
        finally:
            importers.IMPORTERS[:] = original

    def test_repository_card_files_are_valid(self):
        self.assertEqual(len(read_cards(REPOSITORY / "card_content.toml")), 10)
        self.assertEqual(len(read_cards(REPOSITORY / "decks" / "debugging.toml")), 18)


class ImportCliTest(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary_directory.name)
        self.database = self.directory / "sidestep.db"

    def tearDown(self):
        self.temporary_directory.cleanup()

    def write(self, name, content):
        path = self.directory / name
        path.write_text(content)
        return str(path)

    def run_cli(self, *arguments):
        output, errors = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            code = main([*arguments, "--database", f"sqlite://{self.database}"])
        return code, output.getvalue(), errors.getvalue()

    def cards(self):
        with SQLiteStore(self.database) as store:
            return store.get_cards()

    def test_imports_several_files(self):
        code, output, _ = self.run_cli(
            self.write("alpha.toml", TWO_CARDS), self.write("beta.toml", ONE_CARD)
        )
        self.assertEqual(code, 0)
        self.assertIn("added 3, updated 0, unchanged 0", output)
        self.assertEqual(
            [(card.deck, card.id) for card in self.cards()],
            [("alpha", "one"), ("alpha", "two"), ("beta", "one")],
        )

    def test_reimport_updates_changed_text(self):
        path = self.write("alpha.toml", TWO_CARDS)
        self.run_cli(path)
        self.write("alpha.toml", TWO_CARDS.replace("Second.", "Second, reworded."))
        code, output, _ = self.run_cli(path)
        self.assertEqual(code, 0)
        self.assertIn("added 0, updated 1, unchanged 1", output)

    def test_one_bad_file_imports_nothing(self):
        code, _, errors = self.run_cli(
            self.write("alpha.toml", TWO_CARDS), self.write("broken.toml", "[[card]\n")
        )
        self.assertEqual(code, 1)
        self.assertIn("broken.toml: invalid TOML", errors)
        self.assertEqual(self.cards(), [])

    def test_same_card_in_two_files_with_one_deck_is_rejected(self):
        code, _, errors = self.run_cli(
            self.write("alpha.toml", ONE_CARD), self.write("beta.toml", ONE_CARD), "--deck", "shared"
        )
        self.assertEqual(code, 1)
        self.assertIn("'one' appears twice in deck 'shared'", errors)

    def test_missing_file(self):
        code, _, errors = self.run_cli(str(self.directory / "missing.toml"))
        self.assertEqual(code, 1)
        self.assertIn("cannot read", errors)


if __name__ == "__main__":
    unittest.main()

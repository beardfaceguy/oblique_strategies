import asyncio
import sys
import tempfile
import unittest
from pathlib import Path

from mcp import Client, StdioServerParameters

from sidestep.server import MAX_STORED_TEXT, create_server
from sidestep.sqlite_store import SQLiteStore
from sidestep.store import DataStore, Draw, Outcome, UnknownDrawError


class MemoryStore(DataStore):
    """Proves the server needs nothing beyond the DataStore interface."""

    def __init__(self):
        self.draws: dict[str, Draw] = {}
        self.outcomes: list[Outcome] = []

    def record_draw(self, draw):
        self.draws[draw.id] = draw

    def record_outcome(self, outcome):
        if outcome.draw_id not in self.draws:
            raise UnknownDrawError(f"no draw with id '{outcome.draw_id}'")
        self.outcomes.append(outcome)

    def get_draw(self, draw_id):
        return self.draws.get(draw_id)

    def get_outcomes(self, draw_id):
        return [outcome for outcome in self.outcomes if outcome.draw_id == draw_id]


class ServerTest(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.decks = Path(self.temporary_directory.name) / "decks"
        self.decks.mkdir()
        (self.decks / "alpha.toml").write_text(
            '[[card]]\nid = "a1"\ntext = "First alpha."\n'
            '[[card]]\nid = "a2"\ntext = "Second alpha."\n'
        )
        (self.decks / "beta.toml").write_text('[[card]]\nid = "b1"\ntext = "Only beta."\n')
        self.store = MemoryStore()

    def tearDown(self):
        self.temporary_directory.cleanup()

    def call(self, tool, arguments):
        async def run():
            async with Client(create_server(self.store, self.decks)) as client:
                return await client.call_tool(tool, arguments)

        result = asyncio.run(run())
        return result.is_error, result.content[0].text

    def draw_id(self):
        [draw_id] = self.store.draws
        return draw_id

    def test_draw_from_named_deck_is_recorded(self):
        is_error, text = self.call(
            "draw_card", {"deck": "beta", "context": "stuck", "project": "demo"}
        )
        self.assertFalse(is_error)
        self.assertIn("Strategy: Only beta.", text)
        draw = self.store.get_draw(self.draw_id())
        self.assertEqual(
            (draw.deck, draw.card_id, draw.card_text, draw.context, draw.project),
            ("beta", "b1", "Only beta.", "stuck", "demo"),
        )
        self.assertIn(draw.id, text)

    def test_draw_from_all_decks_reaches_every_card(self):
        for _ in range(60):
            self.call("draw_card", {})
        self.assertEqual(
            {draw.card_id for draw in self.store.draws.values()}, {"a1", "a2", "b1"}
        )

    def test_unknown_deck_is_an_error(self):
        is_error, text = self.call("draw_card", {"deck": "gamma"})
        self.assertTrue(is_error)
        self.assertIn("available: alpha, beta", text)

    def test_record_outcome(self):
        self.call("draw_card", {"deck": "beta"})
        draw_id = self.draw_id()
        is_error, _ = self.call(
            "record_outcome",
            {
                "draw_id": draw_id,
                "helped": True,
                "code_diff": "+fix",
                "tests_failing_before": 2,
                "tests_failing_after": 0,
            },
        )
        self.assertFalse(is_error)
        [outcome] = self.store.get_outcomes(draw_id)
        self.assertEqual(
            (outcome.helped, outcome.code_diff, outcome.tests_failing_before, outcome.tests_failing_after),
            (True, "+fix", 2, 0),
        )

    def test_long_text_is_truncated(self):
        self.call("draw_card", {"deck": "beta"})
        self.call(
            "record_outcome",
            {"draw_id": self.draw_id(), "helped": False, "test_output": "x" * (MAX_STORED_TEXT + 5)},
        )
        [outcome] = self.store.outcomes
        self.assertTrue(outcome.test_output.endswith("[truncated: 5 more characters]"))

    def test_outcome_for_unknown_draw_is_an_error(self):
        is_error, text = self.call("record_outcome", {"draw_id": "missing", "helped": True})
        self.assertTrue(is_error)
        self.assertIn("no draw with id 'missing'", text)

    def test_list_decks(self):
        self.assertEqual(self.call("list_decks", {})[1], "alpha: 2 cards\nbeta: 1 cards")

    def test_serves_over_stdio_with_sqlite(self):
        database = Path(self.temporary_directory.name) / "sidestep.db"

        async def run():
            parameters = StdioServerParameters(
                command=sys.executable,
                args=["-m", "sidestep.server"],
                env={
                    "SIDESTEP_DATABASE_URL": f"sqlite://{database}",
                    "SIDESTEP_DECKS": str(self.decks),
                },
                cwd=str(Path(__file__).resolve().parent.parent),
            )
            async with Client(parameters) as client:
                tools = await client.list_tools()
                result = await client.call_tool("draw_card", {"deck": "beta"})
                return {tool.name for tool in tools.tools}, result.content[0].text

        tool_names, text = asyncio.run(run())
        self.assertEqual(tool_names, {"draw_card", "record_outcome", "list_decks"})
        self.assertIn("Strategy: Only beta.", text)
        draw_id = text.split("draw id: ")[1].split(")")[0]
        with SQLiteStore(database) as store:
            self.assertEqual(store.get_draw(draw_id).card_id, "b1")


if __name__ == "__main__":
    unittest.main()

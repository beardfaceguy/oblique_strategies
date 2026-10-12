import asyncio
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

from mcp import Client, StdioServerParameters

REPOSITORY = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPOSITORY))

import sidestep  # noqa: E402


class SidestepTest(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        directory = Path(self.temporary_directory.name)
        self.log = directory / "draws.jsonl"
        self.decks = directory / "decks"
        self.decks.mkdir()
        (self.decks / "alpha.md").write_text("# Alpha\n\n- First alpha.\n- Second alpha.\n")
        (self.decks / "beta.md").write_text("- Only beta.\n")
        (self.decks / "empty.md").write_text("# Nothing here yet\n")
        os.environ["SIDESTEP_LOG"] = str(self.log)
        os.environ["SIDESTEP_DECKS"] = str(self.decks)

    def tearDown(self):
        del os.environ["SIDESTEP_LOG"]
        del os.environ["SIDESTEP_DECKS"]
        self.temporary_directory.cleanup()

    def read_log(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()]

    def call(self, tool, arguments):
        async def run():
            async with Client(sidestep.server) as client:
                return await client.call_tool(tool, arguments)

        result = asyncio.run(run())
        return result.is_error, result.content[0].text

    def test_load_decks_skips_headings_and_empty_decks(self):
        self.assertEqual(
            sidestep.load_decks(),
            {"alpha": ["First alpha.", "Second alpha."], "beta": ["Only beta."]},
        )

    def test_draw_from_named_deck(self):
        is_error, text = self.call("draw_card", {"deck": "beta", "context": "stuck"})
        self.assertFalse(is_error)
        self.assertIn("Strategy: Only beta.", text)
        [entry] = self.read_log()
        self.assertEqual(entry["deck"], "beta")
        self.assertEqual(entry["context"], "stuck")
        self.assertIn(entry["id"], text)

    def test_draw_from_all_decks_reaches_every_card(self):
        drawn = set()
        for _ in range(60):
            drawn.add(self.call("draw_card", {})[1].splitlines()[0])
        self.assertEqual(
            drawn,
            {"Strategy: First alpha.", "Strategy: Second alpha.", "Strategy: Only beta."},
        )

    def test_unknown_deck_is_an_error(self):
        is_error, text = self.call("draw_card", {"deck": "gamma"})
        self.assertTrue(is_error)
        self.assertIn("available: alpha, beta", text)

    def test_record_outcome_is_logged(self):
        self.call("record_outcome", {"draw_id": "abc123", "helped": True, "note": "found it"})
        [entry] = self.read_log()
        self.assertEqual(entry["type"], "outcome")
        self.assertEqual(entry["id"], "abc123")
        self.assertTrue(entry["helped"])

    def test_list_decks(self):
        self.assertEqual(self.call("list_decks", {})[1], "alpha: 2 cards\nbeta: 1 cards")

    def test_serves_over_stdio(self):
        async def run():
            parameters = StdioServerParameters(
                command=sys.executable,
                args=[str(REPOSITORY / "sidestep.py")],
                env={"SIDESTEP_LOG": str(self.log), "SIDESTEP_DECKS": str(self.decks)},
            )
            async with Client(parameters) as client:
                tools = await client.list_tools()
                result = await client.call_tool("draw_card", {"deck": "beta"})
                return {tool.name for tool in tools.tools}, result.content[0].text

        tool_names, text = asyncio.run(run())
        self.assertEqual(tool_names, {"draw_card", "record_outcome", "list_decks"})
        self.assertIn("Strategy: Only beta.", text)


if __name__ == "__main__":
    unittest.main()

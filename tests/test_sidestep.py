import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "skills" / "sidestep"))

import sidestep  # noqa: E402


class SidestepTest(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.log = Path(self.temporary_directory.name) / "draws.jsonl"
        os.environ["SIDESTEP_LOG"] = str(self.log)

    def tearDown(self):
        del os.environ["SIDESTEP_LOG"]
        self.temporary_directory.cleanup()

    def read_log(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()]

    def test_debugging_deck_loads_all_cards(self):
        cards = sidestep.load_deck("debugging")
        self.assertEqual(len(cards), 18)
        self.assertTrue(all(card and not card.startswith("-") for card in cards))

    def test_unknown_deck_fails(self):
        self.assertEqual(sidestep.main(["draw", "no-such-deck"]), 1)

    def test_draw_and_outcome_are_logged(self):
        draw_id, card = sidestep.draw("debugging", "flaky test")
        self.assertIn(card, sidestep.load_deck("debugging"))
        sidestep.record_outcome(draw_id, True, "found it")

        draw_entry, outcome_entry = self.read_log()
        self.assertEqual(draw_entry["type"], "draw")
        self.assertEqual(draw_entry["card"], card)
        self.assertEqual(draw_entry["context"], "flaky test")
        self.assertEqual(outcome_entry["id"], draw_id)
        self.assertTrue(outcome_entry["helped"])


if __name__ == "__main__":
    unittest.main()

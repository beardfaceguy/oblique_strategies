from datetime import datetime, timezone

from sidestep.store import DataStore, Draw, Outcome, UnknownDrawError

TIME = datetime(2026, 10, 13, 12, 0, tzinfo=timezone.utc)


def make_draw(draw_id="draw-1"):
    return Draw(
        id=draw_id,
        time=TIME,
        deck="debugging",
        card_id="error-is-true",
        card_text="Pretend the error message is literally and precisely true.",
        context="login test fails",
        project="example",
    )


class DataStoreContract:
    """Behaviour every DataStore must have. Mix into a TestCase that defines `make_store`."""

    def make_store(self) -> DataStore:
        raise NotImplementedError

    def setUp(self):
        super().setUp()
        self.store = self.make_store()

    def tearDown(self):
        self.store.close()
        super().tearDown()

    def test_draw_round_trip(self):
        draw = make_draw()
        self.store.record_draw(draw)
        self.assertEqual(self.store.get_draw(draw.id), draw)

    def test_unknown_draw_is_none(self):
        self.assertIsNone(self.store.get_draw("missing"))

    def test_outcome_round_trip(self):
        self.store.record_draw(make_draw())
        outcome = Outcome(
            draw_id="draw-1",
            time=TIME,
            helped=True,
            note="path was wrong",
            code_diff="--- a/x\n+++ b/x\n",
            commit_sha="abc123",
            test_command="pytest",
            tests_failing_before=3,
            tests_failing_after=0,
            test_output="3 passed",
        )
        self.store.record_outcome(outcome)
        self.assertEqual(self.store.get_outcomes("draw-1"), [outcome])

    def test_outcome_optional_fields(self):
        self.store.record_draw(make_draw())
        outcome = Outcome(draw_id="draw-1", time=TIME, helped=False)
        self.store.record_outcome(outcome)
        self.assertEqual(self.store.get_outcomes("draw-1"), [outcome])

    def test_outcomes_are_kept_in_order(self):
        self.store.record_draw(make_draw())
        first = Outcome(draw_id="draw-1", time=TIME, helped=False, note="first")
        second = Outcome(draw_id="draw-1", time=TIME, helped=True, note="second")
        self.store.record_outcome(first)
        self.store.record_outcome(second)
        self.assertEqual(self.store.get_outcomes("draw-1"), [first, second])

    def test_outcome_for_unknown_draw_is_rejected(self):
        with self.assertRaises(UnknownDrawError):
            self.store.record_outcome(Outcome(draw_id="missing", time=TIME, helped=True))
        self.assertEqual(self.store.get_outcomes("missing"), [])

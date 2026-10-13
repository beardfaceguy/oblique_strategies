import secrets
import uuid
from datetime import datetime, timezone

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from sidestep.store import DataStore, Draw, Outcome, StoreError, open_store

# Diffs and test output can be huge; keep enough to review without bloating the store.
MAX_STORED_TEXT = 100_000

INSTRUCTIONS = """\
Call draw_card when you are stuck: the same test or check has failed 3 times, \
you are about to revert your own change, or 3 attempts in a row made no progress.

Each card is a strategy. Trust it: apply it genuinely to your problem for one full \
attempt before judging it, even if its relevance is unclear. Do not reinterpret it \
into what you were already going to do.

Afterwards, call record_outcome with the draw id. Include the diff of the code the \
card led you to write, the commit SHA if you committed, the test command you ran, \
and how many tests failed before and after: that is what lets the decks improve."""


def truncate(text: str) -> str:
    if len(text) <= MAX_STORED_TEXT:
        return text
    return text[:MAX_STORED_TEXT] + f"\n[truncated: {len(text) - MAX_STORED_TEXT} more characters]"


def now() -> datetime:
    return datetime.now(timezone.utc)


def create_server(store: DataStore) -> MCPServer:
    server = MCPServer(name="sidestep", instructions=INSTRUCTIONS)

    def decks():
        try:
            cards = store.get_cards()
        except StoreError as error:
            raise ToolError(str(error)) from error
        if not cards:
            raise ToolError("there are no cards yet; import some with sidestep-import")
        by_deck = {}
        for card in cards:
            by_deck.setdefault(card.deck, []).append(card)
        return by_deck

    @server.tool()
    def draw_card(deck: str | None = None, context: str = "", project: str = "") -> str:
        """Draw a random strategy card to apply to the problem you are stuck on.

        Args:
            deck: Draw only from this deck. Omit to draw from every deck.
            context: What you are stuck on, in a sentence or two.
            project: The repository or project you are working in.
        """
        loaded = decks()
        if deck is None:
            candidates = [card for cards in loaded.values() for card in cards]
        elif deck in loaded:
            candidates = loaded[deck]
        else:
            raise ToolError(f"unknown deck '{deck}' (available: {', '.join(loaded)})")

        # The draw must come from a real random source rather than the model,
        # otherwise the agent picks the card that matches what it already thinks.
        card = secrets.choice(candidates)
        draw = Draw(
            id=uuid.uuid4().hex[:12],
            time=now(),
            deck=card.deck,
            card_id=card.id,
            card_text=card.text,
            context=context,
            project=project,
        )
        try:
            store.record_draw(draw)
        except StoreError as error:
            raise ToolError(str(error)) from error

        return (
            f"Strategy: {card.text}\n\n"
            f"(deck: {card.deck}, card: {card.id}, draw id: {draw.id})\n\n"
            "Apply this strategy to your problem for one full attempt before judging it, "
            "then call record_outcome with this draw id."
        )

    @server.tool()
    def record_outcome(
        draw_id: str,
        helped: bool,
        note: str = "",
        code_diff: str = "",
        commit_sha: str = "",
        test_command: str = "",
        tests_failing_before: int | None = None,
        tests_failing_after: int | None = None,
        test_output: str = "",
    ) -> str:
        """Record what happened after applying a drawn card for one attempt.

        Args:
            draw_id: The draw id returned by draw_card.
            helped: Whether applying the strategy moved the problem forward.
            note: What changed, or why it did not help.
            code_diff: Unified diff of the code the card led you to write.
            commit_sha: Commit containing that code, if you committed it.
            test_command: The command you ran to test it.
            tests_failing_before: Failing tests before applying the card.
            tests_failing_after: Failing tests after applying the card.
            test_output: Relevant test output after applying the card.
        """
        outcome = Outcome(
            draw_id=draw_id,
            time=now(),
            helped=helped,
            note=note,
            code_diff=truncate(code_diff),
            commit_sha=commit_sha,
            test_command=test_command,
            tests_failing_before=tests_failing_before,
            tests_failing_after=tests_failing_after,
            test_output=truncate(test_output),
        )
        try:
            store.record_outcome(outcome)
        except StoreError as error:
            raise ToolError(str(error)) from error
        return f"Recorded outcome for draw {draw_id}."

    @server.tool()
    def list_decks() -> str:
        """List the available decks and how many cards each holds."""
        return "\n".join(f"{name}: {len(cards)} cards" for name, cards in decks().items())

    return server


def main():
    with open_store() as store:
        create_server(store).run()


if __name__ == "__main__":
    main()

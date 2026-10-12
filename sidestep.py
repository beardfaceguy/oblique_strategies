# /// script
# requires-python = ">=3.10"
# dependencies = ["mcp>=2.2,<3"]
# ///
"""MCP server that serves a random strategy card to an agent that is stuck."""

import json
import os
import secrets
import uuid
from datetime import datetime, timezone
from pathlib import Path

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError


def decks_dir():
    configured = os.environ.get("SIDESTEP_DECKS")
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parent / "decks"


def log_path():
    configured = os.environ.get("SIDESTEP_LOG")
    if configured:
        return Path(configured)
    return Path.home() / ".sidestep" / "draws.jsonl"


def load_decks():
    """Return {deck name: [strategy, ...]}. Each `- ` line in a deck file is one card."""
    decks = {}
    for path in sorted(decks_dir().glob("*.md")):
        cards = [
            line[2:].strip()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.startswith("- ") and line[2:].strip()
        ]
        if cards:
            decks[path.stem] = cards
    return decks


def append_log(entry):
    path = log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as log_file:
        log_file.write(json.dumps(entry) + "\n")


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


INSTRUCTIONS = """\
Call draw_card when you are stuck: the same test or check has failed 3 times, \
you are about to revert your own change, or 3 attempts in a row made no progress.

Each card is a strategy. Trust it: apply it genuinely to your problem for one full \
attempt before judging it, even if its relevance is unclear. Do not reinterpret it \
into what you were already going to do. Afterwards, call record_outcome with the \
draw id so the decks can improve."""

server = MCPServer(name="sidestep", instructions=INSTRUCTIONS)


@server.tool()
def draw_card(deck: str | None = None, context: str = "") -> str:
    """Draw a random strategy card to apply to the problem you are stuck on.

    Args:
        deck: Draw only from this deck. Omit to draw from every deck.
        context: One line describing what you are stuck on. Logged with the draw.
    """
    decks = load_decks()
    if not decks:
        raise ToolError(f"no decks with cards found in {decks_dir()}")
    if deck is None:
        candidates = [(name, card) for name, cards in decks.items() for card in cards]
    elif deck in decks:
        candidates = [(deck, card) for card in decks[deck]]
    else:
        raise ToolError(f"unknown deck '{deck}' (available: {', '.join(decks)})")

    # The draw must come from a real random source rather than the model,
    # otherwise the agent picks the card that matches what it already thinks.
    drawn_deck, card = secrets.choice(candidates)
    draw_id = uuid.uuid4().hex[:8]
    append_log(
        {
            "type": "draw",
            "id": draw_id,
            "time": now(),
            "deck": drawn_deck,
            "card": card,
            "context": context,
        }
    )
    return (
        f"Strategy: {card}\n\n"
        f"(deck: {drawn_deck}, draw id: {draw_id})\n\n"
        "Apply this strategy to your problem for one full attempt before judging it, "
        "then call record_outcome with this draw id."
    )


@server.tool()
def record_outcome(draw_id: str, helped: bool, note: str = "") -> str:
    """Record whether a drawn card helped, after applying it for one attempt.

    Args:
        draw_id: The draw id returned by draw_card.
        helped: Whether applying the strategy moved the problem forward.
        note: What changed, or why it did not help.
    """
    append_log(
        {
            "type": "outcome",
            "id": draw_id,
            "time": now(),
            "helped": helped,
            "note": note,
        }
    )
    return f"Recorded outcome for draw {draw_id}."


@server.tool()
def list_decks() -> str:
    """List the available decks and how many cards each holds."""
    decks = load_decks()
    return "\n".join(f"{name}: {len(cards)} cards" for name, cards in decks.items())


if __name__ == "__main__":
    server.run()

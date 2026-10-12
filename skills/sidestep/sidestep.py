#!/usr/bin/env python3
"""Draw a random reframing card from a deck, and log draws and outcomes."""

import argparse
import json
import os
import secrets
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

DECKS_DIR = Path(__file__).resolve().parent / "decks"
DEFAULT_DECK = "debugging"


def log_path():
    configured = os.environ.get("SIDESTEP_LOG")
    if configured:
        return Path(configured)
    return Path.home() / ".sidestep" / "draws.jsonl"


def available_decks():
    return sorted(path.stem for path in DECKS_DIR.glob("*.md"))


def load_deck(name):
    path = DECKS_DIR / f"{name}.md"
    if not path.is_file():
        raise ValueError(
            f"unknown deck '{name}' (available: {', '.join(available_decks())})"
        )
    cards = [
        line[2:].strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.startswith("- ") and line[2:].strip()
    ]
    if not cards:
        raise ValueError(f"deck '{name}' has no cards")
    return cards


def append_log(entry):
    path = log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as log_file:
        log_file.write(json.dumps(entry) + "\n")


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def draw(deck, context):
    # The draw must come from a real random source, not from the model,
    # otherwise the agent picks the card that matches what it already thinks.
    card = secrets.choice(load_deck(deck))
    draw_id = uuid.uuid4().hex[:8]
    append_log(
        {
            "type": "draw",
            "id": draw_id,
            "time": now(),
            "deck": deck,
            "card": card,
            "context": context,
        }
    )
    return draw_id, card


def record_outcome(draw_id, helped, note):
    append_log(
        {
            "type": "outcome",
            "id": draw_id,
            "time": now(),
            "helped": helped,
            "note": note,
        }
    )


def main(argv=None):
    parser = argparse.ArgumentParser(prog="sidestep", description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)

    draw_parser = subcommands.add_parser("draw", help="draw a random card")
    draw_parser.add_argument("deck", nargs="?", default=DEFAULT_DECK)
    draw_parser.add_argument(
        "--context", default="", help="one line on what you were stuck on"
    )

    outcome_parser = subcommands.add_parser(
        "outcome", help="record whether a drawn card helped"
    )
    outcome_parser.add_argument("id", help="the draw id printed by 'draw'")
    outcome_parser.add_argument("result", choices=["helped", "did-not-help"])
    outcome_parser.add_argument("--note", default="")

    subcommands.add_parser("decks", help="list available decks")

    args = parser.parse_args(argv)

    try:
        if args.command == "draw":
            draw_id, card = draw(args.deck, args.context)
            print(f"[{args.deck} #{draw_id}] {card}")
        elif args.command == "outcome":
            record_outcome(args.id, args.result == "helped", args.note)
            print(f"recorded outcome for #{args.id}")
        elif args.command == "decks":
            print("\n".join(available_decks()))
    except (ValueError, OSError) as error:
        print(f"sidestep: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

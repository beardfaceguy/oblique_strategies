import tomllib
from dataclasses import dataclass
from pathlib import Path

DEFAULT_DECKS_DIR = Path(__file__).resolve().parent / "decks"


class DeckError(Exception):
    pass


@dataclass(frozen=True)
class Card:
    deck: str
    id: str
    text: str


def load_decks(decks_dir: Path) -> dict[str, list[Card]]:
    """Load every `*.toml` deck in `decks_dir`, keyed by deck name (the file stem)."""
    decks = {}
    for path in sorted(decks_dir.glob("*.toml")):
        deck = path.stem
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError) as error:
            raise DeckError(f"cannot read deck {path}: {error}") from error

        cards = []
        seen_ids = set()
        for index, entry in enumerate(data.get("card", []), start=1):
            card_id = entry.get("id")
            text = entry.get("text")
            if not isinstance(card_id, str) or not card_id.strip():
                raise DeckError(f"{path}: card {index} has no id")
            if not isinstance(text, str) or not text.strip():
                raise DeckError(f"{path}: card '{card_id}' has no text")
            if card_id in seen_ids:
                raise DeckError(f"{path}: duplicate card id '{card_id}'")
            seen_ids.add(card_id)
            cards.append(Card(deck=deck, id=card_id, text=text.strip()))

        if cards:
            decks[deck] = cards
    return decks

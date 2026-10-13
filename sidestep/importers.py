"""Read card files into `Card`s, independent of file format.

Adding a format means subclassing `CardImporter` and adding an instance to
`IMPORTERS`. Validation, format detection and saving are shared.
"""

import tomllib
from abc import ABC, abstractmethod
from pathlib import Path

from sidestep.store import Card


class CardImportError(Exception):
    pass


class CardImporter(ABC):
    format_name: str
    extensions: tuple[str, ...]

    @abstractmethod
    def parse(self, content: str, default_deck: str) -> list[Card]:
        """Turn file content into cards, raising `CardImportError` if it is malformed.

        Cards whose format has no way to name a deck go in `default_deck`.
        Validation of ids and text happens afterwards, in `read_cards`.
        """


class TomlImporter(CardImporter):
    """Cards as a `[[card]]` array of tables, each with `id` and `text`."""

    format_name = "toml"
    extensions = (".toml",)

    def parse(self, content: str, default_deck: str) -> list[Card]:
        try:
            data = tomllib.loads(content)
        except tomllib.TOMLDecodeError as error:
            raise CardImportError(f"invalid TOML: {error}") from error

        entries = data.get("card")
        if not isinstance(entries, list):
            raise CardImportError("no [[card]] entries found")

        cards = []
        for index, entry in enumerate(entries, start=1):
            if not isinstance(entry, dict):
                raise CardImportError(f"card {index} is not a table")
            card_id = entry.get("id")
            text = entry.get("text")
            if not isinstance(card_id, str) or not isinstance(text, str):
                raise CardImportError(f"card {index} needs a string `id` and `text`")
            cards.append(Card(deck=default_deck, id=card_id, text=text))
        return cards


IMPORTERS: list[CardImporter] = [TomlImporter()]


def format_names() -> list[str]:
    return [importer.format_name for importer in IMPORTERS]


def importer_for(path: Path, format_name: str | None = None) -> CardImporter:
    for importer in IMPORTERS:
        if format_name is not None:
            if importer.format_name == format_name:
                return importer
        elif path.suffix.lower() in importer.extensions:
            return importer
    if format_name is not None:
        raise CardImportError(
            f"unknown format '{format_name}' (supported: {', '.join(format_names())})"
        )
    raise CardImportError(
        f"cannot tell the format of {path} from its extension; pass a format "
        f"(supported: {', '.join(format_names())})"
    )


def validate_cards(cards: list[Card]) -> list[Card]:
    """Strip whitespace and reject empty fields or a (deck, id) that appears twice."""
    validated = []
    seen = set()
    for card in cards:
        deck, card_id, text = card.deck.strip(), card.id.strip(), card.text.strip()
        if not deck:
            raise CardImportError(f"card '{card_id}' has no deck")
        if not card_id:
            raise CardImportError(f"a card in deck '{deck}' has no id")
        if not text:
            raise CardImportError(f"card '{card_id}' in deck '{deck}' has no text")
        if (deck, card_id) in seen:
            raise CardImportError(f"card '{card_id}' appears twice in deck '{deck}'")
        seen.add((deck, card_id))
        validated.append(Card(deck=deck, id=card_id, text=text))
    return validated


def read_cards(path: Path, deck: str | None = None, format_name: str | None = None) -> list[Card]:
    """Read every card in `path`. Cards go in `deck`, or a deck named after the file."""
    importer = importer_for(path, format_name)
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise CardImportError(f"cannot read {path}: {error}") from error
    try:
        return validate_cards(importer.parse(content, deck or path.stem))
    except CardImportError as error:
        raise CardImportError(f"{path}: {error}") from error

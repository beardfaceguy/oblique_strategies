import argparse
import sys
from pathlib import Path

from sidestep.importers import CardImportError, format_names, read_cards, validate_cards
from sidestep.store import StoreError, open_store


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="sidestep-import",
        description="Import card files into the sidestep data store. "
        "New cards are added and existing ones (same deck and id) get their text updated.",
    )
    parser.add_argument("files", nargs="+", type=Path, metavar="FILE")
    parser.add_argument(
        "--deck", help="deck to import the cards into (default: each file's name without extension)"
    )
    parser.add_argument(
        "--format",
        choices=format_names(),
        help="file format (default: detected from each file's extension)",
    )
    parser.add_argument(
        "--database",
        help="database URL (default: SIDESTEP_DATABASE_URL, then ~/.sidestep/sidestep.db)",
    )
    args = parser.parse_args(argv)

    try:
        # Read and validate every file before saving any, so a bad file imports nothing.
        cards = []
        for path in args.files:
            file_cards = read_cards(path, deck=args.deck, format_name=args.format)
            print(f"{path}: {len(file_cards)} cards")
            cards.extend(file_cards)
        cards = validate_cards(cards)

        with open_store(args.database) as store:
            result = store.save_cards(cards)
    except (CardImportError, StoreError) as error:
        print(f"sidestep-import: {error}", file=sys.stderr)
        return 1

    print(f"added {result.added}, updated {result.updated}, unchanged {result.unchanged}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

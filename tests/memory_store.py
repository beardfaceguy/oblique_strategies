from sidestep.store import Card, DataStore, Draw, Outcome, SaveCardsResult, UnknownDrawError


class MemoryStore(DataStore):
    """A DataStore with no backend, used to show the server needs nothing beyond the interface."""

    def __init__(self):
        self.cards: dict[tuple[str, str], Card] = {}
        self.draws: dict[str, Draw] = {}
        self.outcomes: list[Outcome] = []

    def save_cards(self, cards):
        added = updated = unchanged = 0
        for card in cards:
            existing = self.cards.get((card.deck, card.id))
            if existing is None:
                added += 1
            elif existing.text != card.text:
                updated += 1
            else:
                unchanged += 1
            self.cards[(card.deck, card.id)] = card
        return SaveCardsResult(added=added, updated=updated, unchanged=unchanged)

    def get_cards(self, deck=None):
        return [
            card
            for _, card in sorted(self.cards.items())
            if deck is None or card.deck == deck
        ]

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

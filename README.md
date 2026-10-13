# sidestep

An MCP server that serves a randomly drawn strategy card to a coding agent that is stuck, inspired by Brian Eno and Peter Schmidt's *Oblique Strategies*.

Agents get stuck in loops: retrying near-identical fixes, drifting from the real problem. A random strategy breaks the loop. Every draw, the code it led to, and the test results are recorded, so patterns in which cards help with which problems can be studied later.

## Principles

- **The draw comes from code, not the model.** A model asked to pick a card picks the one that fits what it already thinks.
- **Trust the card.** The agent applies the strategy genuinely for one attempt before judging it.
- **Record everything** (card, context, resulting code, test results) so the decks can evolve.
- **Original text only.** The official Oblique Strategies deck is copyrighted; every card here is original.

## Tools

| Tool | What it does |
| --- | --- |
| `draw_card(deck?, context?, project?)` | Returns one random strategy, from every deck or only the named one, plus a draw id. |
| `record_outcome(draw_id, helped, ...)` | Records what happened: a note, the code diff and commit SHA, the test command, failing test counts before and after, and test output. |
| `list_decks()` | Lists decks and their card counts. |

The server's instructions tell the agent when to draw (same failure 3 times, about to revert its own change, 3 attempts without progress), to trust the card, and what to report afterwards.

## Install

Requires [uv](https://docs.astral.sh/uv/).

Claude Code:

```sh
claude mcp add sidestep -- uv run --quiet --project /absolute/path/to/oblique_strategies sidestep
```

Any other MCP client (Cursor, etc.):

```json
{
  "mcpServers": {
    "sidestep": {
      "command": "uv",
      "args": ["run", "--quiet", "--project", "/absolute/path/to/oblique_strategies", "sidestep"]
    }
  }
}
```

`uv run --project` always runs the current code in the checkout, so a `git pull` takes effect on the next start. (`uvx --from <path>` caches the first build and keeps running it.)

Then import some cards (see below); the server has nothing to draw until you do, and warns at startup when the database has no cards. The warning goes to stderr, which MCP clients usually keep in their server logs rather than showing in the chat.

## Configuration

| Environment variable | Default |
| --- | --- |
| `SIDESTEP_DATABASE_URL` | `~/.sidestep/sidestep.db` (SQLite). Accepts `sqlite:///absolute/path.db` or `sqlite:relative/path.db`. |

The database holds diffs from whatever projects your agents work on; keep it private.

## Cards and importing

Cards live in the data store. Put them there with `sidestep-import`:

```sh
uv run --project /absolute/path/to/oblique_strategies sidestep-import decks/debugging.toml
```

- A file can hold one card or many; every card in it is imported.
- Cards go in a deck named after the file (`debugging` above), or the one given with `--deck`.
- A card is identified by its deck and `id`. Importing a card that already exists updates its text; draws keep the text the card had when it was drawn.
- Every file is checked before anything is saved, so one bad file imports nothing.
- `--database URL` imports into a different store than `SIDESTEP_DATABASE_URL`.

TOML card files are an array of `[[card]]` tables, each with a stable `id` and the `text` of the strategy:

```toml
[[card]]
id = "error-is-true"
text = "Pretend the error message is literally and precisely true."
```

`decks/debugging.toml` is a placeholder starter deck for testing. `card_content.toml` holds the first ten cards of the real deck, not yet imported.

### Adding a file format

Everything except parsing is shared, in `sidestep/importers.py`. To support another format:

1. Subclass `CardImporter`, set `format_name` and `extensions`, and implement `parse(content, default_deck)` to return `Card`s.
2. Add an instance to `IMPORTERS`.

Format detection, the `--format` option, validation (blank fields, duplicate ids) and saving pick it up automatically.

## Storage backends

Everything outside the store modules talks only to the `DataStore` interface in `sidestep/store.py`. To add a backend (for example Postgres):

1. Write `sidestep/postgres_store.py` with a `PostgresStore(DataStore)` implementing `save_cards`, `get_cards`, `record_draw`, `record_outcome`, `get_draw` and `get_outcomes`.
2. Teach `open_store` in `sidestep/store.py` its URL scheme (`postgresql://...`).
3. Add a test that mixes `tests.store_contract.DataStoreContract` into a `unittest.TestCase`, as `tests/test_sqlite_store.py` does. The contract tests every store must pass come for free.

## Tests

```sh
uv run python -m unittest discover -t . -s tests
```

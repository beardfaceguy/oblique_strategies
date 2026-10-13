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
claude mcp add sidestep -- uvx --from /absolute/path/to/oblique_strategies sidestep
```

Any other MCP client (Cursor, etc.):

```json
{
  "mcpServers": {
    "sidestep": {
      "command": "uvx",
      "args": ["--from", "/absolute/path/to/oblique_strategies", "sidestep"]
    }
  }
}
```

## Configuration

| Environment variable | Default |
| --- | --- |
| `SIDESTEP_DATABASE_URL` | `~/.sidestep/sidestep.db` (SQLite). Accepts `sqlite:///absolute/path.db` or `sqlite:relative/path.db`. |
| `SIDESTEP_DECKS` | The decks shipped in `sidestep/decks/` |

The database holds diffs from whatever projects your agents work on; keep it private.

## Decks

Each `*.toml` file in the decks directory is a deck named after the file. Every card needs a stable `id` (draws are recorded against it) and the `text` of the strategy:

```toml
[[card]]
id = "error-is-true"
text = "Pretend the error message is literally and precisely true."
```

`sidestep/decks/debugging.toml` is a placeholder starter deck.

## Storage backends

Everything outside the store modules talks only to the `DataStore` interface in `sidestep/store.py`. To add a backend (for example Postgres):

1. Write `sidestep/postgres_store.py` with a `PostgresStore(DataStore)` implementing `record_draw`, `record_outcome`, `get_draw` and `get_outcomes`.
2. Teach `open_store` in `sidestep/store.py` its URL scheme (`postgresql://...`).
3. Add a test that mixes `tests.store_contract.DataStoreContract` into a `unittest.TestCase`, as `tests/test_sqlite_store.py` does. The contract tests every store must pass come for free.

## Tests

```sh
uv run python -m unittest discover -t . -s tests
```

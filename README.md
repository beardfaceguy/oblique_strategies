# sidestep

An MCP server that serves a randomly drawn strategy card to a coding agent that is stuck, inspired by Brian Eno and Peter Schmidt's *Oblique Strategies*.

Agents get stuck in loops: retrying near-identical fixes, drifting from the real problem. A random strategy breaks the loop.

## Principles

- **The draw comes from code, not the model.** A model asked to pick a card picks the one that fits what it already thinks.
- **Trust the card.** The agent applies the strategy genuinely for one attempt before judging it.
- **Log every draw** (card, context, whether it helped) so the decks can evolve.
- **Original text only.** The official Oblique Strategies deck is copyrighted; every card here is original.

## Tools

| Tool | What it does |
| --- | --- |
| `draw_card(deck?, context?)` | Returns one random strategy, from every deck or only the named one, plus a draw id. |
| `record_outcome(draw_id, helped, note?)` | Records whether the strategy helped. |
| `list_decks()` | Lists decks and their card counts. |

The server's instructions tell the agent when to draw (same failure 3 times, about to revert its own change, 3 attempts without progress) and to trust the card.

## Install

Requires [uv](https://docs.astral.sh/uv/); dependencies are declared inline in `sidestep.py`.

Claude Code:

```sh
claude mcp add sidestep -- uv run --quiet /absolute/path/to/oblique_strategies/sidestep.py
```

Any other MCP client (Cursor, etc.):

```json
{
  "mcpServers": {
    "sidestep": {
      "command": "uv",
      "args": ["run", "--quiet", "/absolute/path/to/oblique_strategies/sidestep.py"]
    }
  }
}
```

## Decks

Decks are Markdown files in `decks/`; every line starting with `- ` is one card, and the file name is the deck name. Add a deck by adding a file. `decks/debugging.md` holds a placeholder starter deck.

| Environment variable | Default |
| --- | --- |
| `SIDESTEP_DECKS` | `decks/` next to `sidestep.py` |
| `SIDESTEP_LOG` | `~/.sidestep/draws.jsonl` |

## Tests

```sh
uv run --with "mcp>=2.2,<3" python -m unittest discover tests
```

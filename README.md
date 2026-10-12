# sidestep

Randomly drawn reframing prompts for coding agents (and humans) who are stuck, inspired by Brian Eno and Peter Schmidt's *Oblique Strategies*.

Agents get stuck in loops: retrying near-identical fixes, drifting from the real problem. A random card breaks the loop.

## Principles

- **The draw comes from code, not the model.** A model asked to pick a card picks the one that fits what it already thinks.
- **Trust the card.** Apply it genuinely for one attempt before judging it.
- **Log every draw** (card, context, whether it helped) so the decks can evolve.
- **Original text only.** The official Oblique Strategies deck is copyrighted; every card here is original.

## Install as a Claude Code skill

```sh
mkdir -p ~/.claude/skills
ln -s "$PWD/skills/sidestep" ~/.claude/skills/sidestep
```

Then type `/sidestep` (or `/sidestep debugging`) in Claude Code. The skill also tells the agent to draw on its own after 3 identical failures, before reverting its own change, or after 3 attempts without progress.

## Use from the command line

```sh
python3 skills/sidestep/sidestep.py draw --context "login test keeps failing"
# [debugging #3f9c2a1b] Pretend the error message is literally and precisely true.

python3 skills/sidestep/sidestep.py outcome 3f9c2a1b helped --note "the path really was wrong"
```

Draws and outcomes are appended to `~/.sidestep/draws.jsonl` (override with `SIDESTEP_LOG`).

## Decks

Decks are Markdown files in `skills/sidestep/decks/`; every line starting with `- ` is a card. Add a deck by adding a file. Only `debugging` exists so far.

## Tests

```sh
python3 -m unittest discover tests
```

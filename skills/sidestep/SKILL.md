---
name: sidestep
description: Draw a random reframing card when stuck. Use when the same test has failed 3 times, you are about to revert your own change, or 3 attempts in a row made no progress. Also when the user types /sidestep [deck].
argument-hint: "[deck]"
---

# Sidestep

A randomly drawn card to break a loop, in the spirit of Oblique Strategies.

## When to draw

Draw a card as soon as any of these is true:

- The same test or check has failed 3 times in a row.
- You are about to revert a change you made yourself.
- 3 attempts in a row made no measurable progress.
- The user asks for one (`/sidestep`, optionally followed by a deck name).

## How to draw

Never pick a card yourself. Run the script in this skill's directory:

```sh
python3 <skill-dir>/sidestep.py draw $ARGUMENTS --context "<one line: what you are stuck on>"
```

The deck defaults to `debugging`. `python3 <skill-dir>/sidestep.py decks` lists the others.

## Trust the card

Show the card to the user, then apply it, genuinely, for one full attempt before judging it, even if it seems irrelevant. Its relevance is often only visible after acting on it. Do not reinterpret it into what you were already going to do.

## Record the outcome

After that attempt, record whether it helped, using the id the draw printed:

```sh
python3 <skill-dir>/sidestep.py outcome <id> helped --note "<what changed>"
python3 <skill-dir>/sidestep.py outcome <id> did-not-help --note "<why>"
```

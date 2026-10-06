---
name: idea-forge
description: Generate high-impact, pitchable ideas by crossing a list of topics (problems) with a list of technologies. Builds a topic–bridge–tech knowledge graph, mines surprising-but-relevant seeds, generates ideas through diverse lenses and personas, kills weak ones, ranks the rest by a pairwise tournament judged by a non-technical panel, and writes pitch cards. Use when the user asks for ideas from data/topics + data/tech, mentions the RTA competition, or wants to run, resume or re-rank an ideation run.
---

# Idea Forge

Python (`python -m ideaforge`) does the deterministic work: parsing, embeddings, graph,
seed mining, dedupe, Elo. **You** do the judgement work: cards, ideas, critique, judging.
Prompts for each LLM stage live in `prompts/`. Read the one for a stage before doing it.

Setup (once per container): `uv venv .venv && uv pip install --python .venv/bin/python -r requirements.txt`.
Use `PY=.venv/bin/python`. A run lives in `runs/<name>/` (gitignored); default name `rta`.

Always read `data/brief.md` before stages 1–4. If it has unknowns that would change
which ideas win (judging criteria, tracks), ask the user once, then proceed.

## Pipeline

| # | Step | Who | Command / prompt | Output |
|---|---|---|---|---|
| 0 | Ingest lists | py | `$PY -m ideaforge ingest --run runs/rta --topics data/topics.md --tech data/tech.md` | items.json, links.json, notes.json |
| 1 | Cards + bridges | you | `prompts/01-cards.md` → then `$PY -m ideaforge check --run runs/rta` until ok | cards.json |
| 2 | Graph | py | `$PY -m ideaforge build --run runs/rta` | graph.json, graph.html |
| 3 | Mine seeds | py | `$PY -m ideaforge mine --run runs/rta --n 60` | seeds.json, seeds.md |
| 4 | Generate | you | `prompts/02-generate.md`, 1–3 ideas per seed | ideas.jsonl |
| 5 | Dedupe | py | `$PY -m ideaforge dedupe --run runs/rta` | ideas.dedup.jsonl |
| 6 | Critique | you | `prompts/03-critique.md` (incl. web prior-art check) → `$PY -m ideaforge survivors --run runs/rta` | survivors.jsonl, killed.md |
| 7 | Tournament | both | repeat: `pair` → fill `matches-rN.json` per `prompts/04-judge.md` → `record --round N` | tournament.json |
| 7b | Evolve (optional, after round 3) | you | `prompts/05-evolve.md`, then dedupe/critique/survivors, continue pairing | new entrants |
| 8 | Report | py | `$PY -m ideaforge report --run runs/rta --top 5` | TOP_IDEAS.md |

Rounds: `ceil(log2(survivors)) + 2`.

## Doing the LLM stages well

- **Cards (1):** write the bridge list once, from both lists together, before any card.
  For ~450 items, fill cards in batches of ~40 (parallel sub-agents only if the user has
  asked for agents); every batch gets the same bridge list. Web-search unfamiliar tool
  names instead of guessing.
- **Generate (4):** batches of ~10 seeds. Honour each seed's strategy and persona — they
  exist to stop every batch converging on the same 5 ideas. Problem first, tech last.
- **Critique (6):** expect to kill half or more. Reframe strong-but-technical ideas via
  `rewrite` rather than killing them.
- **Judge (7):** judge every row independently from `A_pitch`/`B_pitch` only, in the
  row's judge persona. First-impression impact for that audience beats cleverness.

## Helpers

- `agent-reach` skill / `WebSearch` — prior-art checks, Dubai facts, unknown tool names.
- `product-brainstorming` skill — when the user wants to explore one problem area live.
- `grilling` skill — stress-test a finalist with the user before they pitch it.

## Resuming

Every step reads/writes files in the run folder, so a run can resume anywhere: check
which outputs exist and continue from the first missing one. Re-running `mine` with a
different `--seed`/`--n` gives a fresh batch of seeds without redoing the cards.

## Reporting back

Give the user the top ideas as pitch cards (title, one-liner, problem, idea, impact,
first demo) plus the path to `TOP_IDEAS.md`, `graph.html` and `killed.md`. Say how many
ideas were generated, killed and ranked.

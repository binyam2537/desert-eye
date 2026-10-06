# desert-eye — topic × tech idea engine

Turns a list of **problems** (`data/topics.md`, RTA mobility topics) and a list of
**technologies** (`data/tech.md`) into a handful of ideas that a non-technical jury
understands in 10 seconds and remembers.

```
topics ─┐                         ┌─ anchor        (obvious fit, go big)
        ├─ cards ─ bridge graph ──┼─ serendipity   (relevant but rarely paired)
tech  ──┘   (needs / provides)    ├─ analogy       (works for A → try on look-alike B)
                                  ├─ combo / stack (two techs, different needs)
                                  └─ wildcard
                  ↓ seeds + random everyday persona
        generate (6 lenses) → dedupe → critique (7 gates + web prior-art)
        → Swiss Elo tournament judged by investor / official / journalist / user
        → evolve leaders → TOP_IDEAS.md pitch cards
```

Why this design and not Obsidian / RAG / plain vectors: see [docs/RESEARCH.md](docs/RESEARCH.md).

## Use it

In Claude Code, in this repo, say for example *"run idea-forge on the RTA lists"*. The
`idea-forge` skill (`.claude/skills/idea-forge/SKILL.md`) drives every step.

By hand:

```bash
uv venv .venv && uv pip install --python .venv/bin/python -r requirements.txt
PY=.venv/bin/python
$PY -m ideaforge ingest --run runs/rta --topics data/topics.md --tech data/tech.md
# write runs/rta/cards.json per prompts/01-cards.md, then:
$PY -m ideaforge check  --run runs/rta
$PY -m ideaforge build  --run runs/rta      # open runs/rta/graph.html
$PY -m ideaforge mine   --run runs/rta --n 60
# ideas.jsonl (prompts/02) → dedupe → critique.jsonl (prompts/03) → survivors
# then pair / judge (prompts/04) / record for each round, then report
```

`examples/demo/` has a tiny worked dataset (8 × 8 with cards) for trying the mechanics.

## Layout

| Path | What |
|---|---|
| `data/` | your lists + `brief.md` (audience, constraints, what wins — edit it) |
| `prompts/` | instructions for each LLM stage |
| `ideaforge/` | deterministic Python: parsing, embeddings, graph, mining, dedupe, Elo, report |
| `.claude/skills/` | `idea-forge` + installed skills (`agent-reach`, `product-brainstorming`, `grilling`) |
| `runs/` | per-run outputs (gitignored) |

Embeddings are local ([model2vec](https://github.com/MinishLab/model2vec), no GPU, no
API key; set `IDEAFORGE_EMBED_MODEL=tfidf` to work fully offline).

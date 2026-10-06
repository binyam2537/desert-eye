"""ideaforge CLI. The deterministic half of the pipeline; Claude does the LLM steps
(cards, ideas, critique, judging) by following .claude/skills/idea-forge/SKILL.md.

  python -m ideaforge ingest   --run runs/X --topics data/topics.txt --tech data/tech.txt
  python -m ideaforge check    --run runs/X            # validate cards.json
  python -m ideaforge build    --run runs/X            # embeddings + graph + graph.html
  python -m ideaforge mine     --run runs/X --n 60     # seeds.json / seeds.md
  python -m ideaforge dedupe   --run runs/X            # ideas.jsonl -> ideas.dedup.jsonl
  python -m ideaforge survivors --run runs/X           # + critique.jsonl -> survivors.jsonl
  python -m ideaforge pair     --run runs/X            # next tournament round
  python -m ideaforge record   --run runs/X --round N  # score a judged round
  python -m ideaforge report   --run runs/X --top 5    # TOP_IDEAS.md
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .embed import DEFAULT_MODEL


def main() -> None:
    ap = argparse.ArgumentParser(prog="ideaforge")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def cmd(name: str):
        p = sub.add_parser(name)
        p.add_argument("--run", type=Path, required=True)
        return p

    p = cmd("ingest")
    p.add_argument("--topics", type=Path, required=True)
    p.add_argument("--tech", type=Path, required=True)
    cmd("check")
    p = cmd("build")
    p.add_argument("--model", default=DEFAULT_MODEL, help="model2vec model id, or 'tfidf'")
    p = cmd("mine")
    p.add_argument("--n", type=int, default=60)
    p.add_argument("--cap", type=int, default=3, help="max seeds per topic / per tech")
    p.add_argument("--seed", type=int, default=0)
    p = cmd("dedupe")
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--threshold", type=float, default=0.78)
    cmd("survivors")
    p = cmd("pair")
    p.add_argument("--seed", type=int, default=0)
    p = cmd("record")
    p.add_argument("--round", type=int, required=True)
    p = cmd("report")
    p.add_argument("--top", type=int, default=5)
    a = ap.parse_args()

    if a.cmd == "ingest":
        from .io import ingest, save
        data = ingest(a.topics, a.tech)
        items = data["items"]
        save(a.run / "items.json", items)
        save(a.run / "links.json", data["links"])
        save(a.run / "notes.json", data["notes"])
        res = {**{k: sum(1 for i in items if i["kind"] == k) for k in ("topic", "tech")},
               "flagged_links": len(data["links"])}
    elif a.cmd == "check":
        from .graph import validate_cards
        from .io import load
        errs = validate_cards(load(a.run / "items.json"), load(a.run / "cards.json"))
        res = {"ok": not errs, "errors": errs[:50]}
    elif a.cmd == "build":
        from .graph import build
        res = build(a.run, a.model)
    elif a.cmd == "mine":
        from .mine import mine
        res = mine(a.run, a.n, a.cap, a.seed)
    elif a.cmd == "dedupe":
        from .dedupe import dedupe
        res = dedupe(a.run, a.model, a.threshold)
    elif a.cmd == "survivors":
        from .tournament import survivors
        res = survivors(a.run)
    elif a.cmd == "pair":
        from .tournament import pair
        res = pair(a.run, a.seed)
    elif a.cmd == "record":
        from .tournament import record
        res = record(a.run, a.round)
    else:
        from .report import report
        res = {"report": str(report(a.run, a.top))}
    print(json.dumps(res, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

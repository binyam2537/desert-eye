"""Collapse near-duplicate ideas. LLMs repeat themselves across parallel runs even when
told not to, so this runs before any critique or ranking."""
from __future__ import annotations

from pathlib import Path

from .embed import embed
from .io import load_jsonl, save_jsonl


def idea_text(idea: dict) -> str:
    return ". ".join(str(idea.get(k, "")) for k in ("title", "one_liner", "concept") if idea.get(k))


def dedupe(run: Path, model: str, threshold: float = 0.86) -> dict:
    ideas = load_jsonl(run / "ideas.jsonl")
    if not ideas:
        raise SystemExit("ideas.jsonl is empty")
    E = embed([idea_text(i) for i in ideas], model)
    S = E @ E.T
    keep, merged_into = [], {}
    for i, idea in enumerate(ideas):
        dup = next((k for k in keep if S[i, k] >= threshold), None)
        if dup is None:
            keep.append(i)
        else:
            merged_into[i] = dup
    out = []
    for k in keep:
        idea = dict(ideas[k])
        twins = [ideas[i]["id"] for i, d in merged_into.items() if d == k]
        if twins:
            # Convergent ideas reached from different seeds are a (weak) signal of strength.
            idea["also_generated_as"] = twins
            idea["seed_ids"] = sorted({idea.get("seed_id")} | {ideas[i].get("seed_id") for i, d in merged_into.items() if d == k} - {None})
        out.append(idea)
    save_jsonl(run / "ideas.dedup.jsonl", out)
    return {"in": len(ideas), "out": len(out), "merged": len(merged_into)}

"""Collapse near-duplicate ideas. LLMs repeat themselves across parallel runs even when
told not to, so this runs before any critique or ranking."""
from __future__ import annotations

from pathlib import Path

from .embed import embed
from .io import load_jsonl, save_jsonl


def idea_text(idea: dict) -> str:
    return ". ".join(str(idea.get(k, "")) for k in ("title", "one_liner", "concept") if idea.get(k))


def _norm_title(idea: dict) -> str:
    return " ".join(str(idea.get("title", "")).lower().split())


def dedupe(run: Path, model: str, threshold: float = 0.78, near: float = 0.72) -> dict:
    """Merge ideas whose text similarity >= threshold or whose titles are identical.
    Pairs in [near, threshold) are listed in near_duplicates.md for the critic to judge.
    (0.78 suits model2vec static embeddings; raise it for sentence-transformer models.)"""
    ideas = load_jsonl(run / "ideas.jsonl")
    if not ideas:
        raise SystemExit("ideas.jsonl is empty")
    E = embed([idea_text(i) for i in ideas], model)
    S = E @ E.T
    keep, merged_into = [], {}
    for i, idea in enumerate(ideas):
        dup = next((k for k in keep if S[i, k] >= threshold
                    or (_norm_title(idea) and _norm_title(idea) == _norm_title(ideas[k]))), None)
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
    lines = ["# Possible overlaps (not merged) — critic decides", ""]
    for a in range(len(keep)):
        for b in range(a + 1, len(keep)):
            i, j = keep[a], keep[b]
            if near <= S[i, j] < threshold:
                lines.append(f"- {S[i, j]:.2f} **{ideas[i]['id']}** {ideas[i].get('title', '')} ↔ "
                             f"**{ideas[j]['id']}** {ideas[j].get('title', '')}")
    (run / "near_duplicates.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"in": len(ideas), "out": len(out), "merged": len(merged_into), "near_pairs": len(lines) - 2}

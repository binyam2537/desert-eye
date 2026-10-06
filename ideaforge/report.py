"""Final pitch cards for the top ideas."""
from __future__ import annotations

from pathlib import Path

from .io import load, load_jsonl


def report(run: Path, top: int = 5) -> Path:
    st = load(run / "tournament.json")
    ideas = {i["id"]: i for i in load_jsonl(run / "survivors.jsonl")}
    seeds = {s["id"]: s for s in load(run / "seeds.json")}
    ranked = sorted(((i, r) for i, r in st["ratings"].items() if i in ideas), key=lambda kv: -kv[1])
    lines = [f"# Top {top} ideas", "",
             f"Ranked by a {st['rounds']}-round pairwise tournament judged by a simulated "
             "non-technical panel (investor, policymaker, journalist, everyday user).", ""]
    for rank, (iid, rating) in enumerate(ranked[:top], 1):
        i = ideas[iid]
        s = seeds.get(i.get("seed_id"), {})
        lines += [f"## {rank}. {i.get('title', iid)}  ·  Elo {round(rating)}", "",
                  f"> {i.get('one_liner', '')}", ""]
        for key, label in (("problem", "The problem"), ("concept", "The idea"),
                           ("how_tech_enables", "Why now / how tech makes it possible"),
                           ("impact", "Impact"), ("who_benefits", "Who benefits"),
                           ("first_demo", "First demo"), ("phases", "Roadmap")):
            if i.get(key):
                lines.append(f"**{label}:** {i[key]}  ")
        c = i.get("critique", {})
        if c.get("prior_art"):
            lines.append(f"**Closest existing work:** {c['prior_art']}  ")
        if c.get("biggest_risk"):
            lines.append(f"**Biggest risk:** {c['biggest_risk']}  ")
        if s:
            techs = " + ".join(t["name"] for t in s.get("techs", []))
            lines.append(f"<sub>Origin: seed {s['id']} ({s['strategy']}) — {s['topic']['name']} × {techs}; "
                         f"relevance {s['metrics']['relevance']}, surprise {s['metrics']['surprise']}</sub>")
        lines.append("")
    if len(ranked) > top:
        lines += ["## Runners-up", ""]
        lines += [f"- {ideas[i].get('title', i)} (Elo {round(r)})" for i, r in ranked[top:top + 10]]
    out = run / "TOP_IDEAS.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out

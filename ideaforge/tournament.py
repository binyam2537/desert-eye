"""Critique filter + Swiss-system Elo tournament.

LLMs are unreliable at absolute 1-10 scoring of ideas but much better at "which of
these two is stronger?", so ranking is done by pairwise matches (as in Google's AI
co-scientist). Every match is judged twice with the order swapped; a split verdict
counts as a draw, which cancels position bias.
"""
from __future__ import annotations

import random
from pathlib import Path

from .io import load, load_jsonl, save, save_jsonl
from .personas import JUDGE_PANEL

GATES = ["ten_second", "matters", "not_incremental", "tech_is_enabler", "broad", "plausible", "not_already_done"]
K = 32
START = 1200.0


def survivors(run: Path) -> dict:
    ideas = {i["id"]: i for i in load_jsonl(run / "ideas.dedup.jsonl")}
    crit = {c["id"]: c for c in load_jsonl(run / "critique.jsonl")}
    missing = sorted(set(ideas) - set(crit))
    if missing:
        raise SystemExit(f"critique.jsonl is missing {len(missing)} ideas, e.g. {missing[:5]}")
    keep, killed = [], []
    for iid, idea in ideas.items():
        c = crit[iid]
        failed = [g for g in GATES if not c.get("gates", {}).get(g, False)]
        # The critic may reframe a strong idea that was pitched too technically.
        idea = {**idea, **{k: v for k, v in (c.get("rewrite") or {}).items() if v}, "critique": c}
        (killed if failed else keep).append((idea, failed))
    save_jsonl(run / "survivors.jsonl", [i for i, _ in keep])
    lines = ["# Killed ideas", ""]
    for idea, failed in killed:
        lines.append(f"- **{idea['id']} {idea.get('title', '')}** — failed: {', '.join(failed)}. "
                     f"{idea['critique'].get('kill_reason', '')}")
    (run / "killed.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"survivors": len(keep), "killed": len(killed)}


def _state_path(run: Path) -> Path:
    return run / "tournament.json"


def _state(run: Path) -> dict:
    p = _state_path(run)
    ids = [i["id"] for i in load_jsonl(run / "survivors.jsonl")]
    if p.exists():
        st = load(p)
        # Late entrants (evolved ideas) join at the median rating so they meet mid-table ideas.
        new = [i for i in ids if i not in st["ratings"]]
        if new:
            vals = sorted(st["ratings"].values())
            mid = vals[len(vals) // 2]
            for i in new:
                st["ratings"][i], st["games"][i] = mid, 0
        return st
    if len(ids) < 2:
        raise SystemExit("need at least 2 survivors for a tournament")
    return {"ratings": {i: START for i in ids}, "played": [], "rounds": 0, "games": {i: 0 for i in ids}}


def pair(run: Path, seed: int = 0) -> dict:
    """Write matches for the next round: neighbours in the rating table, no rematches."""
    st = _state(run)
    ideas = {i["id"]: i for i in load_jsonl(run / "survivors.jsonl")}
    played = {frozenset(p) for p in st["played"]}
    rng = random.Random(seed + st["rounds"])
    order = sorted(st["ratings"], key=lambda i: (-st["ratings"][i], rng.random()))
    matches, pool = [], order[:]
    if len(pool) % 2:  # bye goes to the lowest-rated idea that has played the most
        bye = max(reversed(pool), key=lambda i: st["games"][i])
        pool.remove(bye)
    while pool:
        a = pool.pop(0)
        b = next((x for x in pool if frozenset((a, x)) not in played), pool[0])
        pool.remove(b)
        matches.append((a, b))
    rnd = st["rounds"] + 1
    out = []
    for n, (a, b) in enumerate(matches, 1):
        judge = JUDGE_PANEL[(n + rnd) % len(JUDGE_PANEL)]
        for order_ in ("AB", "BA"):
            x, y = (a, b) if order_ == "AB" else (b, a)
            out.append({"match": f"R{rnd}M{n}", "order": order_, "A": x, "B": y, "judge": judge,
                        "A_pitch": _pitch(ideas[x]), "B_pitch": _pitch(ideas[y]),
                        "winner": None, "reason": ""})
    save(run / f"matches-r{rnd}.json", out)
    save(_state_path(run), st)
    return {"round": rnd, "matches": len(matches), "judgements_to_fill": len(out),
            "file": str(run / f"matches-r{rnd}.json")}


def _pitch(idea: dict) -> str:
    """Only what a non-technical audience would hear: no metrics, no seed metadata."""
    keys = [("title", ""), ("one_liner", ""), ("problem", "Problem: "), ("concept", "Idea: "),
            ("impact", "Impact: ")]
    return "\n".join(f"{p}{idea[k]}" for k, p in keys if idea.get(k))


def record(run: Path, rnd: int) -> dict:
    st = _state(run)
    if rnd != st["rounds"] + 1:
        raise SystemExit(f"expected round {st['rounds'] + 1}, got {rnd}")
    rows = load(run / f"matches-r{rnd}.json")
    by_match: dict[str, list[dict]] = {}
    for r in rows:
        if r.get("winner") not in ("A", "B", "tie"):
            raise SystemExit(f"{r['match']} {r['order']}: winner must be 'A', 'B' or 'tie'")
        by_match.setdefault(r["match"], []).append(r)
    for m, rs in by_match.items():
        ab = next(r for r in rs if r["order"] == "AB")
        a, b = ab["A"], ab["B"]
        pts = 0.0  # points for a, out of the two judgements
        for r in rs:
            if r["winner"] == "tie":
                pts += 0.5
            elif (r["winner"] == "A") == (r["A"] == a):
                pts += 1.0
        sa = pts / len(rs)
        ea = 1 / (1 + 10 ** ((st["ratings"][b] - st["ratings"][a]) / 400))
        st["ratings"][a] += K * (sa - ea)
        st["ratings"][b] += K * ((1 - sa) - (1 - ea))
        st["games"][a] += 1
        st["games"][b] += 1
        st["played"].append([a, b])
    st["rounds"] = rnd
    save(_state_path(run), st)
    top = sorted(st["ratings"].items(), key=lambda kv: -kv[1])[:5]
    return {"round": rnd, "top5": [(i, round(r)) for i, r in top]}

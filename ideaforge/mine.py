"""Mine idea seeds from the graph.

Each seed is a topic + one or two technologies + the *reason* they connect (shared
bridges, an analogy, or a graph path). Seeds are scored on three separate axes taken
from serendipity research (relevance x novelty x surprise) instead of plain cosine
similarity, which only ever returns the obvious pairings.

Strategies (default quota share in parentheses):
  anchor       (0.15) strong functional fit and semantically close -> credible ideas
  serendipity  (0.35) strong functional fit but semantically distant -> surprising-yet-relevant
  analogy      (0.20) tech X fits topic A; topic B has the same *needs* as A but looks unrelated
  combo        (0.20) topic + two techs from different tech clusters covering different needs
  wildcard     (0.10) random distant pair that still shares at least one bridge
  stack        (0.12, only if the tech list flags 'A <-> B' pairs) the topics a flagged
               tech pair serves best together
"""
from __future__ import annotations

import math
import random
from itertools import islice
from pathlib import Path

import networkx as nx
import numpy as np

from .graph import load_graph
from .io import load, save
from .personas import GENERATION_PERSONAS

QUOTAS = {"anchor": 0.15, "serendipity": 0.35, "analogy": 0.20, "combo": 0.20, "wildcard": 0.10}
QUOTAS_WITH_STACK = {"stack": 0.12, "anchor": 0.13, "serendipity": 0.30, "analogy": 0.18,
                     "combo": 0.17, "wildcard": 0.10}


def _pct(m: np.ndarray) -> np.ndarray:
    """Percentile rank (0..1) of every entry within the whole matrix."""
    flat = m.ravel()
    ranks = np.empty_like(flat)
    ranks[np.argsort(flat, kind="stable")] = np.arange(flat.size)
    return (ranks / max(1, flat.size - 1)).reshape(m.shape)


def _unit(m: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(m, axis=1, keepdims=True)
    n[n == 0] = 1.0
    return m / n


class Space:
    def __init__(self, run: Path):
        self.G, self.meta = load_graph(run)
        self.cards = load(run / "cards.json")
        self.groups = {it["id"]: (it.get("groups") or [""])[0] for it in load(run / "items.json")}
        self.user_links = self.meta.get("user_links", [])
        self.bridges = self.meta["bridges_order"]
        self.bname = {b["id"]: b["name"] for b in self.meta["bridges"]}
        k = self.meta["kinds"]
        self.T, self.X = k["topic"]["ids"], k["tech"]["ids"]
        self.tcomm, self.xcomm = k["topic"]["community"], k["tech"]["community"]
        self.Et, self.Ex = np.load(run / "emb_topic.npy"), np.load(run / "emb_tech.npy")
        self.Bt, self.Bx = np.load(run / "bridge_topic.npy"), np.load(run / "bridge_tech.npy")

        # Relevance: best shared bridge, plus a little credit for each extra shared one.
        self.R = np.zeros((len(self.T), len(self.X)), dtype=np.float32)
        for lo in range(0, len(self.T), 64):  # chunked so big lists don't blow memory
            prod = self.Bt[lo:lo + 64, None, :] * self.Bx[None, :, :]   # t x X x B
            best = prod.max(axis=2)
            self.R[lo:lo + 64] = np.clip(best + 0.15 * (prod.sum(axis=2) - best), 0, 1)
        self.C = self.Et @ self.Ex.T                                # semantic closeness
        self.Cpct = _pct(self.C)
        self.S = 1.0 - self.Cpct                                    # surprise
        # Novelty: penalise generic "hub" techs ("AI", "apps") that sit close to every topic
        # in meaning or plausibly fit most of them functionally.
        rank = lambda v: np.argsort(np.argsort(v, kind="stable"), kind="stable") / max(1, len(v) - 1)
        hub_pct = 0.5 * rank(self.Cpct.mean(axis=0)) + 0.5 * rank((self.R >= 0.5).mean(axis=0) + 1e-3 * self.R.mean(axis=0))
        self.N = np.broadcast_to(1.0 - 0.5 * hub_pct, self.C.shape)
        self.seren = self.R * (0.35 + 0.65 * self.S) * (0.6 + 0.4 * self.N)

    def shared(self, ti: int, xi: int) -> list[dict]:
        prod = self.Bt[ti] * self.Bx[xi]
        out = []
        for j in np.argsort(-prod):
            if prod[j] <= 0:
                break
            b = self.bridges[j]
            out.append({"bridge": b, "name": self.bname[b], "strength": round(float(prod[j]), 3),
                        "topic_why": self._why(self.T[ti], b), "tech_why": self._why(self.X[xi], b)})
        return out[:3]

    def _why(self, iid: str, b: str) -> str:
        for ln in self.cards["items"][iid]["links"]:
            if ln["bridge"] == b:
                return ln.get("why", "")
        return ""

    def paths(self, a: str, b: str, k: int = 3, max_len: int = 5) -> list[list[str]]:
        """Up to k node-diverse short paths a->b (K-Paths style), weighting strong edges as short."""
        H = self.G.copy()
        for u, v, d in H.edges(data=True):
            d["cost"] = 1.0 - 0.9 * float(d.get("w", 0.5))
        out, used = [], set()
        try:
            for p in islice(nx.shortest_simple_paths(H, a, b, weight="cost"), 30):
                if len(p) > max_len:
                    break
                mid = set(p[1:-1])
                if out and mid & used:
                    continue  # keep paths that go through different intermediate nodes
                out.append(p)
                used |= mid
                if len(out) == k:
                    break
        except nx.NetworkXNoPath:
            pass
        label = lambda n: self.G.nodes[n].get("label", n)
        return [[label(n) for n in p] for p in out]


def _cands_anchor(sp: Space):
    score = sp.R * (1 - sp.S)
    for ti, xi in zip(*np.unravel_index(np.argsort(-score, axis=None), score.shape)):
        if sp.R[ti, xi] < 0.3:
            continue
        yield score[ti, xi], {"topic": int(ti), "techs": [int(xi)]}


def _cands_serendipity(sp: Space):
    for ti, xi in zip(*np.unravel_index(np.argsort(-sp.seren, axis=None), sp.seren.shape)):
        if sp.R[ti, xi] < 0.3 or sp.S[ti, xi] < 0.5:
            continue
        yield sp.seren[ti, xi], {"topic": int(ti), "techs": [int(xi)]}


def _cands_analogy(sp: Space):
    prof = _unit(sp.Bt) @ _unit(sp.Bt).T        # same needs
    look = _pct(sp.Et @ sp.Et.T)                # looks alike
    out = []
    obvious = np.argwhere((sp.R >= 0.5) & (sp.Cpct >= 0.7))
    for t1, x in obvious:
        for t2 in range(len(sp.T)):
            if t2 == t1 or prof[t1, t2] < 0.5 or look[t1, t2] > 0.5:
                continue
            if sp.Cpct[t2, x] > 0.6:            # already an obvious fit for t2 too
                continue
            s = prof[t1, t2] * (1 - look[t1, t2]) * sp.R[t1, x]
            out.append((s, {"topic": int(t2), "techs": [int(x)], "via_topic": int(t1)}))
    out.sort(key=lambda z: -z[0])
    yield from out


def _cands_combo(sp: Space):
    xsim = _pct(sp.Ex @ sp.Ex.T)
    out = []
    for ti in range(len(sp.T)):
        need = sp.Bt[ti]
        if need.sum() == 0:
            continue
        top = [int(x) for x in np.argsort(-sp.R[ti])[:8] if sp.R[ti, x] >= 0.25]
        for i, a in enumerate(top):
            for b in top[i + 1:]:
                if sp.xcomm[sp.X[a]] == sp.xcomm[sp.X[b]]:
                    continue
                cov = (np.minimum(need, np.maximum(sp.Bx[a], sp.Bx[b]))).sum() / need.sum()
                solo = max((np.minimum(need, sp.Bx[a])).sum(), (np.minimum(need, sp.Bx[b])).sum()) / need.sum()
                gain = cov - solo                # what the second tech adds
                if gain <= 0.05:
                    continue
                s = cov * (0.5 + gain) * (0.5 + 0.5 * (1 - xsim[a, b]))
                out.append((s, {"topic": ti, "techs": [a, b]}))
    out.sort(key=lambda z: -z[0])
    yield from out


def _cands_stack(sp: Space):
    xi = {x: i for i, x in enumerate(sp.X)}
    out = []
    for a, b in sp.user_links:
        if a not in xi or b not in xi:
            continue  # a topic-topic pair; nothing to stack
        a, b = xi[a], xi[b]
        both = np.maximum(sp.Bx[a], sp.Bx[b])
        need = sp.Bt.sum(axis=1)
        need[need == 0] = 1.0
        cov = np.minimum(sp.Bt, both[None, :]).sum(axis=1) / need
        score = cov * (0.5 + 0.5 * (sp.S[:, a] + sp.S[:, b]) / 2)
        for ti in np.argsort(-score)[:4]:
            if cov[ti] > 0:
                out.append((float(score[ti]), {"topic": int(ti), "techs": [a, b]}))
    out.sort(key=lambda z: -z[0])
    yield from out


def _cands_wildcard(sp: Space, rng: random.Random):
    pairs = [(int(t), int(x)) for t, x in np.argwhere((sp.R > 0) & (sp.S > 0.75))]
    rng.shuffle(pairs)
    for t, x in pairs:
        yield 0.0, {"topic": t, "techs": [x]}


def mine(run: Path, n: int = 60, cap: int = 3, seed: int = 0) -> dict:
    sp = Space(run)
    rng = random.Random(seed)
    gens = {"anchor": _cands_anchor(sp), "serendipity": _cands_serendipity(sp),
            "analogy": _cands_analogy(sp), "combo": _cands_combo(sp),
            "wildcard": _cands_wildcard(sp, rng), "stack": _cands_stack(sp)}
    quotas = QUOTAS_WITH_STACK if sp.user_links else QUOTAS
    # No single topic category (e.g. "Parking") may take more than its fair share.
    n_groups = len({sp.groups.get(t, "") for t in sp.T}) or 1
    group_cap = math.ceil(1.5 * n / n_groups) + 1
    use_t, use_x, use_g, seen, seeds = {}, {}, {}, set(), []
    for strat, share in quotas.items():
        want = max(1, round(n * share))
        got = 0
        for score, c in gens[strat]:
            if got >= want:
                break
            key = (c["topic"], tuple(sorted(c["techs"])))
            if key in seen:
                continue
            # Diversity caps: no topic or tech may dominate the seed set.
            g = sp.groups.get(sp.T[c["topic"]], "")
            if (use_t.get(c["topic"], 0) >= cap or any(use_x.get(x, 0) >= cap for x in c["techs"])
                    or use_g.get(g, 0) >= group_cap):
                continue
            seen.add(key)
            use_g[g] = use_g.get(g, 0) + 1
            use_t[c["topic"]] = use_t.get(c["topic"], 0) + 1
            for x in c["techs"]:
                use_x[x] = use_x.get(x, 0) + 1
            seeds.append(_describe(sp, strat, score, c, rng))
            got += 1
    for i, s in enumerate(seeds, 1):
        s["id"] = f"S{i:03d}"
    save(run / "seeds.json", seeds)
    (run / "seeds.md").write_text(_markdown(seeds), encoding="utf-8")
    counts = {k: sum(1 for s in seeds if s["strategy"] == k) for k in quotas}
    return {"seeds": len(seeds), "by_strategy": counts}


def _describe(sp: Space, strat: str, score: float, c: dict, rng: random.Random) -> dict:
    ti, xs = c["topic"], c["techs"]
    tid = sp.T[ti]
    card = lambda iid: sp.cards["items"][iid]
    seed = {
        "strategy": strat,
        "score": round(float(score), 4),
        "topic": {"id": tid, "name": sp.G.nodes[tid]["label"], "group": sp.groups.get(tid, ""), "plain": card(tid).get("plain", ""),
                  "who": card(tid).get("who", ""), "pain": card(tid).get("pain", ""),
                  "scale": card(tid).get("scale", "")},
        "techs": [{"id": sp.X[x], "name": sp.G.nodes[sp.X[x]]["label"], "plain": card(sp.X[x]).get("plain", ""),
                   "maturity": card(sp.X[x]).get("maturity", "")} for x in xs],
        "metrics": {"relevance": round(float(np.mean([sp.R[ti, x] for x in xs])), 3),
                    "surprise": round(float(np.mean([sp.S[ti, x] for x in xs])), 3),
                    "novelty": round(float(np.mean([sp.N[ti, x] for x in xs])), 3)},
        "bridges": [sp.shared(ti, x) for x in xs],
        "paths": sp.paths(tid, sp.X[xs[0]]),
        "persona": rng.choice(GENERATION_PERSONAS),
    }
    if "via_topic" in c:
        v = sp.T[c["via_topic"]]
        seed["analogy"] = {"from_topic": sp.G.nodes[v]["label"],
                           "note": f"{seed['techs'][0]['name']} is a natural fit for "
                                   f"{sp.G.nodes[v]['label']}; {seed['topic']['name']} has the same "
                                   f"underlying needs but is rarely linked to it."}
    return seed


def _markdown(seeds: list[dict]) -> str:
    lines = ["# Idea seeds", "",
             "Each seed is a *starting point*, not an idea. Generate from the problem first.", ""]
    for s in seeds:
        techs = " + ".join(t["name"] for t in s["techs"])
        m = s["metrics"]
        grp = f" ({s['topic']['group']})" if s['topic'].get('group') else ""
        lines += [f"## {s['id']} [{s['strategy']}] {s['topic']['name']}{grp} × {techs}",
                  f"- **Problem:** {s['topic']['plain']} — *who:* {s['topic']['who']} — *pain:* {s['topic']['pain']}"
                  + (f" — *scale:* {s['topic']['scale']}" if s['topic'].get('scale') else "")]
        for t in s["techs"]:
            lines.append(f"- **{t['name']}** ({t.get('maturity') or 'n/a'}): {t['plain']}")
        for t, br in zip(s["techs"], s["bridges"]):
            for b in br:
                lines.append(f"- *Bridge* **{b['name']}** ({b['strength']}): topic — {b['topic_why']}; "
                             f"{t['name']} — {b['tech_why']}")
        if s.get("analogy"):
            lines.append(f"- *Analogy:* {s['analogy']['note']}")
        if s["paths"]:
            lines.append("- *Paths:* " + " | ".join(" → ".join(p) for p in s["paths"]))
        lines += [f"- *Relevance* {m['relevance']} · *surprise* {m['surprise']} · *novelty* {m['novelty']}",
                  f"- *Think as:* {s['persona']}", ""]
    return "\n".join(lines)

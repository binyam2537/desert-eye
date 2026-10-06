"""Build the tripartite graph  Topic --needs--> Bridge <--provides-- Tech,
plus same-kind similarity edges and communities, from items + LLM-written cards."""
from __future__ import annotations

import json
from pathlib import Path

import networkx as nx
import numpy as np

from .embed import embed
from .io import item_text, load, save

KNN = 4  # similarity neighbours per node when linking items of the same kind


def active_items(items: list[dict], cards: dict) -> list[dict]:
    """Items minus those the cards file folds into another item (`aliases`) or drops
    as not-really-an-item (`drop`, e.g. a list of road users under a heading)."""
    gone = set(cards.get("aliases", {})) | set(cards.get("drop", []))
    return [it for it in items if it["id"] not in gone]


def validate_cards(items: list[dict], cards: dict) -> list[str]:
    """Return a list of problems; empty means the cards file is usable."""
    errs = []
    ids = {it["id"] for it in items}
    for a, target in cards.get("aliases", {}).items():
        if a not in ids or target not in ids:
            errs.append(f"alias {a} -> {target}: both must be item ids")
        elif target in cards.get("aliases", {}):
            errs.append(f"alias {a} -> {target}: target is itself an alias")
    items = active_items(items, cards)
    bridge_ids = {b["id"] for b in cards.get("bridges", [])}
    if not bridge_ids:
        errs.append("cards.bridges is empty")
    per_item = cards.get("items", {})
    for it in items:
        c = per_item.get(it["id"])
        if c is None:
            errs.append(f"missing card for {it['id']}")
            continue
        if not c.get("plain"):
            errs.append(f"{it['id']}: 'plain' is empty")
        links = c.get("links", [])
        if not links:
            errs.append(f"{it['id']}: no bridge links")
        for ln in links:
            if ln.get("bridge") not in bridge_ids:
                errs.append(f"{it['id']}: unknown bridge {ln.get('bridge')!r}")
            w = ln.get("w", 0)
            if not isinstance(w, (int, float)) or not 0 < w <= 1:
                errs.append(f"{it['id']}: weight for {ln.get('bridge')} must be in (0, 1]")
    unknown = set(per_item) - {it["id"] for it in items}
    errs += [f"card for unknown item {u}" for u in sorted(unknown)]
    return errs


def _bridge_matrix(ids: list[str], cards: dict, bridges: list[str]) -> np.ndarray:
    col = {b: j for j, b in enumerate(bridges)}
    m = np.zeros((len(ids), len(bridges)), dtype=np.float32)
    for i, iid in enumerate(ids):
        for ln in cards["items"][iid]["links"]:
            m[i, col[ln["bridge"]]] = max(m[i, col[ln["bridge"]]], float(ln["w"]))
    return m


def _profile_sim(m: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(m, axis=1, keepdims=True)
    n[n == 0] = 1.0
    u = m / n
    return u @ u.T


def _communities(ids: list[str], sim: np.ndarray, seed: int = 7) -> dict[str, int]:
    g = nx.Graph()
    g.add_nodes_from(ids)
    for i in range(len(ids)):
        order = np.argsort(-sim[i])
        for j in [j for j in order if j != i][:KNN]:
            if sim[i, j] > 0:
                g.add_edge(ids[i], ids[j], weight=float(sim[i, j]))
    comms = nx.community.louvain_communities(g, weight="weight", seed=seed)
    return {n: ci for ci, c in enumerate(sorted(comms, key=len, reverse=True)) for n in c}


def build(run: Path, model: str) -> dict:
    items = load(run / "items.json")
    cards = load(run / "cards.json")
    errs = validate_cards(items, cards)
    if errs:
        raise SystemExit("cards.json is not valid:\n  " + "\n  ".join(errs[:40]))
    items = active_items(items, cards)
    aliases = cards.get("aliases", {})

    bridges = [b["id"] for b in cards["bridges"]]
    by_kind = {k: [it for it in items if it["kind"] == k] for k in ("topic", "tech")}
    out = {"bridges": cards["bridges"], "kinds": {}}
    G = nx.Graph()
    for b in cards["bridges"]:
        G.add_node(b["id"], kind="bridge", label=b["name"], desc=b.get("desc", ""))

    for kind, its in by_kind.items():
        ids = [it["id"] for it in its]
        emb = embed([item_text(it, cards["items"][it["id"]]) for it in its], model)
        bm = _bridge_matrix(ids, cards, bridges)
        # Communities mix meaning (embeddings) and function (which bridges it touches).
        sim = 0.5 * (emb @ emb.T) + 0.5 * _profile_sim(bm)
        comm = _communities(ids, sim)
        np.save(run / f"emb_{kind}.npy", emb)
        np.save(run / f"bridge_{kind}.npy", bm)
        out["kinds"][kind] = {"ids": ids, "community": comm}
        for it in its:
            c = cards["items"][it["id"]]
            G.add_node(it["id"], kind=kind, label=it["name"], desc=it.get("desc", ""),
                       plain=c.get("plain", ""), community=comm[it["id"]])
            rel = "needs" if kind == "topic" else "provides"
            for ln in c["links"]:
                G.add_edge(it["id"], ln["bridge"], rel=rel, w=float(ln["w"]), why=ln.get("why", ""))
        es = emb @ emb.T
        for i in range(len(ids)):
            for j in [j for j in np.argsort(-es[i]) if j != i][:KNN]:
                if not G.has_edge(ids[i], ids[j]):
                    G.add_edge(ids[i], ids[j], rel="similar", w=float(es[i, j]))

    # Pairs the user flagged as worth checking ("SUMO <-> CARLA").
    user_links = []
    if (run / "links.json").exists():
        for a, b in load(run / "links.json"):
            a, b = aliases.get(a, a), aliases.get(b, b)
            if a in G and b in G and a != b:
                G.add_edge(a, b, rel="user-flagged", w=0.8)
                user_links.append([a, b])
    out["user_links"] = user_links
    out["bridges_order"] = bridges
    save(run / "graph.json", {**out, "graph": nx.node_link_data(G, edges="links")})
    _write_html(run / "graph.html", G)
    return {"nodes": G.number_of_nodes(), "edges": G.number_of_edges(),
            "topic_communities": len(set(out["kinds"]["topic"]["community"].values())),
            "tech_communities": len(set(out["kinds"]["tech"]["community"].values()))}


def load_graph(run: Path) -> tuple[nx.Graph, dict]:
    meta = load(run / "graph.json")
    return nx.node_link_graph(meta["graph"], edges="links"), meta


_HTML = """<!doctype html><html><head><meta charset="utf-8"><title>Idea Graph</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<script src="https://cdnjs.cloudflare.com/ajax/libs/vis-network/9.1.9/standalone/umd/vis-network.min.js"></script>
<style>:root{--bg:#fafaf7;--fg:#222;--muted:#666}
@media (prefers-color-scheme:dark){:root{--bg:#16171a;--fg:#e8e8e8;--muted:#9a9a9a}}
body{margin:0;font:14px system-ui,sans-serif;background:var(--bg);color:var(--fg)}
#g{position:absolute;inset:0}#info{position:absolute;left:12px;top:12px;max-width:360px;
background:var(--bg);border:1px solid var(--muted);border-radius:8px;padding:10px 12px;opacity:.95}
small{color:var(--muted)}</style></head><body><div id="g"></div>
<div id="info"><b>Topic</b> (circles) · <b>Bridge</b> (diamonds) · <b>Tech</b> (boxes)<br>
<small>Colour = community. Click a node for details. Dashed = semantic similarity. Red = your flagged pairs.</small><div id="d"></div></div>
<script>const N=__NODES__,E=__EDGES__;
const shape={topic:"dot",tech:"box",bridge:"diamond"};
const pal=["#4e79a7","#f28e2b","#59a14f","#e15759","#76b7b2","#edc948","#b07aa1","#ff9da7","#9c755f","#bab0ac"];
const nodes=new vis.DataSet(N.map(n=>({id:n.id,label:n.label,shape:shape[n.kind],
 color:n.kind==="bridge"?"#888":pal[(n.community||0)%pal.length],font:{color:getComputedStyle(document.body).color},
 title:(n.plain||n.desc||""),size:n.kind==="bridge"?14:10})));
const edges=new vis.DataSet(E.map((e,i)=>({id:i,from:e.source,to:e.target,dashes:e.rel==="similar",color:e.rel==="user-flagged"?{color:"#d62728"}:undefined,
 width:e.rel==="similar"?0.5:1+2*(e.w||0),title:e.rel+(e.why?": "+e.why:""),color:{opacity:e.rel==="similar"?.25:.6}})));
const net=new vis.Network(document.getElementById("g"),{nodes,edges},{physics:{solver:"forceAtlas2Based"},interaction:{hover:true}});
net.on("click",p=>{if(!p.nodes.length)return;const n=N.find(x=>x.id===p.nodes[0]);
 document.getElementById("d").innerHTML="<hr><b>"+n.label+"</b><br>"+(n.plain||n.desc||"")+"<br><small>"+n.id+"</small>";});
</script></body></html>"""


def _write_html(path: Path, G: nx.Graph) -> None:
    nodes = [{"id": n, **{k: v for k, v in d.items()}} for n, d in G.nodes(data=True)]
    edges = [{"source": u, "target": v, **d} for u, v, d in G.edges(data=True)]
    path.write_text(_HTML.replace("__NODES__", json.dumps(nodes, ensure_ascii=False))
                    .replace("__EDGES__", json.dumps(edges, ensure_ascii=False)), encoding="utf-8")

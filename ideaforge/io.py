"""Reading the two input lists and the JSON files every stage passes along."""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

KINDS = ("topic", "tech")


def slug(text: str) -> str:
    """Normalised id: lowercase, crude singular ('Digital twins' == 'Digital Twin'),
    'ROS 2' == 'ROS2'."""
    words = re.findall(r"[a-z0-9]+", text.lower())
    words = [w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith(("ss", "us", "is")) else w for w in words]
    s = re.sub(r"([a-z])-(\d)", r"\1\2", "-".join(words))
    return s[:60] or "item"


def _clean(text: str) -> str:
    text = re.sub(r"\*\*|__|`", "", text)
    return re.sub(r"\s+", " ", text).strip().rstrip("*").strip()


def _split_name_desc(line: str) -> tuple[str, str]:
    """'Name: description', 'Name — description', 'Name - description'."""
    for sep in (" — ", " – ", " - ", ": ", "\t"):
        if sep in line:
            name, desc = line.split(sep, 1)
            if 0 < len(name.strip()) <= 60:
                return _clean(name), _clean(desc)
    return _clean(line), ""


LINK_RE = re.compile(r"^\**\s*([^*↔]+?)\s*(?:↔|<->|<=>)\s*([^*]+?)\s*\**\s*$")
LABEL_LIST_RE = re.compile(r"^\**([\w /&+-]{2,40}):\**\s+(.+,.+)$")
BULLET_RE = re.compile(r"^(\s*)(?:[-*+•]|\d+[.)])\s+(.*)$")


def parse_markdown(text: str) -> tuple[list[dict], list[tuple[str, str]], dict[str, list[str]]]:
    """Parse a loosely structured markdown list.

    Returns (rows, links, notes):
      rows  — {name, desc, group}; headings and parent bullets become the group
      links — ('A', 'B') pairs written as 'A ↔ B'
      notes — prose sentences per group (useful context for the LLM stages)
    """
    lines = text.replace("\r", "").split("\n")
    rows, links, notes = [], [], {}
    heading, parent, parent_indent = "", None, -1

    def indent_of(raw: str) -> int:
        return len(raw.expandtabs(4)) - len(raw.expandtabs(4).lstrip())

    def is_plain_short(raw: str) -> bool:
        t = raw.strip()
        return (bool(t) and not t.startswith(("#", "|", "-", "*", "↓")) and not BULLET_RE.match(raw)
                and len(t.split()) <= 5 and not t.endswith((".", ":", "?", "!")) and "↔" not in t)

    nonblank = [i for i, l in enumerate(lines) if l.strip() and l.strip() != "↓"]
    for k, i in enumerate(nonblank):
        raw = lines[i]
        t = raw.strip()
        group = parent or heading
        if t.startswith("#"):
            heading = _clean(re.sub(r"^#+\s*(?:\d+[.)]\s*)?", "", t))
            parent = None
            continue
        if re.fullmatch(r"\|?[\s:|-]+\|?", t):  # table separator
            continue
        if t.startswith("|"):
            cells = [_clean(c) for c in t.strip("|").split("|")]
            if len(cells) >= 1 and cells[0] and cells[0].lower() not in ("technology", "topic", "name", "tech"):
                rows.append({"name": cells[0], "desc": cells[1] if len(cells) > 1 else "", "group": heading})
            continue
        m = None if BULLET_RE.match(raw) else LINK_RE.match(t)  # '- AV ↔ pedestrians' is an item
        if m:
            links.append((_clean(m.group(1)), _clean(m.group(2))))
            continue
        bm = BULLET_RE.match(raw)
        body = bm.group(2) if bm else t
        lm = LABEL_LIST_RE.match(_clean(body) if "**" not in body else body)
        if lm:
            label = _clean(lm.group(1))
            for part in lm.group(2).split(","):
                part = _clean(part)
                if part:
                    rows.append({"name": part, "desc": "", "group": label})
            continue
        if bm:
            ind = indent_of(raw)
            nxt = nonblank[k + 1] if k + 1 < len(nonblank) else None
            has_children = nxt is not None and BULLET_RE.match(lines[nxt]) and indent_of(lines[nxt]) > ind
            if parent is not None and ind <= parent_indent:
                parent, parent_indent = None, -1
            if has_children:  # '1. simulation' with nested bullets is a group, not an item
                parent, parent_indent = _clean(body), ind
                continue
            name, desc = _split_name_desc(body)
            rows.append({"name": name, "desc": desc, "group": parent or heading})
            continue
        if t.endswith(":"):
            continue  # 'Ideas:', 'also check these:' — sub-headers
        if is_plain_short(raw):
            prev_ok = k > 0 and is_plain_short(lines[nonblank[k - 1]])
            next_ok = k + 1 < len(nonblank) and is_plain_short(lines[nonblank[k + 1]])
            if prev_ok or next_ok:  # a run of bare short lines is a list
                rows.append({"name": _clean(t), "desc": "", "group": heading})
            continue
        notes.setdefault(group or "_", []).append(_clean(t))
    return [r for r in rows if r["name"]], links, notes


def read_list(path: Path) -> tuple[list[dict], list[tuple[str, str]], dict]:
    """Parse a list file: .md/.txt (structured markdown), .csv (name[,description]) or
    .json (list of str or {name, description, group})."""
    text = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()
    if suffix == ".json":
        rows = []
        for d in json.loads(text):
            if isinstance(d, str):
                n, ds = _split_name_desc(d)
                rows.append({"name": n, "desc": ds, "group": ""})
            else:
                rows.append({"name": _clean(str(d.get("name") or d.get("title"))),
                             "desc": str(d.get("description") or d.get("desc") or ""),
                             "group": str(d.get("group") or "")})
        return rows, [], {}
    if suffix == ".csv":
        rows = []
        for i, r in enumerate(csv.reader(text.splitlines())):
            if not r or not r[0].strip():
                continue
            if i == 0 and r[0].strip().lower() in ("name", "topic", "tech", "technology", "title"):
                continue
            rows.append({"name": _clean(r[0]), "desc": ",".join(r[1:]).strip(), "group": ""})
        return rows, [], {}
    has_structure = any(BULLET_RE.match(l) or l.lstrip().startswith(("|", "#"))
                        and not l.lstrip().startswith("# ") for l in text.splitlines())
    if suffix == ".txt" or not has_structure:
        rows = []
        for raw in text.splitlines():
            line = raw.strip()
            if line and not line.startswith("#"):
                n, ds = _split_name_desc(line)
                rows.append({"name": n, "desc": ds, "group": ""})
        return rows, [], {}
    return parse_markdown(text)


def ingest(topics_path: Path, tech_path: Path) -> dict:
    """Merge both lists into items (deduplicated by normalised name; groups accumulate)."""
    items: dict[str, dict] = {}
    links, notes = [], {}
    for kind, path in (("topic", topics_path), ("tech", tech_path)):
        rows, lk, nt = read_list(path)
        notes[kind] = nt
        for row in rows:
            iid = f"{kind}:{slug(row['name'])}"
            it = items.setdefault(iid, {"id": iid, "kind": kind, "name": row["name"], "desc": "", "groups": []})
            if row["desc"] and not it["desc"]:
                it["desc"] = row["desc"]
            if row.get("group") and row["group"] not in it["groups"]:
                it["groups"].append(row["group"])
        for a, b in lk:
            pair = []
            for name in (a, b):
                iid = f"{kind}:{slug(name)}"
                items.setdefault(iid, {"id": iid, "kind": kind, "name": name, "desc": "",
                                       "groups": ["user-flagged connections"]})
                pair.append(iid)
            links.append(pair)
    return {"items": list(items.values()), "links": links, "notes": notes}


def load(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save(path: Path, data) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_jsonl(path: Path) -> list[dict]:
    out = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def save_jsonl(path: Path, rows: list[dict]) -> None:
    Path(path).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
                          encoding="utf-8")


def item_text(item: dict, card: dict | None = None) -> str:
    """Text used for embedding an item: name, description, and the card's plain-language fields."""
    parts = [item["name"], item.get("desc", "")] + item.get("groups", [])[:1]
    if card:
        parts += [card.get("plain", ""), card.get("pain", ""), card.get("who", "")]
    return ". ".join(p for p in parts if p)

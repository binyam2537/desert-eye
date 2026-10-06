# Stage 1 — Problem cards, capability cards, bridges

Input: `runs/<run>/items.json` (every topic and tech, with optional description and the
heading/group it came from), `runs/<run>/notes.json` (context sentences found in the
lists) and `data/brief.md`.
Output: `runs/<run>/cards.json`, validated by `python -m ideaforge check --run runs/<run>`.

The two lists rarely mention each other, so the link between them has to be made
explicit. We do that through **bridges**: plain-language capabilities that a topic
*needs* and a technology *provides*. Bridges are the most important thing in this
file — they decide which pairings the miner can find.

## 1. Bridges (do these first, looking at BOTH lists together)

Write 15–40 bridges (≈ 1 per 4 items, more for long lists). Each bridge:

- is a **human outcome phrased as a verb phrase a 12-year-old understands**:
  "Notice problems hidden from view", "See trouble before it happens",
  "Try changes safely before doing them", "Work where there is no internet or expert",
  "Prove something happened without a middleman". Never a tech word
  ("computer vision", "IoT", "ML") and never a sector ("healthcare").
- should plausibly connect **at least 2 topics and 2 technologies**; a bridge that only
  one item touches is too specific — merge it.
- does not overlap heavily with another bridge.

Then id them `b_<short_snake_name>`.

## 2. One card per item

Topic card (the topic as a *problem people feel*):

```json
"topic:<slug>": {
  "plain": "one sentence a non-technical person would nod at, naming the pain",
  "who": "who suffers, concretely (not 'stakeholders')",
  "scale": "how many people / how much money or time — order of magnitude is fine, mark guesses with ~",
  "pain": "what it costs them: time, money, health, safety, dignity",
  "links": [{"bridge": "b_x", "w": 0.9, "why": "short reason this problem needs that capability"}]
}
```

If a topic is abstract ("sustainability", "education"), restate it as the most
widely felt concrete problem inside it, and say so in `plain`.

Tech card (the tech as *what it newly lets people do*):

```json
"tech:<slug>": {
  "plain": "what it lets you do that you couldn't cheaply do before — no jargon",
  "maturity": "lab | emerging | ready | commodity",
  "links": [{"bridge": "b_x", "w": 0.8, "why": "short reason it provides that capability"}]
}
```

## Unknown names — look them up, never guess

Tool and product names (e.g. *Jev*, *Laya*, *MiroFish*, *OpenClaw*, *Hermes Agent*) may be
newer than your training data. Web-search any you can't describe with confidence before
writing its card. Note what you found in `plain`.

## Clean-up keys (optional, top level of cards.json)

- `"aliases": {"tech:gaussian-splatting": "tech:3d-gaussian-splatting"}` — fold
  near-duplicates the normaliser missed into one item. Aliased items get no card.
- `"drop": ["topic:car", "topic:taxi"]` — entries that aren't really topics/techs
  (e.g. a list of road users under a heading). Dropped items get no card.

## Topic context

Topics in this project are RTA problem areas. Write `who`/`scale`/`pain` for **Dubai**
where you can (residents, commuters, tourists, outdoor workers, taxi drivers…).

## Weights (`w`, 0–1]

- 0.9–1.0 core: this need/capability *defines* the item
- 0.6–0.8 strong and direct
- 0.3–0.5 real but secondary
- don't link below 0.3; leave it out instead

Give each item 2–5 links. Be honest: a generic technology ("AI") should not get 0.9 on
everything — over-linking makes every pairing look relevant and kills the signal.

## Scale

For long lists, split the items into batches of ~40 and fill cards in parallel
sub-agents, but write the bridge list once, first, and give every batch the same list.
Item ids must match `items.json` exactly.

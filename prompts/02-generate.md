# Stage 2 — Generate ideas from seeds

Input: a batch of seeds from `runs/<run>/seeds.md` (or `seeds.json`).
Output: lines appended to `runs/<run>/ideas.jsonl`.

Read `data/brief.md` (plus every file in `data/private/` and `runs/<run>/addendum.md` if they exist — they are confidential and take precedence) first — audience, constraints and what wins.

## Who these ideas are for

They will be pitched to **non-technical people** (investors, officials, judges, the
public). An idea wins if, on first hearing, a smart non-expert says *"that could
actually change things"* — not *"that's technically interesting."*

## Ambition charter (read before every batch)

> Your first few ideas will be the obvious ones. Treat them as warm-up: keep one only if
> it still earns its place after you have the non-obvious ones. If an idea would appear in
> a generic "10 ways AI can help X" listicle, sharpen it or drop it. Anchor every idea in
> the seed's problem, people and bridge — not in the technology.

## How to work each seed

1. **Start from the problem, not the tech.** Re-read the seed's *who*, *pain* and *scale*.
   Picture it through the seed's **"Think as"** persona: what does this problem look like
   on their worst day?
2. **Use the seed's reason for existing.**
   - `anchor`: the fit is obvious — your job is an unusually *big* or *simple* version.
   - `serendipity`: relevant but rarely paired — explain the surprising link in one line.
   - `analogy`: borrow how the tech already helps the *source topic*, transfer the mechanism.
   - `combo`: the idea must need **both** technologies; each covers a different need.
   - `wildcard`: be bold; drop it if no honest idea exists.
3. **Push through these lenses** (pick the 2–3 that fit; they are starting biases):
   pain & friction · remove/invert/automate a step · break an assumption everyone treats as
   fixed · leverage (one thing that makes many future things cheaper) · cross-domain analogy
   (how does biology / logistics / games / another industry already solve this shape of
   problem?) · flip a constraint (10× cheaper, zero staff, a million users, works offline).
4. Write **1–3 ideas per seed**, each substantially different. Zero is fine.

## Pitch structure (every idea must fit it)

**Big recognisable problem → simple powerful concept → technology quietly makes it
possible → clear, measurable impact.**

## Reject before writing

- an existing product + one AI feature / dashboard / sensor / app / chatbot
- anything whose value needs technical knowledge to appreciate
- "platform", "ecosystem", "leveraging", "AI-powered", "blockchain-based" as the concept
- niche users only (a few hundred specialists) unless the outcome is dramatic
- a better version of something that already works fine for most people

## Output — one JSON object per line in `ideas.jsonl`

```json
{"id": "I001", "seed_id": "S007", "lens": "flip a constraint",
 "title": "3–6 words, memorable, no jargon",
 "one_liner": "≤ 25 words a 12-year-old gets: what it is and why it matters",
 "problem": "who suffers, how much, why today's fix fails (2 sentences)",
 "concept": "what it does, described as the user experiences it (2–3 sentences)",
 "how_tech_enables": "why this is possible *now* and wasn't 5 years ago (1–2 sentences)",
 "impact": "one concrete number or before/after (mark estimates with ~)",
 "who_benefits": "the people, not the buyer persona",
 "first_demo": "the 2-minute *simulated* demo that would make the room gasp",
 "phases": "Phase 1 simulation demo → Phase 2 pilot (hardware if any) → Phase 3 city-wide"}
```

Ids: continue numbering from the last id in the file. With parallel sub-agents give
each a prefix (`A001`, `B001`, …) to avoid clashes.

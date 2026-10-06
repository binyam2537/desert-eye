# Stage 3 — Critique: kill, reframe, or keep

Input: `runs/<run>/ideas.dedup.jsonl`.
Output: one line per idea in `runs/<run>/critique.jsonl`; then
`python -m ideaforge survivors --run runs/<run>`.

Read `data/brief.md` first. Be a harsh, fair critic. Expect to kill **half or more**. A smaller set of strong ideas
beats a long list. Judge the idea, not the writing — but see *reframe* below.

## Gates (all must be `true` to survive)

| gate | passes when |
|---|---|
| `ten_second` | A non-technical person understands the problem **and** why the idea matters within 10 seconds of the one-liner. |
| `matters` | The problem affects many people, or costs serious money/time/health, or is a recognised societal/business pain. |
| `not_incremental` | It changes the outcome, not just the efficiency; not "existing thing + AI/dashboard/sensor/app". |
| `tech_is_enabler` | The technology makes it possible; the idea is not "use technology X". Swap the tech name for "magic" — is it still exciting? |
| `broad` | Could reach a city, an industry, or a large group — or the impact on a smaller group is dramatic (life, safety, livelihood). |
| `plausible` | A small team can show it convincingly **in simulation / software** within the competition timeline (see `data/brief.md`); hardware only in later phases; no physics-defying steps. |
| `not_already_done` | No well-known product already does essentially this at scale. **Search the web** for finalists (see below). |

## Prior-art check

For every idea that passes the first six gates, run 1–2 web searches
(`WebSearch`, or the **agent-reach** skill's Exa search) for the idea's core mechanism.
Record the closest thing you find in `prior_art`. If something nearly identical already
exists at scale, `not_already_done` is false — unless the idea is clearly 10× cheaper,
broader, or different in who it serves, in which case say that.

## Reframe instead of killing

If an idea is genuinely strong but **pitched too technically or too narrowly**, keep the
gates honest for the *reframed* version and put the fixed fields in `rewrite`. Only
`title`, `one_liner`, `problem`, `concept`, `impact` may be rewritten. Don't use this to
rescue a weak idea.

## Output line

```json
{"id": "I007",
 "gates": {"ten_second": true, "matters": true, "not_incremental": true, "tech_is_enabler": true,
           "broad": true, "plausible": true, "not_already_done": true},
 "kill_reason": "one sentence if any gate is false, else empty",
 "prior_art": "closest existing product/project (with URL) and how this differs",
 "biggest_risk": "the one assumption that would kill it if wrong",
 "rewrite": {"one_liner": "optional plain-language reframe"}}
```

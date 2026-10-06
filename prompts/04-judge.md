# Stage 4 — Tournament judging

Input: `runs/<run>/matches-r<N>.json` (written by `python -m ideaforge pair`).
Output: the same file with `winner` (`"A"`, `"B"` or `"tie"`) and `reason` filled in on
every row; then `python -m ideaforge record --run runs/<run> --round <N>`.

Read `runs/<run>/addendum.md` first if it exists (confidential challenge context).

Each match appears twice with A and B swapped. Judge each row **independently** — don't
look at the other order's verdict. The scorer turns a split verdict into a draw, which
cancels any bias towards whichever idea is shown first.

## How to judge a row

You are the row's `judge` (e.g. *Investor*, *City official*, *Journalist*, *Everyday
user*). Read only `A_pitch` and `B_pitch` — exactly what that person would hear in a
pitch. Apply the judge's `lens`, then ask, in order:

1. Which problem would this person care about more, instantly?
2. Which idea do they understand faster and could repeat to a friend?
3. Which one would make them say "that could actually change things"?
4. Which is more believable as something real people could build and use?

Pick the winner on **first-impression impact for this audience**. Technical
cleverness and novelty for experts do **not** count. Prefer `"tie"` only when you
truly can't separate them.

`reason`: one sentence, in the judge's voice.

## Efficiency

Rows can be judged in parallel sub-agents (e.g. one per judge). Keep every row's
`match`, `order`, `A`, `B` untouched.

## How many rounds

Run `ceil(log2(survivors)) + 2` rounds (about 6 for 20–40 ideas). After round 3 you may
do one **evolve** pass (see `05-evolve.md`) and continue the remaining rounds with the
new entrants.

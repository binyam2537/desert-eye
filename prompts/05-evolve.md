# Stage 5 — Evolve the leaders (optional, after tournament round 3)

Input: current top ~8 by rating (`runs/<run>/tournament.json` + `survivors.jsonl`) and
the judges' `reason`s from the match files.
Output: 3–8 new ideas appended to `ideas.jsonl` with ids `E001…`, each with
`"parents": ["I012", "I031"]`.

Moves (use what the judges' reasons point to):

- **Combine** two leaders that solve halves of the same problem into one stronger idea.
- **Simplify** a leader to the one feature that made judges pick it.
- **Scale up** a leader's scope from one building to a city, from one crop to every farm.
- **Borrow** the hook of a high-rated idea (its first-demo moment, its framing) for a
  leader with a weaker story.

Then: `python -m ideaforge dedupe`, critique **only** the new ideas (append to
`critique.jsonl`), `python -m ideaforge survivors`, and continue with `pair`. New
survivors join the running tournament at the median rating.

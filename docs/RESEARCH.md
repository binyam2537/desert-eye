# How the pipeline was chosen

Inputs reviewed: three earlier AI chats (two on "graph vs RAG vs vectors", one on making
ideas impressive to non-technical judges), four GitHub repos, the skills.sh registry,
and the research papers the chats cited (each checked to confirm it exists and says
what the chat claimed).

## Verdict on the chats' suggestions

| Suggestion | Verdict | Why |
|---|---|---|
| Obsidian-style graph | ✗ as the engine, ✓ for viewing | Both chats were right: it only shows links you already wrote. We output `graph.html` for exploring instead. |
| Plain RAG | ✗ | Retrieval isn't the bottleneck. With two lists there is nothing to retrieve. |
| Plain vector similarity | ✗ alone, ✓ as one signal | Nearest neighbours = the most *obvious* pairings, which give predictable ideas. We use the semantic distance as a **surprise** signal, not a relevance one. |
| Bipartite / tripartite graph with "bridge concepts" (chat 2) | ✓ **core of the design** | The lists never mention each other. Bridges (plain-language capabilities a topic *needs* and a tech *provides*) make the link explicit and explainable. They are also pitch-friendly: "see trouble before it happens" beats "predictive analytics". |
| Relevance × Novelty × Surprise score (SerenQA) | ✓ | Real paper (AAAI 2026). Relevance comes from bridges, surprise from embedding distance, novelty penalises generic "AI fits everything" techs. |
| Analogical transfer (SMAR / NIE-style) | ✓ simplified | "Tech X fits topic A; topic B has the same needs but looks unrelated → try X on B." Cheap to compute on the graph. |
| Multi-hop diverse paths (K-Paths) | ✓ for explanations | Real paper (2025). Used to show *how* a topic reaches a tech, not to pick seeds. |
| Cross-cluster combos | ✓ | Topic + two techs from different clusters that cover *different* needs. |
| GraphRAG (Microsoft) | ✗ | Built for summarising big document collections. Overkill for two lists. Revisit if we add research papers. |
| Graph2Idea / GoAI | ✗ to adopt, ✓ the idea | Real papers. Built around paper-citation graphs. The useful part (feed the LLM compact graph context, not raw text) is what `seeds.md` does. |
| Iterative generate → critique → mutate (ResearchAgent, AI co-scientist) | ✓ | Implemented as critique gates + Elo tournament + an optional evolve step. |
| "Generate 30, kill hard, show 5" + "wow separate from novelty" (chat 3) | ✓ **most important single change** | Encoded as the generation charter, the 7 critique gates, and a non-technical judge panel. |

## What the research adds that the chats missed

1. **LLMs repeat themselves.** In the largest human study of LLM research ideas
   (Si, Yang & Hashimoto, ICLR 2025, 100+ NLP researchers) the LLM ideas were rated
   *more novel* than experts' ideas, but generation collapsed into duplicates and LLM
   self-ranking agreed poorly with humans. → We dedupe with embeddings, and we never ask
   for 1–10 scores.
2. **Random ordinary personas restore diversity.** Studies on LLM idea homogeneity
   (e.g. *Examining and Addressing Barriers to Diversity in LLM-Generated Ideas*, and
   Terwiesch/Mollick et al. 2026) find everyday personas beat "creative expert" prompts
   and chain-of-thought alone. → Each seed gets a random everyday persona.
3. **Pairwise beats absolute.** Google's AI co-scientist ranks hypotheses with an Elo
   tournament of pairwise debates. → Swiss-system Elo, every match judged twice with
   A/B swapped so position bias cancels out.
4. **Grounding + explicit rejection.** The `ce-ideate` skill (Every's compound-engineering
   plugin) requires a stated basis for each idea and an explicit, reasoned rejection
   pass. It also uses six lenses (pain, inversion, assumption-breaking, leverage,
   cross-domain analogy, constraint-flipping). → Borrowed into `prompts/02` and `03`.

## Repos reviewed

| Repo | What it is | Decision |
|---|---|---|
| [Panniantong/agent-reach](https://github.com/Panniantong/agent-reach) | Gives agents internet access: Exa search, web reader, YouTube, GitHub, Reddit/X (with login) and more, through one routing skill. | **Installed the skill** (`.claude/skills/agent-reach`). Used for prior-art checks and to look up unfamiliar tool names. To use the CLI on your machine: `pipx install https://github.com/Panniantong/agent-reach/archive/main.zip && agent-reach install` (read-only check first; `--system` only when you approve). |
| [naibowang/easyspider](https://github.com/NaiboWang/EasySpider) | A visual, point-and-click desktop web scraper (Electron GUI). | **Not used.** It's a GUI for humans and has no agent skill. Nothing in this workflow needs bulk scraping; agent-reach + web search cover lookups. |
| [obra/superpowers → brainstorming](https://github.com/obra/superpowers/tree/main/skills/brainstorming) | A gate for *software design*: classify the task, ask questions, write a spec, get approval, then plan. Its description says "MUST use before any creative work". | **Not installed.** It turns creative tasks into spec-writing and would hijack every ideation run in this repo. Its useful habits (one question at a time, propose 2–3 options) are in the installed `product-brainstorming` and `grilling` skills. Install anyway with `npx skills add obra/superpowers --skill brainstorming -a claude-code`. |
| [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify) | Turns a *codebase / doc folder* into a knowledge graph (tree-sitter for code, LLM for docs), Leiden communities, "surprising connections". | **Not used for now.** It's built for corpora of files. It deliberately avoids embeddings, and it has no idea of "needs vs provides". Two lists need a purpose-built graph (~300 lines of NetworkX). Its best ideas (communities, cross-community surprises, every edge carries a reason) are reproduced here. **Use it later** if you add a folder of RTA reports or papers, then merge its concepts in as extra items. |

Better options than graphify for this job: **NetworkX + local embeddings** (chosen: no
server, no API key). Neo4j/LightRAG/GraphRAG only pay off with large text corpora.

## Skills installed from skills.sh (project scope, `.claude/skills/`)

| Skill | Source | Why |
|---|---|---|
| `agent-reach` | Panniantong/agent-reach | Web/social research, prior-art checks |
| `product-brainstorming` | anthropics/knowledge-work-plugins | HMW, JTBD, assumption testing, reverse brainstorming for live sessions on one problem |
| `grilling` | mattpocock/skills | Stress-test a finalist before pitching |
| `idea-forge` | this repo | The pipeline itself |

Considered and skipped: `ce-ideate` (excellent method, but depends on its plugin's
other agents; its frames and rules were borrowed instead), `mattpocock/research`
(code-docs research), `grill-me` (just a wrapper around `grilling`).

## Sources

- Si, Yang, Hashimoto — Can LLMs Generate Novel Research Ideas? https://arxiv.org/abs/2409.04109
- SerenQA — Assessing LLMs for Serendipity Discovery in KGs https://arxiv.org/abs/2511.12472
- K-Paths https://arxiv.org/abs/2502.13344
- Graph2Idea https://arxiv.org/abs/2606.09105
- GoAI https://arxiv.org/abs/2503.08549
- Google AI co-scientist https://arxiv.org/abs/2502.18864
- LLMs can Realize Combinatorial Creativity https://arxiv.org/abs/2412.14141
- AI and its impact on creativity and diversity (LLM product ideas) https://arxiv.org/abs/2607.27553
- Barriers to diversity in LLM-generated ideas https://www.researchgate.net/publication/401178492
- Using GenAI personas increases collective diversity https://arxiv.org/abs/2504.13868
- Jev / Laya decision models https://runware.ai/blog/jev-laya-and-the-emerging-role-of-decision-models
- MiroFish https://github.com/666ghj/MiroFish

# Knowledge-gap probe: report (2026-11-01)

**Question.** Are there docs lookups that take more than one fetch, often enough for breadcrumbs to pay? And can we tell without asking developers to run a script?

**Answer: no, not for library docs lookups in coding work.** Lookups that take several fetches are common when an agent checks a library fact: two thirds of its lookups. But breadcrumbs don't make them cheaper:

- **The current policy makes them dearer:** miss-0.5, the best write policy so far, comes out at +22% tokens (token-weighted).
- **What's in the registry saves almost nothing on a related question:** −3%.
- **Even a perfect breadcrumb misses the 30% bar:** handing the agent the exact source URL saves 12%.

Two field samples also show that web lookups are a small part of a session's work. The plan's decision rule ([PLAN.md](../docs/PLAN.md#short-term-execution-plan)) puts library docs in the "no win" column. What's left is the narrow case earlier experiments did show: access knowledge for sites that are hard to reach.

Raw data: `experiment/out_probe-0.1/` (local, like other `out_*` folders). Tables: `out_probe-0.1/report.md`, regenerated with `python out_probe-0.1/report.py`.

## 1. How we got here

1. **Field data, one developer** (`experiment/LOG.md`, 2026-11-01):
   - 835 transcripts, 46 web calls, 18-19 lookups, 47-50% of lookups a single call.
   - Mostly one large codebase with vendored dependencies.
   - Too small, and too narrow, to answer the question.
2. **A plan to estimate demand without developers.** It started as a "knowledge-gap probe": ask the model versioned API questions from memory and check the answers.
3. **Redesign.** On review, the memory-only probe measured the wrong thing:
   - Questions about post-cutoff changes are wrong by construction.
   - Drawing evenly from the API reference ignores usage.
   - A confident wrong answer means the agent never looks anything up, so breadcrumbs can't help it.

   The redesign measures demand directly. The agent gets web tools and decides for itself whether to look up. We record whether it did, how many calls the lookup took, and what breadcrumbs save on those lookups.
4. **This run (probe-0.1).** Six arms on 72 questions, two reps of the breadcrumb comparison, read-only and same-question ceilings, and an oracle arm.
5. **Second field sample:** aggregate counts from this machine's own transcripts.

## 2. Questions (research/probe/questions.yaml)

- **72 questions, 12 libraries, 6 groups.** fast frontend (vite, astro), AI SDKs (anthropic, openai), stable (requests, express), Python data/web (pydantic, fastapi), cloud SDKs (stripe, google-cloud-storage), niche (cachekit, @embrace-io/web-sdk).
  - The niche pair came from `research/scripts/pickniche.py`: 2k-50k weekly downloads, first release 2024-06 to 2026-06, seeded draw, hand-checked.
  - google-cloud-storage replaced boto3, whose API is generated from service models.
- **Every question names a version.** Every answer is checked by `run.py verify` against a file pinned to a release tag.
- **Each library has 3 `random` and 3 `changed` questions.**
  - random: drawn with seed 1 from the documented API.
  - changed: drawn from changelog entries since 2025-06 (12 months before Sonnet 5.5's Jun 2026 cutoff), each with `changed_in` release and date.
- **Skips are written into the file:** internals, experimental/beta/admin APIs, and entries too vague for a one-line question.

## 3. Arms (all Sonnet 5.5, `--iteration miss-0.5`)

| Arm | What it measures |
|---|---|
| memory | No tools: what the model knows (answer, confidence or UNSURE) |
| open | Web tools, no registry, no rule to look up: does the agent look up on its own, and how many calls does it take? |
| cold-nowrite (+ -related) | Forced lookup, no registry: the cost of a lookup when one happens |
| cold → warm-related | miss-0.5 as used: a cold agent writes, a warm agent answers a related question about the same library (pairs: questions 1→2, 3→4, 5→6 of each library) |
| warm-related-nowrite | The same with no warm writing: the value of the registry's contents alone |
| warm-same | The same question again: a ceiling for breadcrumbs |
| oracle | The question plus its ground-truth source URL: a perfect breadcrumb |

There were 576 scored runs: 504 in the main arms (two reps of the breadcrumb comparison) and 72 oracle runs.
- **Wrong answers:** 6 in the web arms (open 1, cold 1, cold-nowrite-related 2, warm-related 1, warm-same 1), and none in the oracle.
- **Usage limit:** the 5-hour limit hit twice. Two warm-related runs waited about two hours for the reset and then went through. The first oracle pass all hit the limit and was rerun after the reset. Rows from runs that hit the limit are left out.

## 4. Results

### What the model knows

| Sample | Right | Wrong, high confidence | Unsure |
|---|---|---|---|
| random (36) | 64% | 0% | 36% |
| changed before the cutoff (25) | 32% | 0% | 68% |
| changed after the cutoff (11) | 0% | 18% | 82% |

The model is well calibrated: it says UNSURE rather than guess. It was wrong with high confidence twice, both on Express 5.3, which shipped after the cutoff.

### Does the agent look things up on its own? (open)

| Sample | Looked up | Correct | Web calls per lookup |
|---|---|---|---|
| random | 56% | 100% | 2.1 |
| changed before the cutoff | 84% | 100% | 2.6 |
| changed after the cutoff | 91% | 91% | 3.0 |
| all 72 | 71% | 99% | 2.5 |

- **It looks up when it should:** 95% of the questions it was unsure about from memory, and 42% of those it knew.
- **Only once did it answer wrong without looking.** That was Express 5.3 `req.fresh`, where it answered "GET and HEAD only", from memory and with confidence.
- **Lookups took 1 call in 33% of cases, 2 in 29%, 3 in 20%, and 4+ in 18%.** That's two thirds with 2 or more calls, against about half in the field data. These questions name a version, which pushes agents towards pinned sources and searches.

### What a lookup costs (forced, rep 1)

- **74% of lookups took 2+ web calls.** Median 29k tokens total, 15k uncached.
- **Post-cutoff questions cost the most:** 64% took 4+ calls, median 56k.
- **By library:** vite was cheapest (1.2 calls), cachekit and express the dearest (4.2 and 4.5).

### What breadcrumbs save (miss-0.5, two reps, matched by rep)

| Arm | n | Median Δ | Token-weighted Δ |
|---|---|---|---|
| warm-related (realistic: warm agents also write) | 72 | +9% | **+22%** |
| … when that rep's cold run stored a record | 24 | +2% | +7% |
| … when it stored nothing | 48 | +22% | +27% |
| warm-related-nowrite (registry contents only) | 72 | −0% | **−3%** |
| … when cold stored a record | 24 | −8% | −2% |
| warm-same (same question), cold stored a record | 10 | −37% | **−20%** |
| warm-same, all | 36 | +8% | +17% |
| oracle (source URL handed over) | 72 | −22% | **−12%** |

On multi-call questions the oracle's median saving rises to −35%, but its mean is −10%.

### Why breadcrumbs don't help here

1. **Most cold runs can't store a card.** In rep 1:
   - 20 of 36 cold runs got the answer with one fetch, where a card is refused by design.
   - 5 took several fetches but under 2,000 tokens.
   - 10 of the 11 eligible runs stored a card, so the policy is followed.

   Rep 2 stored in 14 of 36.
2. **What gets stored doesn't transfer.** Every stored record was a page card, filed under whatever page the cold agent happened to land on: a GitHub repo, PyPI, readthedocs, a docs page. None was a site record, because docs sites need no access tricks. The warm agent's related question usually needs another page and starts from another URL, so its lookup misses. The misses read "no card for page:github.com/openai/openai-python", "no breadcrumbs for docs.anthropic.com".
3. **When a lookup misses, warm agents pay for the miss note and for writing.** That's the +27% on pairs where cold stored nothing. In a shared registry those writes would be spread over later readers. But reading alone is worth −3%, so there's little to recover.
4. **Even a perfect route saves little.** A docs lookup's cost is mostly fixed agent overhead plus the content itself, not wrong turns. Knowing the exact source cut web calls from 2.8 to 2.0 on average. But the true source is often a whole module file (stripe's `Sessions.ts`, pydantic's `main.py`), bigger than the docs page agents would otherwise read. Hence the oracle's mean of +26%, against a median of −22%.

### How much of a session lookups are (field data)

| | Developer (Loom) | This machine |
|---|---|---|
| Transcripts | 835 | 63 |
| Sessions with any web call | 9 projects of many | 18 (29%) |
| Web calls / lookups (GAP=3) | 46 / 18 | 203 / 44 |
| Single-call lookups | 47-50% | 41-46% |
| Web result tokens | - | 117k: 8.3% of tool-result tokens, against 595M session tokens counting cached reads |

`research/scripts/lookups_local.py` counts as the developer's script does, plus tokens, and prints aggregates only. This machine's sessions are mostly this research project, which uses the web far more than ordinary coding does.

Even at the oracle's 12%, a saving on lookups is 12% of a sliver of each session.

## 5. Caveats

- **Q&A framing, not coding tasks.** Each question names a version, which encourages lookups (71% looked up). In real work agents rarely ask such pointed questions, so real lookup rates are lower. That makes the "small volume" half of the answer stronger, not weaker.
- **Two reps.** Single runs vary by about ±25%. The read-only result (−3% across 72 comparisons) is within about ±6% of zero. The same-question ceiling has n=10.
- **One model (Sonnet 5.5), one write policy (miss-0.5).** A policy built for docs could:
  - file cards under the library, not the landing page;
  - write site records with raw-source URL patterns, such as `raw.githubusercontent.com/<repo>/<tag>/...`.

  The oracle caps what any route-only breadcrumb can save at about 12% token-weighted on this workload. A card that also gave a `section` or `select` could beat the oracle on the large-file cases, but that is closer to caching content (L2) than to routes.
- **The question selection is my judgment** within seeded draws. Skips are listed in `questions.yaml`.
- **12 libraries, Python and JS only.**

## 6. What this means for the plan

- **Library docs for coding agents: no win.** Stop treating breadcrumbs as a general token-saving layer for coding agents.
- **Earlier experiments found a narrower win:** multi-fetch hard tasks, −27% to −32% under miss-0.4. That was access knowledge for sites that need JavaScript, block fetches, or have a better API. That's the plan's "narrow the product" branch. Its demand is untested. The next measurement would be how often agents in real sessions hit sites that are JavaScript-only or blocked. The field script could count fetches that return near-empty or error pages, per transcript, without content.
- **A by-product finding:** confidently wrong answers on post-cutoff API changes are real but rare. It happened once in 72 open runs. Breadcrumbs can't fix them, since the agent never looks up.

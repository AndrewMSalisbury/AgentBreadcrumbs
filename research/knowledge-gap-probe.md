# Knowledge-gap probe (sketch)

Estimates where a docs lookup would change an agent's answer, without asking developers for data. It measures need, not actual lookups: how often the model's remembered API is wrong, by library. Proposed after the 2026-11-01 field data (`experiment/LOG.md`), which showed web lookups are rare in one developer's work but couldn't say whether other projects need them more.

## Questions it answers

1. **How often is the model wrong about library APIs without the web,** overall and by library?
2. **Which libraries are worst,** and does release cadence, release date (relative to the model's cutoff) or popularity predict that?
3. **When a lookup is needed, how many fetches does it take?** This is the bridge to the viability bar: breadcrumbs only save on multi-fetch lookups, and the field data had 50% one-fetch.

## Libraries

About 36, stratified so each group can be read on its own. Six per group:

| Group | Why | Candidates |
|---|---|---|
| Fast-moving frontend | Frequent majors, big API churn | next, react-router, tailwindcss, vite, svelte, astro |
| AI / LLM SDKs | Change monthly, often after the cutoff | anthropic (py), openai (py), langchain, ai (Vercel), llama-index, mcp (py) |
| Stable, widely used | Control: model memory should be good | requests, express, lodash, numpy, flask, serde |
| Python data / web | Mid cadence, deprecation-heavy | pandas, pydantic, fastapi, sqlalchemy, polars, httpx |
| Infra and cloud SDKs | Large surface, integration-heavy | boto3, stripe (node), @aws-sdk/client-s3, kubernetes (py), google-cloud-storage, twilio |
| Niche / new | Little training data | picked from registry search: under ~50k weekly downloads, first release within 2 years of the cutoff, 6 across npm, PyPI and crates |

Per library, the script records from the registry API: current version, release date of each version asked about, releases in the last 12 months, and weekly downloads. Nothing is filled in by hand.

## Questions

Six per library, about 216 in all, always naming a version ("In pydantic 2.x, ..."), because agents in real projects need the installed version, not just the latest.

Two samples, kept apart in the report:

- **Random API sample (3 per library).** Pick symbols at random from the version's API reference or type stubs. This gives an unbiased error rate.
- **Changed API sample (3 per library).** Pick from the changelog or migration guide of releases since about 12 months before the cutoff: renames, removals, new parameters, changed defaults. This gives the worst case, and it overstates the rate on purpose.

Question types, mixed across both samples:

1. **Signature:** parameters of a named function or method, and their order or kind.
2. **Exists / deprecated:** does `X` exist in this version, and what replaced it?
3. **Default or config:** the default of an option or the name of a config key.
4. **Snippet:** a one-line call that does a stated thing (graded by regex on the call, not by running it).

Each question uses the `tasks.yaml` format (`question`, `expect` regexes, `check` with URL and pattern), so `run.py verify` re-checks the ground truth against the docs before a run. Questions are written from the docs first, then checked by hand. The model doesn't write its own questions.

## Arms

Reusing `experiment/run.py`, with a `--tasks` option for this question file:

- **memory:** the `memory` condition (no tools), with a prompt that allows `ANSWER: UNSURE` and asks for confidence (high/low). All 216 questions, 1 rep, Sonnet. Later reps or models only if the spread is interesting.
- **web:** `cold-nowrite` on the questions memory got wrong or unsure, 1 rep. It confirms a lookup fixes the answer and counts fetches and searches per question.

## Grading and output

Each memory answer is **right**, **wrong, high confidence**, **wrong, low confidence** or **unsure**. The costly class is wrong with high confidence: an agent that doesn't know it's wrong won't look anything up. Hand-review a sample of 20 regex grades.

Report:

- Error rate per group and per library, random and changed samples side by side.
- Error rate against months between the version's release and the cutoff, and against releases per year.
- From the web arm: fetches per fixed question (1 / 2 / 3+), compared with the field data's 50% one-fetch.

## Cost

Memory runs replace the system prompt and load no tools or MCP servers. A smoke run took 917 tokens and 3 seconds, so 216 runs are about 0.2M tokens. Web runs are probably 60-100 at about 20-40k each. Both fit in a few 5-hour windows on the Pro plan. Writing and checking the 216 questions is the main cost, not the runs.

## What would change the plan

- **Low error on random API questions (under ~5% wrong with high confidence) outside new and AI libraries:** demand for docs lookups is narrow. Aim breadcrumbs at the worst groups and their sites, and add hard tasks from them.
- **High error on popular, fast-moving libraries, with fixes needing 2+ fetches:** that's where breadcrumbs could pay. Seed those sites, add them as hard tasks, and score the viability bar there.
- **High error but fixes are mostly one fetch:** need exists, but breadcrumbs can't save much. The single-fetch work (skipping or folding the lookup) becomes the priority.

## Limits

- Need isn't demand. A wrong memory answer only costs anything if an agent hits that API in real work and the error isn't caught by a test or type check.
- Questions written from changelogs are biased toward gaps; that's why the random sample is reported separately.
- One model, one cutoff. A newer model moves every "months since cutoff" number.
- The candidate list leans toward ecosystems we know. The niche group is drawn from registry search to offset that a little.

## Build steps

1. Done: `--tasks` option in `run.py`, and a `memory` condition (no tools or MCP servers, its own prompt allowing `UNSURE` and asking for confidence). Rows get `confidence`, `library`, `sample` and `outcome`. `related` is optional in a task file. `baseline` stays the empty overhead run.
2. Done: `research/scripts/libmeta.py` reads the hand-written list in `research/probe/libraries.yaml` and writes `research/probe/libmeta.yaml`. Per library it records the latest stable version, first and latest release, stable releases in the last 12 months, the first release of each major (each minor below 1.0), and weekly downloads. Release dates come from deps.dev; downloads from npm, pypistats and crates.io. Terraform's aws provider became `@aws-sdk/client-s3`, because deps.dev doesn't cover the Terraform registry. The niche group comes from `research/scripts/pickniche.py`. It keeps packages with 2k-50k weekly downloads whose first release falls in 2024-06 to 2026-06, and drops families of 4+ packages that share a name prefix. The picks are the first 2 per ecosystem in seeded order that pass the hand check; `libraries.yaml` lists the rejects and why.

The cutoff is Sonnet 5.5's reliable knowledge cutoff and training data cutoff, both Jun 2026 (Anthropic's models overview, checked 2026-11-01). The probe runs `--model sonnet`, which ran `claude-sonnet-5-5` in the smoke run.
3. `research/probe/questions.yaml`: 6 questions per library in `tasks.yaml` format, verified with `run.py verify`.
4. A smoke run on 2 libraries per group (72 questions) before the rest, to check grading and the prompt.
5. Report script: the tables above.

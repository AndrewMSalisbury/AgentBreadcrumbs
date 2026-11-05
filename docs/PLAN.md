# Agent Breadcrumbs Plan

*Mirror of the shareable plan doc: [Agent Breadcrumbs Plan](https://claude.ai/artifact/4NE5HAUh1WMnhhWoNZzNrP). The doc is the source of truth; this copy was exported on 2026-10-26.*

Agents that read a web page leave a short, structured breadcrumb in a central registry, so the next agent can skip the searching, wrong turns and failed fetches. This plan covers the standard, how it is tested, and the path to a working registry. The immediate next step is a small experiment proving breadcrumbs make getting site data measurably cheaper.

## Problem and idea

Every agent that answers a question from the web repeats the same discovery work: searching, fetching wrong pages, parsing noisy HTML and fighting JavaScript-only sites. A breadcrumb records what one agent learned — where the answer is, how to get it, what it says, and the route there — so the next agent starts from that instead of from zero.

Measured on 2026-10-21 (o200k_base tokenizer, an approximation of Claude's). Static pages, content in the HTML:

| Page | Raw HTML (tokens) | Cleaned Markdown (tokens) | Breadcrumb (tokens) |
| --- | --- | --- | --- |
| Stripe docs: rate limits | 276,169 | 2,735 | 153 |
| GitHub: Firecrawl repo | 233,454 | 5,581 | 105 |
| Wikipedia: Web crawler | 106,709 | 17,965 | 120 |
| MDN: HTTP 429 | 56,738 | 565 | 98 |
| Python docs: json | 32,576 | 8,031 | 128 |
| llmstxt.org | 13,199 | 2,640 | 78 |
| **Total** | **718,845** | **37,517** | **682** |

JavaScript-heavy pages:

| Page | Plain fetch, content (tokens) | Rendered raw → content (tokens) |
| --- | --- | --- |
| crates.io (serde) | 14 ("enable JavaScript") | 11,357 → 535 |
| Spotify (artist) | 0 | 288,729 → 946 |
| Uniswap (tokens) | 11 ("enable JavaScript") | 278,651 → 1,214 |
| X (@AnthropicAI) | 289 (real content) | blocked |

What the numbers show:

- Raw HTML is 5–100× larger than the useful text; cleaning it is a code job, not an AI job.
- Having an AI rewrite pages costs about 5× more than reading them, because output tokens cost 4–5× input.
- Writing breadcrumbs for all six pages cost about 9% of reading them once.
- Plain fetches of JavaScript sites fail silently. Rendering takes about 15 seconds and up to 289k raw tokens.
- The crates.io API returned 142,782 tokens, of which the useful fields were 97. Knowing how to get the data is the biggest saving.

The breadcrumbs measured here were written by hand, not by an agent in a pipeline; the test plan below fixes that. Raw data and scripts: [`research/`](../research).

## Landscape

Nobody yet runs a public, agent-written registry of paths through websites; the nearest players cache content or curate data centrally.

| Project | What it does | How breadcrumbs differ |
| --- | --- | --- |
| [Firecrawl Alexandria](https://firecrawl.dev/howiai) | Curated, paid data library for agents; launched 2026-09-22 with a $75M Series B; in ChatGPT and Codex | Agent-contributed, path-level, long-tail, neutral; strongest company in the space and could add this |
| [llms.txt](https://llmstxt.org/) | Site-owner-written Markdown map of a site | Written by agents as they work and kept current by them |
| [Aicorn](https://www.claudepluginhub.com/plugins/telepenin-aicorn-plugin) | Claude Code plugin; shared cache so each page is converted once | Stores judgments and routes, not page copies |
| [agentsweb.org](https://chromewebstore.google.com/detail/bjdgnbanmhhlicnhclicblekglephipg) | People share pages as Markdown into a public cache | Automatic, and no content redistribution |
| [AnswersEngine Global Pages](https://answersengine.readthedocs.io/en/latest/fetch_doc.html) | Shared fetched-page cache for scraping customers | Open across providers, not one platform |
| [webnav](https://socket.dev/npm/package/@dikshanty94/webnav) | Per-user site maps for browsing agents | Shared between all agents |
| [Web Speed](https://aiindigo.com/tutorials/getting-started-with-web-speed-accelerate-ai-agent-web-navigation) | Described as a shared web-map registry; operator unverified | Closest concept; needs checking |

Lessons from Alexandria: free discovery with paid retrieval, distribution through MCP from day one, agreements with data owners, and a measured quality claim.

## Decisions so far

The shape of the standard is settled; scoring numbers wait for test data.

| Question | Decision | Status |
| --- | --- | --- |
| What breadcrumbs capture | Where things are, how to get it, what it says, task routes | Decided |
| Depth | Tiered levels; testing picks defaults | Decided |
| Unit | Site record plus per-URL page cards | Decided |
| Who writes | Any agent, with scoring | Decided |
| Where they live | Central registry | Decided |
| Storage format | JSON validated by JSON Schema | Proposed |
| Write format | JSON through an API or MCP tool call | Proposed |
| Read format | Compact YAML by default; JSON or Markdown on request | Proposed |
| Fingerprints | Computed by the registry | Proposed |
| Depth growth and L3 outline | Demand-driven depth; L3 for long or hard pages | Proposed |
| Core of the L1 card | A route (the cheapest way to get the page's content), not a section map | Decided: section maps failed the bar in map-0.1; route cards cleared it from route-0.1 |
| Scoring weights and decay | — | After testing |

## How it works

![Agent B skips the search Agent A paid for](img/how-it-works.png)

The first agent pays the full cost and leaves a breadcrumb; the registry validates, fingerprints and scores it; later agents read it and go straight to the right page.

## The breadcrumb standard

Three record types: one site record per domain, one page card per normalized URL, and routes that chain page cards together. Full spec: [breadcrumb-standard.md](breadcrumb-standard.md).

**Site record** — knowledge that applies to every page on a domain:

- **Access:** needs JavaScript, .md versions, public API, blocks headless browsers, known extraction problems
- **Structure:** main sections and what lives under each URL prefix
- **Routes:** "to find X here, go A → B → C"
- **Pointers:** llms.txt, sitemap, site search URL

**Page card** — one per URL, at one of four tiers:

| Tier | Contents | Budget (tokens) | When to use |
| --- | --- | --- | --- |
| L0 Pointer | URL, one-line answers, date checked, fingerprint | ~30 | Every page visited |
| L1 Card | L0 + route (the smallest source with the page's content and the fetch arguments that worked), access notes, links worth following, page size | ~200 | Default for useful pages |
| L2 Card + facts | L1 + 3–10 facts, each with a section and a short quote | ~400 | Facts asked for repeatedly |
| L3 Outline (proposed) | One line per section, ~5–10% of page size | varies | Long or hard-to-reach pages |

How the four kinds of knowledge map onto records:

| Knowledge | Lives in |
| --- | --- |
| Where things are | L0 answers, site structure |
| How to get it | Site access, L1 route and access notes |
| What it says | L1 answers, L2 facts, L3 outline |
| Task routes | Site routes |

**Route** — a goal (what was looked for), ordered steps (page-card IDs, not raw URLs), and answer_at (the page and section holding the answer).

## Depth policy

Breadcrumbs point at pages rather than replace them; depth is added only where demand proves it pays.

Why brief by default:

1. **Writing is expensive.** A short Stripe card costs ~750 input-token equivalents; a near-full write-up costs ~13,700, about 5× reading the page.
2. **Readers scan many records.** 20–50 cards at 30–150 tokens is 1.5k–7.5k tokens; at 1,500 each it is 30k–75k.
3. **Detail goes stale.** "Covers rate limits" lasts years; "100 requests per second" can change in one docs update.
4. **Every claim needs checking.** More facts means more to verify and more room for hallucinated detail.
5. **Long text hides injected instructions.** Short structured fields are easier to police.
6. **Copyright and site owners.** Detailed write-ups start to look like copies of the site.
7. **Knowing where to look is most of the saving.** The waste is raw HTML and wrong turns, not reading the right page.

When deeper pays: pages that are expensive to reach (JavaScript rendering, blocked headless browsers), huge pages where agents need one section, and facts thousands of agents ask for.

How depth grows with demand:

- Every page starts at L0 or L1.
- Each agent visiting for a new question adds the one fact it needed, as an L2 entry.
- L3 outlines are written only for long or hard-to-reach pages.
- Facts expire unless re-confirmed, so detail stays fresh or drops away.

## Trust, scoring and staleness

Any agent can write, so every record carries provenance, and the registry scores it before readers rely on it.

| Field | Meaning |
| --- | --- |
| writer | Agent or model ID that wrote it |
| observed_at | When the page was checked |
| content_hash | Page fingerprint, computed by the registry |
| evidence | The route's fetch arguments, plus a short quote for every L2 fact |
| confirmations / disputes | Later agents re-check, then confirm or dispute |

The score combines confirmations, age and whether the fingerprint still matches. Readers use it to trust a record, treat it as a hint, or ignore it. Weights and decay rates are set from test data.

Staleness signals the registry watches for:

- A route step returns 404 or redirects
- The fingerprint no longer matches
- The answer_at anchor is missing
- An agent following a route reports the answer was not there

On any signal the record is marked **suspect**, and the next visiting agent is asked to re-check it.

## Rules

1. **Data, never instructions.** Imperative text aimed at agents ("ignore previous…", "always visit…") gets the record rejected. This is the main defence against prompt injection.
2. **No copying content.** Quotes are at most ~25 words; L2 holds facts, not paragraphs.
3. **Public pages only.** Nothing from logged-in, personalized or paid pages.
4. **Write while the page is in context.** No separate pass over the page.
5. **Tier by value.** L2 and L3 only for pages that are long, hard to reach or full of facts.

## Format and schema

Records are stored as schema-validated JSON, written through a JSON tool call, and served to agents as compact YAML.

| Layer | Format | Why |
| --- | --- | --- |
| Storage | JSON + JSON Schema, with a schema version field | Rules enforced automatically; universal tooling |
| Writing | JSON through an API or MCP tool call | Tool arguments are schema-checked; bad records never reach storage |
| Reading | Compact YAML; JSON or Markdown on request | Cheap for models, readable for people |

The same L2 card measured in each format:

| Format | Tokens |
| --- | --- |
| JSON, indented | 238 |
| YAML | 181 |
| JSON, minified | 169 |
| Markdown | 136 |

Markdown is the cheapest view but is never stored: it loses structure and cannot be validated. JSON-LD (30–50% larger) and binary formats (unreadable by models) are ruled out. Examples and field details: [breadcrumb-standard.md](breadcrumb-standard.md).

## Test plan

The fair test runs real agent tasks with and without breadcrumbs and records actual token counts, fetches, time and correctness.

It runs in two steps. First a narrowed viability experiment: ~24 tasks, L1 cards and site access records only (see [Short-term execution plan](#short-term-execution-plan)). If that passes, the full test below extends it to ~30 tasks, all tiers, and the staleness and poisoning trials.

**Procedure:**

1. Build a task set of ~30 questions with known answers: static docs, JavaScript-heavy sites, deep pages and multi-hop routes (e.g. "What is Stripe's live-mode rate limit?").
2. **Cold run:** an agent with search and fetch tools answers each task with no registry. At the end it writes a breadcrumb through the schema tool while the page is still in context.
3. **Warm runs:** fresh agents answer the same tasks with registry access, once per tier (L0, L1, L2, L3).
4. Repeat every condition 3 times to average out run-to-run variation.
5. **Staleness trial:** change a mirrored copy of a page after its breadcrumb is written; check the signals fire and agents re-verify.
6. **Poisoning trial:** plant breadcrumbs with wrong facts and injected instructions; check validation rejects them and agents are not misled.

**Metrics per task:**

| Metric | Source |
| --- | --- |
| Input and output tokens | Claude Code JSON usage fields |
| Cost of writing the breadcrumb | Output tokens of the write call |
| Fetches and searches | Tool-call log |
| Wall-clock time | Harness timer |
| Correct answer | Checked against the known answer |
| Staleness signals fired | Registry log |

**Proposed success criteria** (to confirm before the run):

- Warm runs use at least 40% fewer total tokens than cold runs on average
- Writing cost is recovered within 2 reuses
- Accuracy is no worse than cold runs
- 100% of planted injection breadcrumbs are rejected
- Every staleness change is detected

Agents run through Claude Code headless mode (`claude -p --output-format json`) on the Pro plan, so no API key is needed; each run reports input, cached and output tokens.

## Use-case flavors

Different kinds of agent work waste effort in different places, so each benefits most from a different part of the breadcrumb.

| Use case | Example | Where the effort goes | Most useful breadcrumb |
| --- | --- | --- | --- |
| Hard-to-access sites | crates.io package data | Finding out the page needs JavaScript, then finding the API | Site access record |
| Docs fact lookup | Stripe live-mode rate limit | Searching and picking the right page and section | L1 card + route |
| Coding agents reading docs | Python json options, SDK quickstarts | Noisy HTML, finding the .md or raw version | Site access + L1 card |
| Deep multi-hop pages | A specific webhook event's retry rules | Wrong turns through section pages | Route |
| Long-page research | One section of a Wikipedia article | Reading 18k tokens to use 1k | L1 route to the section, or L3 outline |
| Repeated popular facts | The same rate limit asked thousands of times | Re-reading the page every time | L2 fact |
| Monitoring changes | Prices, changelogs, status pages | Re-locating the value each check | L1 card + fingerprint |
| Logged-in or transactional tasks | Booking, account pages | Personal flows | Out of scope (public pages only) |

The first three rows are where the measurements showed the largest waste, so the experiment starts there.

## Short-term execution plan

One tier is enough to prove viability: test L1 cards plus site access records against a no-breadcrumb baseline, and compare tiers only once that works.

**Why one tier is enough:**

- Viability asks one question: do breadcrumbs make agents cheaper without making them wrong? One good tier against a cold baseline answers it.
- L1 plus site access covers the three highest-waste use cases above.
- L0 alone is too thin and risks a false "no effect" result. L2 and L3 mix in content caching and staleness, which muddies the result.
- Testing every tier multiplies runs and cost before we know there is any effect. Tier comparison becomes the follow-up.

**What to build (smallest version that proves it):**

1. **JSON Schema for the v0.2 MVP subset:** site access record and L1 page card only ([standard §9](breadcrumb-standard.md#9-mvp-subset-for-the-viability-experiment)). The schema's version follows the standard's, so records carry `schema: "0.2"`.
2. **Local registry stub:** a SQLite file with two tools, lookup (by URL or domain) and write (validated against the schema). No scoring, no re-fetching, no hosting.
3. **Agent harness:** a Claude Code headless agent with search, fetch (cleaned Markdown), render (headless Chrome), registry lookup and registry write. It logs token usage, tool calls, time and the final answer.
4. **Task set:** about 24 public-web questions with known answers, 8 each from hard-to-access sites, docs fact lookup and coding-agent docs.
5. **Report:** a table per task and per use case, cold vs warm.

**How to run it:**

1. **Cold:** an agent answers each task with an empty registry and writes breadcrumbs as it finishes.
2. **Warm, same task:** a fresh agent answers the same question with the registry. This shows the ceiling.
3. **Warm, related task:** a fresh agent answers a different question on the same site, e.g. Stripe's sandbox limit after the live limit. This is the real test, since exact repeats are just caching.
4. Run each condition 3 times and average.

Both arms use the same fetch and cleaning pipeline, so any saving comes from breadcrumbs, not from better HTML cleanup.

**Viability bar (proposed, to confirm before running):**

| Measure | Bar |
| --- | --- |
| Total tokens, warm related task vs cold | At least 30% lower on average |
| Fetches and searches per task | Lower in warm runs |
| Answer accuracy | No worse than cold |
| Breadcrumb write cost | Recovered within 2 reuses |

**Deliberately left out of this step:** scoring and trust, poisoning trials, staleness detection, L2 and L3 tiers, a hosted registry, multiple writers.

**Decision after the run:**

- **Clear win:** move to tier comparison (L0 vs L1 vs L2) and the poisoning trial.
- **Win in some use cases only:** narrow the product to those flavors, e.g. an access-knowledge layer for hard sites.
- **No win:** stop or rethink before building the registry.

**Needed to start:** Claude Code on the Pro plan in headless mode, local Chrome and Python with the extraction libraries (all already installed). The registry stub runs as a local MCP server loaded with `--mcp-config`.

**Running on the Pro plan — caveats:**

- **~26k tokens of fixed overhead per run** from Claude Code's own instructions and tools. Subtract an empty baseline run, and trim with `--system-prompt` and `--tools`.
- **Caching skews totals.** Report uncached input, cached input and output separately.
- **Usage limits** reset every 5 hours. Start with 1 repeat instead of 3, spread runs over days, or use `--model sonnet`.
- **Less control than the raw API.** Results describe Claude Code with breadcrumbs, a real agent people use.

An API key is only needed if the limits block progress.

## Roadmap

![The registry is built only after the fair test proves savings](img/roadmap.png)

No dates are set yet. The key gate is the second: if warm runs do not meet the savings criteria, the registry is reshaped or dropped before anything is built.

## Risks and mitigations

The two risks that could sink the project are poisoned records and a large incumbent adding the same feature.

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Poisoned or injected breadcrumbs | Agents misled or hijacked | Schema field limits, imperative-text filter, scoring, poisoning trial before launch |
| Firecrawl or an AI provider builds this | Loss of differentiation | Stay neutral and open; focus on paths and the long tail; ship the standard early |
| Stale breadcrumbs look current | Wrong answers delivered confidently | Registry fingerprints, staleness signals, fact expiry |
| Copyright or terms-of-service complaints | Legal exposure, hostile site owners | Pointers and facts only, quote limits, public pages only, owner opt-out |
| Providers will not contribute | Registry stays empty | MCP distribution; show token savings; free reads |
| Savings smaller than measured | Weak value proposition | Fair test before building the registry; stop or reshape if criteria fail |
| Writer spam or abuse | Low-quality records | Writer identity, rate limits, reputation per writer |

## Open questions

- [ ] Scoring weights: how fast trust decays, and how many confirmations make a fact reliable (after testing)
- [ ] Route handling when a step page moves or its fingerprint changes
- [ ] Writer identity: how agents and providers authenticate, and how abuse is rate-limited
- [ ] Tier selection: rules for when an agent writes L0, L1, L2 or L3
- [ ] Confirm registry-computed fingerprints, and how often the registry re-fetches
- [ ] Business model: free reads, paid bulk access, or a nonprofit standard body
- [ ] Site-owner role: opt-out, verified owner records, or both

## Sources

- [Firecrawl Alexandria](https://firecrawl.dev/howiai)
- [Firecrawl raises $75M Series B; launches Alexandria](https://www.pr.com/press-release/979737)
- [Alexandria in ChatGPT and Codex](https://firecrawl.dev/blog/alexandria-chatgpt-codex)
- [The /llms.txt proposal](https://llmstxt.org/)
- [Aicorn plugin](https://www.claudepluginhub.com/plugins/telepenin-aicorn-plugin)
- [agentsweb.org — Cache for AI](https://chromewebstore.google.com/detail/bjdgnbanmhhlicnhclicblekglephipg)
- [AnswersEngine fetch docs](https://answersengine.readthedocs.io/en/latest/fetch_doc.html)
- [webnav](https://socket.dev/npm/package/@dikshanty94/webnav)
- [Web Speed tutorial](https://aiindigo.com/tutorials/getting-started-with-web-speed-accelerate-ai-agent-web-navigation)
- [AWS Agentic AI Lens: agent caching](https://docs.aws.amazon.com/wellarchitected/latest/agentic-ai-lens/agentsus02-bp02.html)
- Measured pages: [Stripe rate limits](https://docs.stripe.com/rate-limits), [Firecrawl repo](https://github.com/firecrawl/firecrawl), [Wikipedia: Web crawler](https://en.wikipedia.org/wiki/Web_crawler), [MDN 429](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status/429), [Python json](https://docs.python.org/3/library/json.html), [crates.io serde](https://crates.io/crates/serde), [Spotify](https://open.spotify.com/artist/0OdUWJ0sBjDrqHygGUXeCF), [Uniswap](https://app.uniswap.org/explore/tokens)

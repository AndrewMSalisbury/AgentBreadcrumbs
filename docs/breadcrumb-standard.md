# Breadcrumbs for AI Agents — Draft Standard v0.2

*Status: draft · Last updated: 2026-11-05*

This is the specification only. Why the project exists, the measurements, use cases, test plan and roadmap are in [PLAN.md](PLAN.md).

**Changes since v0.1:** added the L3 outline tier (proposed), demand-driven depth rules, the MVP subset (§9), and an open-questions list aligned with the plan. Measurements and test plan moved to PLAN.md.

**Revised 2026-11-05:** the L1 card's core is a `route` (§2.2), the cheapest way to get the page's content, in place of the section map. The viability experiment found section maps failed to save on related questions (map-0.1), while route cards did (route-0.1 onward). Records keep `schema: "0.2"`.

## 1. Definition

A **breadcrumb** is a short, structured note an AI agent leaves in a central registry after reading a web page. It records **where** information is, **how** to get it, **what** it says, and **which route** through a site answers a given question. Agents write breadcrumbs as a side effect of normal work, not in a separate crawl.

## 2. Record types

### 2.1 Site record (one per domain)

| Field | Contents |
|---|---|
| `site` | Normalized host, e.g. `docs.stripe.com` |
| `schema` | Standard version, e.g. `"0.2"` |
| `access` | Needs JavaScript? `.md` versions? Public API (and which fields matter)? Blocks headless browsers? Known extraction problems? |
| `structure` | Main sections and what lives under each URL prefix |
| `routes` | List of routes (§2.3) |
| `pointers` | `llms.txt`, sitemap, site search URL |
| `provenance` | §4 |

### 2.2 Page card (one per normalized URL), in tiers

| Tier | Contents | Budget | When to write |
|---|---|---|---|
| **L0 Pointer** | `url`, `answers` (one line), `observed_at`, `content_hash` | ~30 tokens | Every page visited |
| **L1 Card** | L0 + `route` (below), `access` notes for this page, `links` worth following, `size_tokens` | ~200 tokens | Default for useful pages |
| **L2 Card + facts** | L1 + `facts`: 3–10 entries of `claim`, `value`, `section`, `quote` | ~400 tokens | Facts asked for repeatedly |
| **L3 Outline** *(proposed)* | L1 + `outline`: one line per section | ~5–10% of page size | Long or hard-to-reach pages |

An L1 card's `route` says how to fetch this page's content most cheaply. It is not a site route (§2.3), which says which pages to visit.

| Field | Contents |
|---|---|
| `url` | The smallest source with the page's content: raw source file, API endpoint, Markdown version, or the page itself if nothing smaller exists |
| `select` | JSON paths that keep only the useful fields of an API response |
| `section` | A heading or anchor that fetches only the relevant section of `url` |
| `start` | An offset that reaches the relevant part when `section` doesn't work |
| `tokens` | Approximate size of what the route returns |
| `notes` | What did not work and why, e.g. `section` fails because entries aren't headings |

Only `url` is required. Measured route cards are about 800 bytes of JSON.

### 2.3 Route

| Field | Contents |
|---|---|
| `goal` | What was being looked for |
| `steps` | Ordered page-card IDs (not raw URLs) |
| `answer_at` | Page-card ID and section anchor where the answer was found |

## 3. Depth rules

1. Every page starts at L0 or L1.
2. Depth grows with demand: an agent visiting for a new question adds only the one fact it needed, as an L2 entry.
3. L3 outlines are written only for long or hard-to-reach pages.
4. L2 facts expire unless re-confirmed.
5. An agent never rewrites a page's content; Markdown conversion is done in code, not by the model.

## 4. Provenance and trust

Every record carries:

| Field | Meaning |
|---|---|
| `writer` | Agent or model ID |
| `observed_at` | When the page was checked (ISO date) |
| `content_hash` | Page fingerprint, computed by the registry (§6.2) |
| `evidence` | The route's fetch arguments; a quote for every L2 fact |
| `confirmations` / `disputes` | Later agents re-check, then confirm or dispute |

The registry computes a **score** from confirmations, age and fingerprint match. Readers use it to trust, treat as a hint, or ignore. Weights are set after testing.

### Staleness

A record is marked **suspect** when:
- a route step returns 404 or redirects
- the fingerprint no longer matches
- the `answer_at` anchor is missing
- an agent following a route reports the answer was not there

The next agent to visit is asked to re-check a suspect record.

## 5. Rules

1. **Data, never instructions.** Imperative text aimed at agents ("ignore previous…", "always visit…") gets the record rejected.
2. **No copying content.** Quotes are at most ~25 words; L2 holds facts, not paragraphs.
3. **Public pages only.** Nothing from logged-in, personalized or paid pages.
4. **Write while the page is in context.** No separate pass over the page.
5. **Tier by value.** L2 and L3 only for pages that are long, hard to reach or full of facts.
6. **Pointer-only where sites opt out.** On paths that robots.txt or an AI opt-out signal disallows, records hold only routes, access notes and section anchors: no answers, facts or quotes. The registry never fetches those pages itself.

## 6. Format

### 6.1 Layers

| Layer | Format |
|---|---|
| Storage | JSON, validated by JSON Schema, with a `schema` version field |
| Writing | JSON through an API or MCP tool call; invalid records are rejected before storage |
| Reading | Compact YAML by default; `format=json` or Markdown on request |

Measured size of one L2 card: JSON indented 238 tokens, YAML 181, JSON minified 169, Markdown 136. Markdown is never the stored form. JSON-LD and binary formats are ruled out.

### 6.2 Normalization and identity

1. **URL normalization:** lowercase host; strip tracking parameters (`utm_*`, `ref`, etc.); map `.md` versions to their page; follow `rel=canonical`.
2. **Fingerprint:** computed by the registry from its own fetch of the page, so different cleanup tools never make an unchanged page look changed.
3. **IDs:** page cards are `page:<normalized host + path>`; routes reference them by ID.
4. **Field limits:** short maximum lengths on every free-text field; no free-text instructions field; imperative text is flagged.

## 7. Examples (YAML read view)

```yaml
# site record
site: docs.stripe.com
schema: "0.2"
access:
  md_versions: "append .md to any docs URL"
  extraction_issues: "generic HTML extractors drop table values; use .md"
routes:
  - goal: "API rate limits"
    steps: [page:docs.stripe.com/rate-limits]
    answer_at: "page:docs.stripe.com/rate-limits#rate-limits"
provenance: {writer: claude-opus-5-5, observed_at: 2026-10-21, confirmations: 0}
---
# page card, L2
id: page:docs.stripe.com/rate-limits
url: https://docs.stripe.com/rate-limits
tier: L2
answers: "Stripe API rate and concurrency limits, 429 handling, increase requests"
route:
  url: https://docs.stripe.com/rate-limits.md   # the site's Markdown version keeps table values
  section: "Rate limits"
facts:
  - claim: Global limit, live mode
    value: 100 requests/second
    section: "#rate-limits"
    quote: "Live mode ... 100 requests per second"
  - claim: Global limit, sandbox
    value: 25 requests/second
    section: "#rate-limits"
    quote: "Sandbox ... 25 requests per second"
content_hash: sha256:…
provenance: {writer: claude-opus-5-5, observed_at: 2026-10-21, confirmations: 0}
```

A route card for a long reference page whose entries aren't headings (from the experiment):

```yaml
id: page:doc.rust-lang.org/cargo/reference/manifest.html
url: https://doc.rust-lang.org/cargo/reference/manifest.html
tier: L1
answers: "Cargo.toml manifest reference: package fields, lints, hints, badges"
route:
  url: https://doc.rust-lang.org/cargo/reference/manifest.html
  start: 2300
  tokens: 4100
  notes: "section= on 'The readme field' cuts off after the code sample; start=2300 returns the full entry"
size_tokens: 6400
```

Access knowledge for a JavaScript-heavy site:

```yaml
site: crates.io
schema: "0.2"
access:
  js_required: true   # plain fetch returns an empty shell
  api: "GET https://crates.io/api/v1/crates/{name}"
  api_notes: "full response ~143k tokens (every version listed); keep only crate.* fields (~100 tokens)"
```

## 8. Open questions

1. Scoring weights and decay rates (after testing)
2. Route handling when a step page moves or its fingerprint changes
3. Writer identity and abuse rate-limiting
4. Tier selection rules for agents
5. How often the registry re-fetches to refresh fingerprints

## 9. MVP subset (for the viability experiment)

The first experiment uses only:
- **Site record:** `site`, `schema`, `access`, `provenance`
- **Page card, L1:** `id`, `url`, `answers`, `route`, `access`, `links`, `size_tokens`, `observed_at`, `provenance` (map-0.1 tested `sections` in place of `route`)

Not in the MVP: routes, L0/L2/L3, scoring, confirmations, registry-computed fingerprints (the harness hashes the cleaned page at write time instead).

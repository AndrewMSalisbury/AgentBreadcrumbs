# Breadcrumbs for AI Agents — Draft Standard v0.2

*Status: draft · Last updated: 2026-10-26*

This is the specification only. Why the project exists, the measurements, use cases, test plan and roadmap are in [PLAN.md](PLAN.md).

**Changes since v0.1:** added the L3 outline tier (proposed), demand-driven depth rules, the MVP subset (§9), and an open-questions list aligned with the plan. Measurements and test plan moved to PLAN.md.

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
| **L1 Card** | L0 + `sections` (anchors and what each covers), `access` notes for this page, `links` worth following, `size_tokens` | ~150 tokens | Default for useful pages |
| **L2 Card + facts** | L1 + `facts`: 3–10 entries of `claim`, `value`, `section`, `quote` | ~400 tokens | Facts asked for repeatedly |
| **L3 Outline** *(proposed)* | L1 + `outline`: one line per section | ~5–10% of page size | Long or hard-to-reach pages |

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
| `evidence` | Section anchors; a quote for every L2 fact |
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
sections:
  "#rate-limits": limits table
  "#handle-limiting": backoff advice
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
- **Page card, L1:** `id`, `url`, `answers`, `sections`, `access`, `links`, `size_tokens`, `observed_at`, `provenance`

Not in the MVP: routes, L0/L2/L3, scoring, confirmations, registry-computed fingerprints (the harness hashes the cleaned page at write time instead).

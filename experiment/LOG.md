# Experiment log

Each iteration is named `<approach>-0.<n>`: a new approach starts at 0.1 and each change to it adds 1. Results for an iteration are in `out_<name>/`, and `python run.py ... --iteration <name>` reruns it.

| Iteration | Change | Results |
|---|---|---|
| narrow-0.1 | Page cards holding only the answer's sections (earlier prompt, can't be rerun) | `out_narrow-0.1/` |
| map-0.1 | Page cards map the whole page: main sections and what each covers | `out_map-0.1/` |
| route-0.1 | Route cards: the cheapest way to get the page's content | `out_route-0.1/` |
| lean-0.1 | No page card on one-fetch pages or pages a site URL pattern covers | `out_lean-0.1/` |
| lean-0.2 | lean-0.1 reworded to lead with when a card is expected | `out_lean-0.2/` |
| enforced-0.1 | Route rule, with the skip enforced by the harness | `out_enforced-0.1/` |
| enforced-0.2 | `answers` lists accepted | `out_enforced-0.2/` |
| coldonly-0.1 | lean-0.1 cold registries, warm agents read only | `out_coldonly-0.1/` |
| miss-0.1 | Write rule only in the first lookup that misses (the lean rule) | `out_miss-0.1/` |
| miss-0.2 | Route rule in the miss note, one-fetch cards refused, nudge on the eligible fetch | `out_miss-0.2/` |
| miss-0.3 | Stop hook: a nudged run that stored nothing is sent back once | `out_miss-0.3/` |
| miss-0.4 | No note for runs whose lookups found anything | `out_miss-0.4/` |
| miss-0.5 | Cards need 2,000+ fetched tokens and must be filed under a looked-up site | `out_miss-0.5/` |
| miss-0.6 | The note says again that one-fetch runs still write a site record with a URL pattern (worse: halved site records) | `out_miss-0.6_smoke/` |
| miss-0.7 | miss-0.5, with a search counting toward the page-card bar again (a search and one fetch can earn a card) | `out_miss-0.7_probe/` |
| miss-0.8 | miss-0.7 with a page-card bar of 3 web calls, searches included | `out_miss-0.8/` |
| miss-0.9 | miss-0.7 with the page-card instructions deferred to the fetch that passes the bar; a miss sends only a short site-record note | `out_miss-0.9/` |
| miss-0.10 | miss-0.9 with miss-0.8's bar of 3 web calls | `out_miss-0.10/` |
| miss-0.11 | miss-0.10 with the site-record note ruling out records that only say a plain fetch works | `out_miss-0.11/` |
| probe-0.1 | Not a write policy: library-docs demand, 72 versioned questions on 12 libraries, miss-0.5 arms plus memory, open and oracle | `out_probe-0.1/` |
| miss-0.13 | miss-0.11 with no note on a miss: the site-record note comes with the first result that shows an access route | `out_miss-0.13/` |
| miss-0.14 | miss-0.13 without the 3-call minimum (bar 3 is read off its runs by `out_miss-0.12/bar3.py`) | `out_miss-0.14/` |
| trace-0.1 | No agent writes: route cards built from a no-write run's trace (`out_trace-0.1/build.py`) | `out_trace-0.1/` |
| trace-0.2 | Lean trace cards (no `start` offset), and a cold arm under miss-0.13's site-record note only, its card built from its own trace | `out_trace-0.2/` |
| trace-0.3 | Not run: an offline check of trace cards built from the cheapest of several traces (`out_trace-0.3/check.py`) | `out_trace-0.3/` |
| firecrawl-0.1 | fold-0.1 and noregistry with pages from Firecrawl's scrape (`--backend firecrawl`), against an agent on the stock `firecrawl-mcp` server (`--backend firecrawl-mcp`); cards built from the Firecrawl-backed noregistry run | `out_firecrawl-0.1/` |
| card-0.1 | Route cards in front of stock `firecrawl-mcp`'s scrape (`--backend firecrawl-card`, `bc/firecrawl_card.py`): same 30 tools, a carded page's first scrape served from its route; against stock, 2 reps | `out_card-0.1/` |
| card-0.2 | card-0.1 without the redirect: a route to another URL with no section is only named (`--iteration card-0.2`); with a prompt-only arm (card-0.2 on an empty registry) and a third stock rep | `out_card-0.2/` |

`out_rep1_oldrule/` and `out_smoke_2026-10-26/` are setup runs from before narrow-0.1.

## 2026-10-26: narrow-0.1, narrow cards (hard set, rep 1)

18 hard tasks, Sonnet, one rep. Savings are against cold-nowrite (no registry, no writing). Raw results in `out_narrow-0.1/`.

| | No-write cold | Warm same | Warm related |
|---|---|---|---|
| Mean total tokens | 25.9k | 19.4k | 41.4k |
| Mean per-task cut | | 0% | -57% (costlier) |
| Fetches + searches | 2.3 | 1.4 | 2.1 |
| Correct | 100% | 100% | 100% |

Write cost averaged +15k tokens per task; 3/18 tasks recover it within 2 reuses.

Cold agents wrote narrow cards. Each held its own answer ("keepalive_requests default (1000)") and only the sections around it, so related questions found nothing useful, fetched again and then paid to merge a section in. Worst cases: gha-matrix +441% (card pointed at the limits page; the related answer is on workflow-syntax), nginx +294%, rust +127%.

Fixed: the pypi related regex rejected "10.0 GB".

## 2026-10-27: map-0.1, page-map cards (hard set, rep 1)

The write rule, schema descriptions and write docstring now ask for a map of the whole page: up to 12 main sections, each naming what it covers, with no values. Cold-nowrite rows are reused from 2026-10-26 (its prompt is unchanged; the tool docstrings grew by a few dozen tokens).

### Fix: related baseline

The report compared warm-related with the no-write cost of the *original* question, but several related questions are harder in their own right: Rust `pop_if` loses its version badge under `section=`, and GHA background steps aren't on the page cold agents carded. A new arm, `cold-nowrite-related`, answers the related question with no registry and no writing. Warm-related is now measured against it. Rows for this arm are also appended to `out_narrow-0.1/` (it never touches the registry), so both reports use the same baseline.

### Results (rep 1, against same-question no-write baselines)

| | narrow-0.1 | map-0.1 |
|---|---|---|
| Write cost (cold − cold-nowrite) | +15.3k | +34.1k |
| Cut, warm same | 0% | -8% |
| Cut, warm related | -36% | -53% |
| Fetches related (nw → warm) | 2.5 → 2.1 | 2.5 → 2.4 |
| Correct | 100% everywhere | 100% everywhere |

Page-map cards cost twice as much to write: cold agents read more of the page to map it (nginx +280k, git-config +138k). They also did not make related runs cheaper.

Most of the warm-related loss comes from warm agents **writing**, not from reading. In map-0.1, the 9 related runs that wrote averaged +110% against their baseline (pypi, heroku, gha, git-gc, rust, bash and others). The 9 that didn't write were near the ~15% lookup overhead or better (sonatype -53%, mdn -25%, render -16%). Writes also hit schema rejections and retries (`answers` sent as a list, notes over 200 characters).

The card did route correctly when it applied: git-config related went lookup → one fetch at the carded offset. That one fetch was a 9k-token chunk, though, while the no-write agent found the small raw `gc.adoc` file. Fetch-tool limits, not cards, drive several cases: directive anchors on nginx and git-config aren't headings, so `section=` fails, and Rust's `section=` drops the stable-since badge.

### Read-only warm related (`warm-related-nowrite`)

Same registries, related question, write forbidden: this separates what reading saves from what warm agents spend writing. Run for both card styles; 36/36 correct, no write calls.

| Related, vs cold-nowrite-related | narrow-0.1 | map-0.1 |
|---|---|---|
| With writing (warm-related) | 36% higher | 53% higher |
| Read-only | 1% lower | 4% lower |
| hard_access / docs / coding | -16% / +1% / +14% | -8% / +3% / -6% |

- Writing explains the whole warm-related loss. Without it, warm related costs about the same as no breadcrumbs.
- Reading saves almost nothing on related questions either. Savings appear only where a cold agent took a wrong route that a card or site record avoids: sonatype -71%/-58% (direct API), puppet -33% both, bash -44%/-18%, mdn -11%/-31%.
- Lookup overhead without the write rule is about 2-3% (terraform, galaxy, artifacthub), not the ~15% seen with it. Most of that 15% was the longer write rule in the system prompt, not the lookup.
- Cards can send agents the expensive way: git-config related is +31%/+38% because the card points at a 9k-token chunk of the HTML page, while no-write agents find the small raw `gc.adoc`. One outlier: narrow-0.1 rust read-only took 11 fetches and +104%; page-map rust was -25%.

Verdict for the hard set at rep 1: L1 cards fail the ≥30% bar on related questions, read-only or not. The value seen comes from access routes (APIs, raw sources), not section maps.

## Later

- **Writing policy.** Warm agents should rarely write: writing turned a ~0% read result into +36-53%. Write only on an empty lookup, or let the registry merge sections from fetch logs instead of agent-written records.
- **Route-first breadcrumbs.** Record the cheapest way to get a page's content (raw source, API, Markdown version) rather than a section map, since that's where every saving came from.

- **Skip lookup on one-fetch pages.** On tasks that cold agents answer with a single fetch, warm runs cost about 10% more: the lookup adds tokens and saves nothing. Try telling agents when a lookup is worth it, or folding breadcrumbs into fetch results.
- **Reps 2 and 3.** Every number above is a single run; single runs like gha's 140k related run may be outliers. Run 3 reps per arm before drawing conclusions.

## 2026-10-28: map-0.1, reps 2 and 3 (hard set)

Same code and prompts as map-0.1 rep 1, all six arms, reps 2 and 3 run in parallel. Before running, three answers had moved on and were updated in `tasks.yaml`: hashicorp/google 8.8.1 → 8.9.0, puppetlabs/stdlib 10.1.0 → 10.1.1, puppetlabs/apache 13.4.0 → 13.5.0. 216/216 runs correct. `out_map-0.1/report.md` now averages reps 1-3.

### Results by rep (mean of per-task changes against the same-question no-write run)

| | Rep 1 | Rep 2 | Rep 3 |
|---|---|---|---|
| Write cost | +34.1k | +25.7k | +13.2k |
| Warm same | +8% (median +15%) | +67% (+15%) | +32% (+13%) |
| Warm related | +53% (+15%) | +32% (+16%) | +19% (+12%) |
| Read-only warm related | -4% (+1%) | -5% (-1%) | -5% (0%) |

Over all three reps (`report.py`, per-task means first): warm related is 20% costlier, read-only warm related is 12% cheaper, write cost is +24k per task and 1/18 tasks recover it within 2 reuses. The viability bar still fails on both token measures. Rep 1's conclusion holds: reading saves about 0-12%, and writing turns that into a loss.

Reps disagree a lot on single tasks: read-only sonatype -58% / +138% / -57%, git-gc +38% / -79% / -1%, nginx -3% / +5% / +86%. Medians stay near +0-15% in every rep, so the means are driven by a few large runs.

### Many warm runs never saw a card

Warm runs, classed by what lookup returned (all 3 reps):

| Lookup returned | Warm same | Read-only related | Warm related |
|---|---|---|---|
| Page card for the page looked up | 15 runs, mean 0% | 8, -2% | 15, +68% |
| Site record (API route) | 18, +4% | 17, +2% | 17, +13% |
| Other pages on the site only | 13, -5% | 20, -3% | 12, +27% |
| Nothing | 8, +241% | 9, -22% | 10, +30% |

- Read-only runs that got a page card were no cheaper (-2%). The card was found and still didn't help.
- `www.` mismatch: bash cards are stored under `www.gnu.org`, warm agents look up `gnu.org`, and `page_id`/`host_of` don't fold `www.`, so all 9 bash warm runs saw nothing.
- Lookup key ≠ card key: pypi agents look up `pypi.org`, the card is on `docs.pypi.org`; heroku, mdn and rust agents look up a neighbouring page (`dynos`, `Window/fetch`, `Vec.html`) and get only `other_pages` summaries.
- Cold runs sometimes leave no card: git-gc r3 and github r2 wrote nothing usable, and git-gc r2 carded `code.googlesource.com/.../gc.adoc`. Those warm-same runs then wrote cards themselves at +500-850%.

## 2026-10-29: www. fix, route-0.1, lean-0.1 and lean-0.2 (hard set, reps 1-3)

### Fix: www. hosts

`host_of` and `page_id` now fold `www.` into the bare host, so `www.gnu.org` and `gnu.org` are one site. Stored card URLs keep `www.`. In the map-0.1 runs only bash was affected: its three cold registries were re-keyed and its three warm arms rerun. The map-0.1 totals barely moved (warm related +19%, read-only cut 13%); bash warm-same went from +17% to -18%.

### route-0.1: route-first cards (`--iteration route-0.1`, results in `out_route-0.1/`)

The page card swaps the section map for `route`: the smallest source with the page's content (raw file, API, Markdown version or the page itself), the fetch arguments that worked on it, a rough size and notes on what failed. The site record asks for URL patterns that work for other pages (`{name}`), and site-wide lookups list each carded page's route. No-write baselines are shared with `out_map-0.1/`, since those arms never touch a registry. 324/324 correct.

| Related question, mean per-task change vs no-write | map-0.1 | route-0.1 |
|---|---|---|
| Read-only, all | -13% | -13% |
| Read-only, coding | -21% | **-43%** |
| Read-only, docs / hard_access | -10% / -7% | +1% / +3% |
| With writing, all | +19% | +14% |
| With writing, coding | +17% | **-38%** |
| With writing, docs / hard_access | +30% / +9% | +35% / +44% |
| Write cost (cold - cold-nowrite) | +24.3k | +19.7k |

- Route cards are the first breadcrumb to clear the 30% bar on any group: on coding tasks warm agents answer in about one fetch, read-only or writing. git-gc related -70% (raw `Documentation/config/{group}.adoc`), bash -49%, mdn -39%, rust -55%, nginx -32%. Same-question warm on coding is -39%.
- On hard_access and docs they lose, for two reasons. Pages a cold agent already answers in one fetch have nothing to save, so the lookup is pure overhead (+3-5% read-only). And warm agents write a page card for each new page even when the site record's `{namespace}/{name}` pattern already covers it: puppet 67-100% wrote, +75%; jetbrains +72%; galaxy +44%.
- Overall the viability bar still fails (+14% with writing, -13% read-only), but coding alone passes.

### Harness bug: piped stdin reached agents

`claude -p` appends piped stdin to the prompt. Rerun scripts that fed a task list to a `while read` loop passed the rest of the list to every agent: 103 route rows had +600 to +1,950 tokens per API call. `run.py` now starts agents with `stdin=DEVNULL`; the affected rows were rerun and all route rows have normal first-call sizes (warm-related ~3.5k, read-only ~3.15k). Two usage-limit interruptions left placeholder rows, also rerun. Earlier `for`-loop runs and all page-map rows were unaffected.

Answers that moved during the runs: hashicorp/aws 6.70.0 → 6.71.0 (6 route rows regraded, marked `regraded`).

### lean-0.1: lean write policy (`--iteration lean-0.1`, results in `out_lean-0.1/`)

Same route cards, new write rule: no page card on a page answered with one fetch and no search (a site record is still allowed if it adds a URL pattern), and no page card when lookup's card or site pattern already covers the page. A smoke run first showed puppet cold writing a site record after one fetch; that record carried the `{owner}-{name}` API pattern, so the rule was relaxed to allow it rather than tightened. No-write baselines are copied from `out_route-0.1/`. All four registry arms rerun, reps 1-3; 216/216 correct.

| Mean per-task change vs no-write | route-0.1 | lean-0.1 |
|---|---|---|
| Write cost (cold - cold-nowrite) | +19.7k | +9.9k |
| Warm same, all | +13% | +1% |
| Warm related, all | +14% | **-6%** |
| Read-only related, all | -13% | -16% |
| Warm related, hard_access / docs / coding | +44% / +35% / -38% | +13% / +6% / -37% |
| Warm same, coding | -39% | -18% |
| Write cost recovered within 2 reuses | 1/18 | 6/18 |

- The policy works where it was aimed. Warm agents mostly stopped writing on one-fetch pages: sonatype related +12% → -41%, pypi +58% → -27%, puppet +75% → +18%, terraform +47% → +18%. Warm related now comes out cheaper than no-write overall for the first time, but -6% is still far from the 30% bar.
- It also stops writes that were needed. lean-0.1 cold agents skipped the page card on multi-fetch coding pages: git-gc 0/3 (each cold run fetched the HTML page, then the raw `gc.adoc`, and wrote nothing), rust 0/3, bash 1/3. With no card, warm same on coding fell from -39% to -18% (rust -44% → +17%, git-gc -34% → -11%). The rule opens with "decide whether to write" and lists three reasons not to, which seems to push agents to under-write.
- Writes still slip through on one-fetch pages: jetbrains related wrote 1/3, artifacthub warm same wrote 3/3 (+58%).

### lean-0.2: saying when to write (`--iteration lean-0.2`, results in `out_lean-0.2/`)

lean-0.1 reworded to lead with when a page card is expected ("whenever getting it took more than one fetch or render, or a search"), keeping the skips for one-fetch pages and pages a card or site pattern covers. Same setup as lean-0.1: baselines from `out_route-0.1/`, four registry arms, reps 1-3. A usage limit cut off 48 warm runs (all warm runs for bash, compose, mdn and rust, plus some for nginx, git-gc, gha and r2); they were rerun after the reset. 216/216 correct.

| Mean per-task change vs no-write | route-0.1 | lean-0.1 | lean-0.2 |
|---|---|---|---|
| Write cost | +19.7k | +9.9k | +9.9k |
| Warm same, all | +13% | +1% | +2% |
| Warm related, all | +14% | -6% | +5% |
| Read-only related, all | -13% | -16% | -14% |
| Warm related, hard_access / docs / coding | +44% / +35% / -38% | +13% / +6% / -37% | +8% / +14% / -8% |
| Warm same, coding | -39% | -18% | -12% |
| Cold runs that wrote, coding | 100% | 33% | 50% |
| Write cost recovered within 2 reuses | 1/18 | 6/18 | 4/18 |

- The rewording helped on the pages it was aimed at, and hurt elsewhere. git-gc and rust cold runs wrote 2/3 (lean-0.1 0/3), and bash 3/3. But mdn cold wrote 1/3 (lean-0.1 3/3): r1 and r3 took 4 fetches each and wrote nothing. nginx cold wrote 1/3, so 2 of 3 warm-related nginx runs found no card, paged through the 20k-token page by offset and then wrote one (+78%, lean-0.1 -57%).
- hard_access and docs keep most of lean-0.1's gains (one-fetch pages are still rarely carded), so the skip half of the policy holds. The "write here" half is followed only about half the time, whichever way it's worded.
- lean-0.2 is no better than lean-0.1 overall. With 3 reps, single tasks swing by 50-100 points between policies (nginx related -57% → +78%, mdn same -38% → +23%). Those swings come from whether the cold run happened to write, not from what the rule says.

## Next

- **Move the write policy out of the prompt.** Two prompt wordings get the skip half right but leave page cards on multi-fetch pages to chance (33-50% on coding, against 100% under the route rule). Instead: keep the route rule's unconditional "write a card", and have the harness enforce the skip. Count fetches per run (the web and registry servers can share a per-run file) and reject page cards from one-fetch runs, plus page cards for a URL a stored site pattern already covers.
- **Schema retries.** Warm and cold agents still send `answers` as a list and get rejected, costing a retry per write. Accept a list and join it, or say "one string" in the write docstring.
- **Skip lookup on one-fetch pages** still applies: hard_access and docs read-only runs are +1-3% from lookup overhead alone.
- **Subdomains.** `pypi.org` lookups miss the `docs.pypi.org` card, and puppet's site record lands on `forgeapi.puppet.com` while agents look up `forge.puppet.com`. Folding subdomains is a design question, not done.

## 2026-10-29: enforced-0.1, harness-enforced writes (`--iteration enforced-0.1`, results in `out_enforced-0.1/`)

The route rule's "write a page card" stays in the prompt. The harness decides when a card is pointless:

- The web server logs every fetch and render, and a `PreToolUse` hook on WebSearch (passed with `--settings`; it runs under `--setting-sources ""`) logs every search. Both write to the run's `calls.log`.
- `write` refuses a page card, before schema checks so it isn't retried, when the run had at most one fetch and no search, or when a stored site record's URL pattern covers the card's URL or `route.url`. `{name}` matches one path segment, and a placeholder whose name mentions a path or slashes (`{group path with slashes}`) may span several. Site records are always accepted.
- Each fetch or render result ends with a line saying whether a page card from this run would be stored, and the rule tells agents to skip the card when the latest line says no. Without that line, agents would still spend a write turn on cards that get refused.
- Nowrite arms are unchanged (no log, no note), so baselines can be copied from `out_route-0.1/` as for lean-0.1. Rows record `write_results` (stored / rejected / not_stored).

Smoke (`out_enforced-0.1_smoke/`, cold, rep 1): puppet fetched once, saw "would not store" and wrote nothing. git-gc fetched the HTML page, then the raw `gc.adoc`, and stored a route card after one schema rejection.

### Results (reps 1-3)

No-write baselines and the baseline row are copied from `out_lean-0.2/` (originally `out_route-0.1/`). All four registry arms ran, reps 1-3 in parallel, with no interruptions. 216/216 correct, and every answer verified at its source before the run.

| Mean per-task change vs no-write | route-0.1 | lean-0.1 | lean-0.2 | enforced-0.1 |
|---|---|---|---|---|
| Write cost | +19.7k | +9.9k | +9.9k | +15.6k |
| Warm same, all | +13% | +1% | +2% | +11% |
| Warm related, all | +14% | -6% | +5% | +20% |
| Read-only related, all | -13% | -16% | -14% | **-18%** |
| Warm related, hard_access / docs / coding | +44% / +35% / -38% | +13% / +6% / -37% | +8% / +14% / -8% | **+1%** / +80% / -22% |
| Read-only related, coding | -43% | | | -38% |
| Warm same, coding | -39% | -18% | -12% | -19% |
| Cold runs that stored a page card, coding | 100% | 33% | 50% | 72% |
| Write cost recovered within 2 reuses | 1/18 | 6/18 | 4/18 | 5/18 |

- **The skip works.** On hard_access no arm wrote anything: 0 of 54 cold and warm runs, and the registry never had to refuse a card, because agents always heeded the note. Warm related on hard_access is +1%, the best of any policy. The ~+15% left on one-fetch warm-same runs is the write rule's length in the system prompt, as before. Cold agents also stopped writing site records on one-fetch API pages (puppet wrote one under lean-0.1), probably because the note reads as "don't write" when it only covers page cards.
- **Coding cards came back, but not all the way.** 13/18 coding cold runs stored a card (git-gc, bash, mdn and nginx 3/3), against 33-50% under the prompt wordings. Rust stored 1/3, and the other two runs were eligible (2 and 4 fetches plus a search, note said "would store") but never called write. Read-only coding related is -38%, near route's -43%. With writing it's -22%, against route's -38%: nginx related +28% (2.7 fetches) and rust same +28% with only one card.
- **Docs blew up.** Warm-related agents wrote in 12/18 docs runs. A related question usually needs a second page or a search, so the run qualifies, and the "would store a page card" note on every fetch result seems to work as an invitation. gha +93% (110k: more searches than the no-write run, plus a write), github +119%, pypi +165%, render +65%, heroku +27%. Read-only docs related is -11%, so again the loss is all writing.
- **Search loophole.** A search counts like a second fetch, so one search plus one fetch qualifies for a card. 9 of 42 stored cards came from such runs: all 8 pypi writes, plus one github. Pypi agents look up `pypi.org`, miss the `docs.pypi.org` card (the subdomain issue), search, fetch once and write again: write cost +35.5k, and warm runs +165-207%. With writing forbidden, the same agents skip the search and answer in one fetch (11.8k).
- **Schema retries are now the biggest fixed cost.** 36 of 42 stored writes followed a rejection, 34 of them for `answers` sent as a list. Each one is an extra turn over the whole context.

Verdict: harness enforcement fixes what it was aimed at (no writes on one-fetch pages, more cards on multi-fetch coding pages), but overall it's worse than lean-0.1 (+20% vs -6% with writing). The loss comes from writes the rule allows: warm agents on docs pages and pypi's search-then-write loop. Read-only related is the best yet at -18%, so the registry contents are better. The writes cost more than they save.

## Next

- **Accept `answers` as a list** and join it. It's a cheap change and it affects every arm: 34 of 42 enforced-0.1 writes paid a retry turn.
- **Show only refusals.** Drop the "would store" note and say only when a card would be refused, to see whether the positive note is what invites the docs writes.
- **Count fetches, not searches,** for eligibility, or count a search only when it led to a page lookup had nothing on. Pypi's loop also needs the subdomain fix.
- **Warm writes on related pages.** Even legitimate warm cards (a second page for a related question) rarely pay back at 3 reps. A stricter test would allow page cards only in runs where lookup returned nothing for the site.


## 2026-10-30: enforced-0.2, list `answers` accepted (`--iteration enforced-0.2`, results in `out_enforced-0.2/`)

Same as enforced-0.1, with one registry change: a page card whose `answers` is a list of strings has it joined with "; " before any check, so it's stored on the first write instead of rejected. Agents still send a list almost every time. No-write baselines and the baseline row are copied from `out_enforced-0.1/`. All four registry arms, hard set, reps 1-3 in parallel. 216/216 correct.

Before the run, `verify` found three easy-set answers had moved (not used here, fixed for later): openvsx rust-analyzer 0.4.3098 → 0.4.3101, amo Dark Reader 4.9.133 → 4.9.134, and the Claude docs dropped "32 MB for standard endpoints". The claude-vision related question now asks for the Messages request limit on the first-party API (128 MB).

| Mean per-task change vs no-write | route-0.1 | lean-0.1 | lean-0.2 | enforced-0.1 | enforced-0.2 |
|---|---|---|---|---|---|
| Write cost | +19.7k | +9.9k | +9.9k | +15.6k | +9.6k |
| Warm same, all | +13% | +1% | +2% | +11% | -1% |
| Warm related, all | +14% | -6% | +5% | +20% | +11% |
| Read-only related, all | -13% | -16% | -14% | -18% | -15% |
| Warm related, hard_access / docs / coding | +44% / +35% / -38% | +13% / +6% / -37% | +8% / +14% / -8% | +1% / +80% / -22% | +17% / +31% / -16% |
| Cold runs that stored a page card, coding | 100% | 33% | 50% | 72% | 50% |
| Write cost recovered within 2 reuses | 1/18 | 6/18 | 4/18 | 5/18 | 5/18 |

- **The retries are gone.** Writes that hit a schema rejection fell from 36 of 42 stored to 6 of 37. The six left are real limit violations: `route/notes` over 200 characters (6) and one `route/select` sent as a string. Write cost fell from +15.6k to +9.6k, as low as lean-0.1, and pypi's write cost halved (+35.5k → +16.9k) because its search-then-write loop no longer pays a retry each time.
- **Docs are less bad, for the same reason.** Warm related on docs went from +80% to +31%. Warm agents still write on 8 of 18 docs related runs (pypi and gha 3/3, heroku 2/3), but each write now takes one turn. gha +39% and pypi +109% are still the worst tasks.
- **Coding stored fewer cards this time, and that has nothing to do with the change.** 9/18 coding cold runs stored a card, against 13/18. mdn wrote 0/3 after 4 fetches each (3/3 before), so its warm related runs found nothing and came out +39% (enforced-0.1 -38%). Bash stored 2/3 and rust 1/3. The note said "would store" on all of them. Whether an eligible agent writes is still up to it.
- **nginx write cost doubled (+105k)**, but from fetching, not writing: cold r1/r2 took 6 and 5 fetches of the 20k-token page (4 and 4 before). There's still one `notes` rejection per nginx run.
- hard_access warm related moved from +1% to +17%, but all of that is artifacthub (-11% both times) and sonatype (-41% → +51%: one of three warm runs wrote a card). The other four are unchanged at about +15%, which is the write rule's length in the prompt.

Verdict: accepting a list is a clear win on what it targets, and the fixed cost of writing is now as low as it's been (+9.6k). Overall it's still worse than lean-0.1 (+11% vs -6% warm related). What's left is docs agents writing on related pages, plus coding cold runs that don't write when they should. With 3 reps, which tasks end up carded swings the totals by about as much as anything we've changed.

## Next

- **Raise or truncate `route/notes`.** It's the only remaining schema retry (6 of 37 writes, every nginx run). Truncating at 200 characters, with a "(truncated)" marker, would remove it.
- **Show only refusals**, and **count fetches, not searches**: both still apply, aimed at the docs writes.
- **More reps, or fixed cold registries.** Warm results depend mostly on whether the cold run happened to write. To test a reading-side change, reuse one set of cold registries across policies, so the comparison isn't redone on new cold luck.

## 2026-10-30: coldonly-0.1, only cold agents write (results in `out_coldonly-0.1/`)

lean-0.1 is the best policy so far. This tests one structural change against it: cold agents write under the lean rule, and warm agents only read (no write rule in the prompt, told not to call write). It uses lean-0.1's own cold registries, so cold luck is the same on both sides. `warm-related-nowrite` already existed in `out_lean-0.1/`. The new `warm-same-nowrite` arm (hard set, reps 1-3, 54 runs) reads the same registries. Rows and cold registries were copied from `out_lean-0.1/`. 54/54 correct.

| Mean per-task change vs no-write | lean-0.1 (warm agents write) | coldonly-0.1 |
|---|---|---|
| Write cost (cold) | +9.9k | +9.9k (same runs) |
| Warm same, all | +1% | **-3%** |
| Warm related, all | -6% | **-16%** |
| Warm same, hard_access / docs / coding | +12% / +8% / -18% | -9% / 0% / -1% |
| Warm related, hard_access / docs / coding | +13% / +6% / -37% | -4% / -6% / -38% |
| Write cost repaid within 2 reuses | 6/18 | 7/18 |

- **coldonly-0.1 beats lean-0.1** on both questions overall, and in every group except coding same. Part of the gain is the write rule's length: dropping it from warm prompts saves about 1.5k per run, which is +10-15% on the ~11k one-fetch tasks (pypi, r2, render, the registry APIs). The rest is warm writes that never paid back (gha same, 4-5 fetches and a write: +20-70%).
- **Coding same (-18% → -1%) is noise, not a loss.** lean-0.1's cold runs left a record for only 6 of 18 coding tasks and 1 of 18 docs tasks, so most warm runs on both arms had an empty registry. Split by registry:

  | Mean change vs no-write | Registry had records (18 runs) | Registry empty (36 runs) |
  |---|---|---|
  | Same, lean-0.1 warm / read-only | -18% / **-27%** | +19% / +15% |
  | Related, lean-0.1 warm / read-only | +7% / **-6%** | -1% / -8% |

  Where a record exists, reading without writing is better on both questions. In the empty-registry runs both arms are really no-registry runs, but they still range from -8% to +19%: outliers like git-gc r1 (84k, 5 fetches), bash r1 (96k) and nginx r2 (70k) all had empty registries. That spread is the noise floor at 3 reps.
- The viability bar still fails overall (-16% related, bar -30%). Coding related (-38%) passes, as it has under every route-card policy.

Verdict: warm agents shouldn't write. With that settled, the limit is what cold agents leave behind. lean-0.1 leaves too little (no record for most coding and docs tasks), and the route rule leaves a lot at about twice lean-0.1's write cost.

## Next

- **Cold-side policy, with warm agents read-only.** Compare route-0.1, lean-0.1 and enforced-0.2 cold registries, all scored read-only. Read-only related arms exist for all three: route-0.1 -13% (coding -43%), lean-0.1 -16% (-38%), enforced-0.2 -15% (-33%). Each now needs a `warm-same-nowrite` arm on its own registries, then the comparison is write cost against read-only savings.
- **Truncate `route/notes`** at 200 characters instead of rejecting it (the last schema retry).
- **More reps for the deciding run.** The empty-registry spread (-8% to +19%) is as big as most effects measured here.

## 2026-10-30: miss-0.1, write on miss (`--iteration miss-0.1`, results in `out_miss-0.1/`)

All agents get the same prompt, and its step 3 is one line ("call write only if a lookup result asks for breadcrumbs"). The first lookup in a run that finds no page card and no site URL pattern for its target ends with the lean rule and the card format (~450 tokens). The registry refuses a page card for a page that already has one. `route/notes` and `access/notes` over 200 characters are now truncated rather than rejected, in every mode. No-write baselines and the baseline row are copied from `out_lean-0.1/`. Four registry arms, hard set, reps 1-3. A usage limit cut off 120 warm runs, and a memory-pressure kill stopped the first rerun; the rest were rerun one rep at a time. 215/216 correct: one read-only gha related run (empty registry) concluded no background-step limit is documented.

| Mean per-task change vs no-write | lean-0.1 | coldonly-0.1 | miss-0.1 |
|---|---|---|---|
| Write cost | +9.9k | +9.9k | **+4.4k** |
| Write cost, hard_access / docs / coding | +8.2k / +3.3k / +18.3k | same | +6.9k / +2.6k / +3.6k |
| Warm same, all | +1% | **-3%** | +4% |
| Warm related, all | -6% | **-16%** | -9% |
| Warm related, hard_access / docs / coding | +13% / +6% / -37% | -4% / -6% / -38% | +4% / +3% / -35% |
| Read-only related, all | -16% | -16% | -5% |
| Write cost repaid within 2 reuses | 6/18 | 7/18 | 7/18 |

- **The registries are nearly empty under both lean-0.1 and miss-0.1.** For 12 of 18 tasks, cold agents left no record in any rep under either policy, and the two policies' registries differ on only two tasks (nginx: lean-0.1 carded 2 of 3, miss-0.1 0; heroku: lean-0.1 1, miss-0.1 0). Coding cold runs wrote 6/18 under both. Most of the read-only gap (-16% vs -5%) is those two tasks plus baseline noise: pypi, sonatype and git-gc had empty registries under both, yet lean-0.1's read-only runs were 24-46% cheaper than miss-0.1's.
- **Clean signal: the prompt overhead mostly goes away.** On one-fetch tasks with empty registries, warm related went from +13-18% under lean-0.1 to +4-11% under miss-0.1 (terraform and galaxy +18% → +4%, render +14% → +5%, compose +15% → +11%). The note goes only to agents that miss, and ignoring it costs one read.
- **Write cost halved** (+9.9k → +4.4k) with the same number of coding writes, mostly because coding cold runs no longer carry the rule through every turn (+18.3k → +3.6k).
- Warm agents wrote in 2/54 same and a few related runs: the refusal held, and no card was written twice.

Verdict: miss mode is the deployable shape. One prompt, a smaller fixed cost than lean-0.1, and the database still grows on misses. But the hard set can't show what the registry is worth when cold agents leave almost nothing: 12 of 18 tasks never get a record. The next step is the cold side: getting a miss to leave a record when the answer took more than one fetch.

## Next

- **Cold-side policy inside miss mode.** The note's lean rule is followed about a third of the time on multi-fetch pages. Try the route rule's unconditional "write a page card" in the note, plus the enforced refusal for one-fetch runs (so the decision isn't left to the agent), or harness-side eligibility in the note itself ("this run has taken N fetches: write a card").
- **More reps, or tasks known to need several fetches.** With most registries empty, a task's result rests on cold luck and baseline noise (±35% on an empty registry).

## 2026-10-30: miss-0.2, page card enforced (`--iteration miss-0.2`, results in `out_miss-0.2/`)

Miss mode with the cold side changed. The prompt and the one-line step 3 are the same. Three things differ:

- The first lookup that misses ends with the route rule's "write a page card for the page that held the answer whenever getting it took more than one fetch or render", instead of the lean rule's conditions.
- The registry refuses page cards from runs with at most one fetch or render, counting fetches only (searches don't count, which closes pypi's search-then-write loop), and for URLs a stored site pattern covers. It still refuses a second card for a carded page. Site records are always stored.
- The web server and registry share the run's `calls.log` (no WebSearch hook). In a run that got the miss note, only the first fetch or render that makes a card storable ends with "this run has now taken N fetches, so write would store a page card from it: write one ... before answering." Under enforced, a note on every fetch seemed to invite writes.

Smoke (`out_miss-0.2_smoke/`, cold, rep 1): git-gc got the nudge on its second fetch (raw `gc.adoc`) and stored a card, and puppet fetched once and stored only a site record. No-write baselines and the baseline row were copied from `out_miss-0.1/`. Cold reps 1-3 ran in parallel, then the three warm arms ran in parallel, one rep at a time. Nothing was interrupted. 215/216 correct: one warm-related gha run (registry had a card for the matrix page, not the limits page) searched twice and concluded the limit isn't documented.

| Mean per-task change vs no-write | lean-0.1 | coldonly-0.1 | miss-0.1 | miss-0.2 |
|---|---|---|---|---|
| Write cost | +9.9k | +9.9k | +4.4k | +7.3k |
| Write cost, hard_access / docs / coding | +8.2k / +3.3k / +18.3k | same | +6.9k / +2.6k / +3.6k | +5.7k / +4.8k / +11.4k |
| Warm same, all | +1% | -3% | +4% | **-5%** |
| Warm related, all | -6% | **-16%** | -9% | -13% |
| Warm same, coding | -18% | -1% | -7% | **-25%** |
| Warm related, hard_access / docs / coding | +13% / +6% / -37% | -4% / -6% / -38% | +4% / +3% / -35% | -2% / +1% / -37% |
| Read-only related, all | -16% | -16% | -5% | -14% |
| Coding cold runs that stored a page card | 6/18 | same | 6/18 | **13/18** |
| Tasks with a record in some rep | | | 7/18 | **12/18** |
| Write cost repaid within 2 reuses | 6/18 | 7/18 | 7/18 | 8/18 |

- **The cold side is fixed where it was aimed.** git-gc, nginx, mdn and bash stored a card 3/3 (under miss-0.1: git-gc and nginx 0/3), and heroku, gha and sonatype now get cards on their multi-fetch runs. All 23 eligible cold runs (2+ fetches) got the nudge, and 18 stored a page card. Sonatype r1 wrote a site record with the API pattern instead, which is the better record. The other four (rust r2/r3, gha r3, heroku r2) kept fetching after the nudge on their second fetch and never came back to it.
- **The refusal held without being tested.** No card was refused in any cold run: one-fetch agents (compose, github, r2, render, pypi, jetbrains) wrote nothing, and API sites wrote only site records. Warm agents stored a record in 4/54 same and 5/54 related runs (heroku related 2/3), and none were refused either.
- **Coding pays for it.** Warm same on coding is -25%, the best of any policy (nginx -71%, bash -60%, mdn -40%), and related is -37%. Write cost on coding tripled against miss-0.1 (+3.6k → +11.4k), but that's the cards being written. It's still under lean-0.1's +18.3k, because the rule rides with one tool result instead of the system prompt.
- **Rust is the outlier.** Warm same +29% with one card in three reps, and the related baseline is 234k (11 fetches), so its -65% related is mostly baseline variance (read-only related on the same registries is only -13%).
- **hard_access and docs are flat.** One-fetch tasks sit at +1-13%: the read-only runs on the same registries are +1-4%, so the rest is warm agents that miss (another subdomain, or a different page) and carry the ~450-token note. That's the fixed cost of miss mode.

Verdict: miss-0.2 is the best write policy where warm agents also write. It beats miss-0.1 on both questions (-5% / -13% vs +4% / -9%), and it's close to only-cold-writes on related (-13% vs -16%) with one prompt for every agent. The registries finally hold records for most multi-fetch tasks (12/18), so read-only related is -14% against miss-0.1's -5%. The viability bar still fails overall (-13% vs -30%), and passes only on coding, as before. The hard set's one-fetch tasks (10 of 18) can't save anything, because they're already one fetch.

## Next

- **Nudge again at answer time.** 4 of 23 eligible cold runs ignored a nudge that arrived mid-search. Repeating it on later fetches, or once more when the run has gone past 3 fetches without a write, would catch them.
- **warm-same-nowrite on miss-0.2 registries**, to score miss-0.2 with only cold agents writing on the same registries (coldonly-0.1 was lean-0.1's best shape).
- **The viability bar on multi-fetch tasks only.** On one-fetch tasks the registry can only add cost. Score the bar on tasks whose no-write run takes 2+ fetches, or add harder tasks, since that's where breadcrumbs could pay.

## 2026-10-30: miss-0.3, answer-time nudge; multi-fetch bar, only-cold-writes on miss-0.2 (`--iteration miss-0.3`, `out_miss-0.3/`)

Three follow-ups to miss-0.2.

**Multi-fetch bar.** `report.py` adds a `hard/multi-fetch` group: tasks whose no-write related run averages 2+ fetches and searches (`MULTI_FETCH`). That's 9 tasks: sonatype, render, heroku, gha, git-gc, nginx, rust, mdn and bash. The viability bar is scored on it too. Under miss-0.2, warm related on multi-fetch is -30% (29.8%, so marked fail), read-only related -28%, and the write is repaid within 1.2 reuses (median).

**Only cold agents write, miss-0.2 registries** (`warm-same-nowrite` added to `out_miss-0.2/`, 54/54 correct):

| Mean per-task change vs no-write | lean-0.1 registries | miss-0.2 registries |
|---|---|---|
| Read-only same, all / multi-fetch | -3% / -3% | **-17% / -36%** |
| Read-only related, all / multi-fetch | -16% / -28% | -14% / -28% |
| Read-only same, coding | -1% | **-37%** |
| Write repaid within 2 reuses (read-only related) | 7/18 | 9/18 |

The miss-0.2 registries are the best yet for the same question, because they hold records for the multi-fetch coding pages that lean-0.1's cold runs skipped. Same-question multi-fetch (-36%) clears the 30% bar. Related is unchanged, at about -28% on multi-fetch under both.

**Answer-time nudge (`--iteration miss-0.3`).** miss-0.2 plus a `Stop` hook (`bc/stop_nudge.py`). The registry logs each stored record and the web server logs its nudge to `calls.log`. If a run was nudged and stored nothing, the hook blocks the stop once ("call write with a page card ... then repeat your final ANSWER line"). Grading now falls back to the last ANSWER line anywhere in the run's text. No-write baselines were copied from `out_miss-0.1/`. A usage limit cut off 160 warm runs, a memory-pressure kill stopped the first resume, and a resume-script bug (Windows `\r` in task ids) ran only one task per arm. Everything missing was rerun two arms at a time, and the limit-hit rows were dropped (original kept in `results.before_limit_cleanup.jsonl`). All 270 runs: 269/270 correct. The miss is the same gha warm-related run as under miss-0.2: it searched and concluded no limit is documented.

- **The hook does its job.** 24 of 24 nudged cold runs stored a record (miss-0.2 19/23). It fired in 4 cold runs (gha r3, heroku r1/r3, rust r2), and all 4 then wrote. Rust now has a card in 3/3 reps.
- **It fired in only 8 runs** (4 cold, 1 warm same, 3 warm related). Every other run is miss-0.2 under another name, so most of the difference between the two runs is run variance. Rust shows how big that is: cold r1 took 312k with 5 fetches (miss-0.2 86k), and warm-same r2 took 402k although a card existed. Rust alone moves the mean write cost from +7.3k to +14.1k.

| Mean per-task change vs no-write, without rust (17 tasks) | miss-0.2 | miss-0.3 |
|---|---|---|
| Write cost | +6.3k | +7.6k |
| Warm same / related, all | -7% / -10% | -5% / -5% |
| Warm same / related, coding (5) | -36% / -32% | -35% / -39% |
| Warm related, docs | +1% | +22% |
| Read-only related, all | -14% | -11% |
| Only cold writes, same / related, all | -17% / -14% | -10% / -11% |

- **Coding is unchanged and docs got worse.** The docs loss is warm-related agents that miss (the related question needs another page), take a second fetch, get the nudge and write. That happened in 3/3 runs each on render (+46%) and heroku (+26%), against 1/3 and 2/3 under miss-0.2. The mid-run nudge does this in both modes. Docs read-only related is also worse (+14% vs -2% under miss-0.2), mostly gha (5.3 fetches, +46%) and pypi (+58%). Nothing changed there besides the registries, so at 3 reps it reads as noise.

Verdict: the answer-time hook closes the last cold-side gap (every eligible cold run leaves a record). But it acts in so few runs that it can't move the totals, and at 3 reps it's swamped by single-run variance (rust ±300k). miss-0.2 stays the policy to beat. The clearest result in this batch is the read-only one: with miss-0.2 registries, multi-fetch tasks clear the bar on the same question (-36%) and sit at -28-30% on related ones.

## Next

- **Don't nudge warm agents on related pages.** Docs loses whenever a warm agent with a related question writes a second card. Nudge (and hook) only when lookup found nothing for the site at all, not just nothing for the page.
- **More reps on multi-fetch tasks only.** The 9 multi-fetch tasks are where every policy difference shows, and where the noise is (rust, gha, heroku). 6+ reps of just those would be cheaper than more hard-set runs, and would tell miss-0.2 from miss-0.3.
- **Budget for the runs.** A full four-arm hard-set run is about 270 agent runs. It hit the 5-hour usage limit once and memory pressure once at 4 in parallel. Run 2 arms at a time.

## 2026-10-31: miss-0.4, no note for runs that have seen breadcrumbs (`--iteration miss-0.4`, `out_miss-0.4/`)

miss-0.3 with one change: the miss note (and so the mid-run nudge and the Stop hook) goes only to runs whose lookups have found nothing at all. Once any lookup in a run returns a record, the note is never sent, even when the agent later looks up a different site. Under miss-0.3 a warm agent with a related question on a carded site got the note, took a second fetch, got nudged and wrote a second card. That was the docs loss (render +46%, heroku +26%).

Cold runs start from an empty registry, so cold miss-0.4 behaves exactly like cold miss-0.3. The run therefore reuses miss-0.3's cold runs and registries, and reruns only `warm-same` and `warm-related` on the 9 multi-fetch tasks, reps 1-3. It's a paired comparison on identical registries. Baselines and read-only arms are copied from `out_miss-0.3/`.

54/54 correct. Nothing was interrupted.

| Mean per-task change vs no-write, multi-fetch tasks (9) | miss-0.3 | miss-0.4 | Read-only, same registries |
|---|---|---|---|
| Warm same | -11% | **-32%** | -25% |
| Warm same, without rust | -35% | -35% | -25% |
| Warm related | -21% | **-27%** | -30% |
| Warm related, without rust | -21% | -26% | -30% |
| Warm related runs that wrote | 10/27 | 6/27 | 0 |

- **The fix works where it applies.** Heroku, which has a card in all three reps, went from +26% (3/3 related runs wrote a second card) to -19% (none wrote). Nginx related went from -47% to -62%.
- **Render is not that problem.** Its cold runs left no record in any rep (one fetch, nothing to card), so its warm runs are really cold runs. Both policies send the note and both cost +46%: every related run fetched `/docs/free` twice, got nudged and wrote. That's what a nudged write costs on a page that is cheap anyway. The miss-0.3 verdict blamed render's docs loss on warm agents on a carded site, which was wrong for render.
- **A card under another site counts as a miss.** git-gc r2's card is for the raw `gc.adoc` (raw.githubusercontent.com), and rust r2's is for a GitHub release page. A warm agent looks up git-scm.com or doc.rust-lang.org, finds nothing, and gets the note. Those are 2 of the 6 related runs that wrote. The other 4 are on empty registries (render, sonatype r1).
- **Same question is unchanged without rust** (-35% under both). A warm-same run hits its own card and never got the note under either policy. Rust's +177% → -13% is one 402k miss-0.3 run.
- gha related +5% → +27% (3.3 → 4.7 fetches, no writes in either) is run variance.
- Warm related under miss-0.4 (-26%) is now close to read-only on the same registries (-30%): warm agents on a carded site behave almost read-only. miss-0.4's warm related falls short of the 30% bar, and read-only on these registries is right at it.

Verdict: miss-0.4 replaces miss-0.3. It costs nothing on cold runs and removes the second-card writes on carded sites. On multi-fetch tasks it's -32% same and -27% related, against -11% and -21%. What's left is not a write-policy problem. Cards are filed under the site of the route's URL instead of the page the agent looks up, and one-fetch pages get nudged on a second fetch of the same URL.

## Next

- **Reps 4-6 on multi-fetch tasks** (cold, both warm arms, both read-only arms, and new no-write baselines: about 190 runs), once the two fixes above are in, so the extra reps measure the final policy.

## 2026-10-31: miss-0.5, pull threshold and lookup-site filing (`--iteration miss-0.5`, smoke in `out_miss-0.5_smoke/`)

Two fixes on top of miss-0.4, both from the miss-0.4 runs:

- **No card from a run that pulled little.** Counting distinct URLs toward the nudge would have been wrong: 20 of 32 miss-0.4 nudges came on a second fetch of the same URL (the first `section=` guess fails, then `start=` or the right anchor works), and those are the nginx, bash, mdn and heroku cards behind the -65% to -72% same-question savings. What separates render is size. The web server now logs the tokens each fetch or render returned. Under `--iteration miss-0.5`, the nudge and page cards need the run's fetches to have returned 2,000+ tokens in all (`MIN_PULL` in `run.py`). Every cold card that later saved tokens came from a run that pulled 2,286+ (git-gc is the smallest). Render's nudged runs pulled ~450 and sonatype's related r1 545.
- **Cards are filed under a site the run looked up.** git-gc r2's cold agent looked up `git-scm.com`, then wrote its card with `url` set to the raw `gc.adoc`, so it was filed under raw.githubusercontent.com, where no warm agent looks. The registry now refuses a page card whose `url` host the run never looked up, and says to file it under the page on the looked-up site, with the raw source as `route.url`.

Expected effect is small: about 5 points on multi-fetch related (render +46% → about +1%), and 1-2 points from filing (git-gc r2 only).

Smoke (`out_miss-0.5_smoke/`, rep 1): git-gc cold pulled 2,251 tokens over two fetches, was nudged, and filed its card as `page:git-scm.com/docs/git-config` on the first try. Render cold fetched once and wrote nothing, as before. Render warm-related on that empty registry fetched `/docs/free` twice (413 tokens), got no nudge, wrote nothing and took 16.0k (+10% vs no-write, against +46% under miss-0.4).

### Full run (`out_miss-0.5/`, multi-fetch tasks, reps 1-6)

The 9 multi-fetch tasks, reps 1-6, all four registry arms: 324 new runs, plus the no-write baselines for reps 1-3 copied from miss-0.4. Driver: `out_miss-0.5/drive.py`, two runs at a time. Phase 2 hit the weekly usage limit at 03:45. The driver retried every 15 minutes until the 15:00 reset, then finished. No run was lost, and limit-hit rows are kept out of `results.jsonl`. 324/324 correct.

| Mean per-task change vs no-write, multi-fetch tasks (9) | miss-0.3, r1-3 | miss-0.4, r1-3 | miss-0.5, r1-3 | miss-0.5, r1-6 |
|---|---|---|---|---|
| Write cost | +24.7k | same runs | | **+15.8k** |
| Warm same | -11% | -32% | -42% | **-44%** |
| Warm related | -21% | -27% | -37% | **-32%** |
| Read-only same | | | -42% | -44% |
| Read-only related | -30% | same runs | -30% | -26% |
| Warm runs that wrote | 13/54 | 9/54 | | **0/216** |
| Write repaid within 2 reuses (median) | | | | 6/9 (1.14) |

- **The cold side is now deterministic.** 8 of 9 tasks have a page card in all 6 reps. Render has none in any rep: one fetch of 2.5k tokens, so the registry has nothing to save, as intended. 48 of 54 cold runs were nudged and all 48 stored a card.
- **Filing fired exactly where predicted.** The refusal fired twice, both on git-gc's raw `gc.adoc` card (r2, r4), and both agents re-filed it under `git-scm.com/docs/git-config`. git-gc warm same went from -18% (miss-0.4, r2 misfiled) to -57%.
- **The pull threshold removed the cheap writes.** Render related went from +46% to +12%: no nudge, no write. Across all four warm arms, no warm agent wrote anything (0/216). Warm agents now behave read-only on their own.
- **Viability bar** (report.py): warm related -32% on the 9 tasks, so it **passes** (bar -30%). Same question -44%, fetches 3.3 → 1.1 (same) and 3.8 → 2.2 (related), accuracy unchanged, write repaid within 1.14 reuses (median). Read-only related is -26%, so that row fails. Since no warm agent wrote, warm related and read-only related differ only in step 3 of the prompt. The 6-point gap between them is rep noise, which puts the true related cut at about -26% to -32%, right at the bar.
- **Noise.** Per-rep means of warm same are -41% to -46% (sd 2 points) and of warm related -23% to -38% (sd 6). Baselines move too: git-gc and rust no-write runs in reps 4-6 differ from reps 1-3 by +86% / -64% and +83% / -70%. Six reps is about the least that separates policies a few points apart on related questions.
- report.py's `hard/multi-fetch` group now has 7 tasks: with 6 reps of baselines, sonatype and render average under 2 fetches. Its numbers are -56% same / -36% related, passing both on warm related and on payback, with read-only related at -28%. The 9-task row is the one comparable with earlier runs.
- miss-0.4 and miss-0.5 are not paired, since miss-0.5 ran new cold registries. Compared on reps 1-3 with the same baselines, miss-0.5 is 10 points better on both questions (-42% / -37% vs -32% / -27%).

Verdict: miss-0.5 is the first policy to pass the viability bar on warm related questions, on the tasks where breadcrumbs can pay. Same-question savings (-44%) are large and stable. Related savings sit at about 30%, inside rep noise of the bar. It writes on the cold side only, where a card saves something, and no warm agent wrote.

## Next

- **Related questions are the weak side.** Read-only related is -26%: warm agents find the card, but the related answer is on another page (gha limits vs workflow-syntax, rust `pop_if`). What a card's `answers` and links say decides whether a related question can use it.

## 2026-10-31: miss-0.5 on the easy set and the one-fetch hard tasks (`out_miss-0.5/`, reps 1-3)

`python out_miss-0.5/drive.py cheap`: the 24 easy tasks and the 9 one-fetch hard tasks, cold and both warm arms, reps 1-3. The easy set needed new no-write baselines (its only earlier run, `out_rep1_oldrule/`, predates narrow-0.1). The one-fetch hard baselines are the rows miss-0.1 to miss-0.3 used, copied from miss-0.3. Read-only arms were left out, since no warm agent wrote in the multi-fetch run. 441 runs. The 5-hour limit hit at the start of phase 2, a memory-pressure kill stopped the driver while it waited, and it resumed after the reset with nothing lost.

Before the run, `verify` found openvsx rust-analyzer had moved from 0.4.3101 to 0.4.3102. It moved again to 0.4.3103 during the run: two warm-same runs answered 0.4.3103 and were regraded correct (marked `regraded`), and `tasks.yaml` now expects 0.4.3103. 441/441 correct.

| Mean per-task change vs no-write, reps 1-3 | Tasks | Write cost | Warm same | Warm related | Medians |
|---|---|---|---|---|---|
| Easy, all | 24 | +2.6k | +11% | +13% | +7% / +7% |
| Easy, hard_access / docs / coding | 8 / 8 / 8 | +1.6k / +2.2k / +3.9k | +13% / +14% / +6% | +34% / +7% / -3% | |
| Easy, one fetch | 20 | +2.0k | +12% | +16% | +7% / +7% |
| Easy, 2+ fetches | 4 | +5.2k | +4% | -3% | +6% / -4% |
| Hard, one fetch | 9 | +3.0k | +20% | +8% | +10% / +9% |

- **On one-fetch pages miss-0.5 costs about +7% (median):** a lookup plus, when it misses, the ~450-token note. It can't save anything there. Means run higher because of single expensive runs: jsdelivr related +142%, depsdev related +67%, jetbrains same +62%, pypi same +57%, crates same +51%, letsencrypt same +51%.
- **Same as earlier policies on the hard one-fetch tasks**, on the same baselines: warm same / related +8% / +7% (miss-0.1), +9% / +4% (miss-0.2), +21% / +9% (miss-0.3), +20% / +8% (miss-0.5). miss-0.3 and miss-0.5 both have the Stop hook, but it fired in only one of these runs (miss-0.3, pypi related r1). The gap to miss-0.1/0.2 comes from jetbrains and pypi same, so it's single-run variance at 3 reps.
- **Write cost is small** (+2-3k): one-fetch cold runs get no nudge and store no page card. Site records with API URL patterns are still stored (openvsx, terraform, galaxy and puppet in 3/3).
- **Warm agents wrote in 13 of 198 runs, all of them misses.** Every one first got the miss note, because its cold run had left nothing for that site. 10 of the 13 were site records for API sites (crates, npm, jsdelivr, depsdev, artifacthub, jetbrains), which are stored at any fetch count. The other 3 were page cards after a nudge (discord, tailwind, depsdev). None wrote over an existing record.
- **The few easy tasks that need several fetches do save on related questions:** python-json-bytes -21% / -25%, go -19% related, tailwind -17% related. That's only 4 tasks at 3 reps.

Verdict: miss-0.5 does no harm beyond its fixed cost on cheap pages. About +7% median on a page answered in one fetch, against -44% same / -32% related on pages that take several fetches. Whether it pays in deployment depends on that mix: with the +7% and -32% figures, it breaks even when about 1 lookup in 6 is for a multi-fetch page.

## Next

- **Cut the fixed cost on one-fetch pages.** The note is ~450 tokens on every miss. A shorter note, or sending it only after the run's second fetch (when a card could be stored), would remove most of the +7%.
- **Related questions** (above) are the other lever.

## 2026-10-31: miss-0.6, one-fetch site records (`--iteration miss-0.6`, cold runs in `out_miss-0.6_smoke/`)

miss-0.5 with one sentence added back to the miss note, inside the page-card bullet: "If you got the answer with one fetch or render, write no page card, but a site record is still worth writing if it gives a URL pattern lookup lacked."

Why: lean-0.1 added that sentence after a smoke run showed puppet's one-fetch site record carrying a useful `{owner}-{name}` pattern, and miss-0.1's note kept it. miss-0.2 rebuilt the note from the route rule to get page cards on multi-fetch pages, and the sentence went with the lean rule's skip list. Nothing in this log gives a reason to drop it, and the registry stores site records at any fetch count. Since then one-fetch API runs write site records less often. jetbrains cold runs stored one in 3/3 under lean-0.1, lean-0.2 and miss-0.1, and in 0/3 under miss-0.2, miss-0.3 and miss-0.5. All six lean-0.1 and miss-0.5 cold runs fetched the same Marketplace API. With the record, lean-0.1's warm jetbrains runs read about 170 tokens instead of a 9k page (-92% uncached), against +43% under miss-0.5. enforced-0.1 saw the same effect ("the note reads as 'don't write' when it only covers page cards"). terraform, galaxy and puppet still get site records under miss-0.5, so the loss may be limited to opaque-ID patterns like jetbrains' `{pluginId}`.

To test: cold and warm runs on the one-fetch API tasks (hard: terraform, galaxy, artifacthub, puppet, jetbrains; easy: the 8 hard_access tasks), checking that site records come back without page cards from one-fetch runs.

**Smoke (rep 1, plus terraform reps 2-3).** jetbrains cold stored a site record with the `{pluginId}` pattern and no page card. But the record didn't mention the ~8k changelog payload, so the warm run fetched it whole: 23.2k, no better than the 23.5k baseline. lean-0.1's record had noted the size and fields, and its warm runs used `select` (11.9k, -49%). terraform stored its site record in 1/3 (miss-0.5 3/3), flathub 0/1, and compose wrote nothing.

**Site-record check (cold only, 5 reps).** The 13 one-fetch API tasks (8 easy hard_access, plus terraform, galaxy, artifacthub, puppet and jetbrains). miss-0.6 reps 1-5 in `out_miss-0.6_smoke/`, and miss-0.5 reps 4-5 in `out_miss-0.5_sitecheck/` so both have 5 reps (`run_sitecheck.sh`). 86 runs, all correct.

| Cold runs storing a site record | miss-0.5 | miss-0.6 |
|---|---|---|
| terraform / galaxy / artifacthub / puppet | 5 / 3 / 4 / 5 of 5 | 1 / 0 / 1 / 3 of 5 |
| openvsx / amo / crates / bundlephobia / npm | 4 / 2 / 1 / 3 / 2 | 2 / 0 / 0 / 2 / 2 |
| jsdelivr / jetbrains | 0 / 0 | 2 / 1 |
| flathub / depsdev | 0 / 0 | 0 / 0 |
| All 13 tasks | **29/65** | **14/65** |

- The sentence halved site records. The two sites it gained (jsdelivr, jetbrains) gained 3 between them, and the sites that reliably wrote under miss-0.5 lost 16. jetbrains, the target, got only 1/5.
- This matches terraform's earlier dips: lean-0.2 (1/3) and enforced-0.2 (0/3) also lead with what not to write after one fetch. "Write no page card, but..." reads as "write nothing".
- No one-fetch run wrote a page card in either iteration.
- 14 of miss-0.5's 29 records already note a `select` or a size, which is what the jetbrains record lacked.

Verdict: miss-0.6 is a negative result, and miss-0.5 stays the policy. A sentence that leads with what not to write suppresses writes. A next try would change only the site-record bullet, in positive terms: write one whenever an API or raw-source URL works for other pages, even after one fetch, and give the fetch arguments that keep the result small and its rough size.

## 2026-11-01: field data from one developer's transcripts (not an iteration)

A developer ran an aggregate-only script over their local Claude Code transcripts (835, in `~/.claude` and `~/.claude2`) and sent back counts. No text, URLs or domains were shared. A web call is `WebSearch`, `WebFetch` or a browser page load or read. A lookup is a run of web calls that ends at the next user message, or after GAP non-web tool calls in a row (GAP = 3 and GAP = 1 reported).

| | GAP = 3 | GAP = 1 |
|---|---|---|
| Web calls (search / fetch / browser) | 46 (17 / 26 / 3) | same |
| Lookups | 18 | 19 |
| Exactly one call | 9 (50%) | 9 (47%) |
| ...of which a fetch with no search before it | 8 | 8 |
| Fetches to a domain fetched in an earlier lookup | 12 of 29 (41%) | same |

84% of the transcripts are on one large codebase (Loom) with few, pinned dependencies, vendored upstream code and its own agent guides. 13 of 30 `WebFetch` calls went to GitHub, not split into own repos versus upstream.

- **Web lookups are rare here:** about one web call per 18 transcripts. Whatever breadcrumbs save, the total here is small.
- **Half the lookups are one-fetch,** the case where miss-0.5 can only add cost (about +7% median, above). Multi-fetch tasks are -27% / -32% under miss-0.4. Weighted 50/50 by lookup count, that's roughly -10 to -12%. Even at zero cost on one-fetch lookups it's about -15%, still under the 30% bar. Multi-call lookups probably use more tokens, so a token-weighted blend would be better, but the report counts calls only.
- **One-fetch lookups are almost all a known URL with no search first** (8 of 9). The harness can see that before the fetch runs, so it may be a usable signal for skipping the lookup.
- **41% repeat-domain fetches** is the case site records and warm-related runs are built for.

Limits: 18 lookups (one lookup moves the single-call share by about 5 points), one developer, one main codebase, no research or shopping lookups, the two folders may overlap, and transcripts only go back about 30 days.

## Next

- **Estimate demand without developers.** The developer's top suggestion: ask the model versioned API questions about popular libraries and check the answers against the docs. The error rate by library and release date shows where a lookup would change the result. Public agent instruction files (`CLAUDE.md`, `AGENTS.md`) that point at docs are a second, passive signal.
- **Skip or fold the lookup on known-URL fetches.** Skip the registry lookup on a first fetch with no search before it, or return the breadcrumb inside the fetch result so a miss costs almost nothing.
- **Ask the developer for:** tokens per lookup, a folder-overlap check, and GitHub own versus upstream.

## 2026-11-01: probe-0.1, library-docs demand (`out_probe-0.1/`, report in `research/knowledge-gap-probe-report.md`)

The real question from the field data: are multi-fetch docs lookups common enough for breadcrumbs to pay? 72 questions (`research/probe/questions.yaml`), 6 per library on 12 libraries in 6 groups. Each names a version and is checked against a file pinned to a release tag. 3 are drawn from the documented API, 3 from changelog entries since 2025-06. Arms, all Sonnet and miss-0.5:
- memory: no tools.
- open: web tools, no registry, no rule to look up.
- forced lookup: cold-nowrite and cold-nowrite-related.
- breadcrumbs: cold → warm-related, warm-related-nowrite and warm-same, on pairs within each library (questions 1→2, 3→4, 5→6), 2 reps.
- oracle: the source URL in the prompt.

576 scored runs (504 main, 72 oracle). The usage limit hit twice and the runs were retried after the reset.

| | Result |
|---|---|
| Open: looked up | 71% (random 56%, changed before cutoff 84%, after 91%); 99% correct |
| Open lookups with 2+ web calls | 67% (forced: 74%, median 29k total) |
| Cold runs storing a record | 10/36 rep 1, 14/36 rep 2 (20/36 rep 1 were one-fetch) |
| warm-related vs cold-nowrite-related | median +9%, token-weighted **+22%** |
| warm-related-nowrite (read only) | median −0%, token-weighted **−3%** |
| warm-same, cold stored | median −37%, token-weighted −20% (n=10) |
| Oracle | median −22%, token-weighted **−12%**, mean +26% |

- **Lookups with several fetches are common.** When an agent checks a library fact, it looks up on its own and usually needs 2+ calls. It looks up on 95% of the questions it was unsure about from memory. Only 1 of 72 open runs was confidently wrong without looking (Express 5.3 `req.fresh`, after the cutoff).
- **Breadcrumbs don't make them cheaper.** Every stored record was a page card filed under the page the cold agent landed on (GitHub repo, PyPI, readthedocs), and no site records were written. A related question needs another page and enters by another URL, so lookups miss. Then the warm agent pays for the miss note and the write.
- **Even a perfect route saves only 12%** (token-weighted). The cost of a docs lookup is mostly agent overhead and the content, and the true source is often a large module file.
- **Field data: lookups are a small part of a session.** This machine's 63 transcripts (aggregate counts only, same definitions as the developer's script): 29% of sessions have any web call, 41-46% of lookups are one call, and web results are 8.3% of tool-result tokens.

Verdict: no win on library docs for coding agents. That's the plan's "no win" branch for this use case. The remaining case is access knowledge for hard sites (multi-fetch hard tasks, −27% to −32% under miss-0.4), whose real-world demand is untested.

## 2026-11-02: access-failure counts, this machine (not an iteration)

`research/scripts/access_failures.py` counts fetches that fail or come back near-empty, what the lookup does next, and whether the same site fails again in another session. Lookups are as in `lookups_local.py` (GAP=3). Failures are classed from the opening text of each result: blocked (401/403/429, bot checks), gone (404/410, "page not found"), too large, server error, redirect, and JavaScript-only or empty (the summarizer reports only a title or incomplete content). The classes were hand-checked against this machine's results. The script prints counts only; domains are kept in memory to count repeats.

| | This machine (64 transcripts) |
|---|---|
| Lookups / web calls | 44 / 203 (92 fetches, 111 searches) |
| Failed fetches | 14 (15%): gone 6, blocked 3, JS/empty 2, redirect 2, too large 1 |
| Lookups with an access failure (blocked, JS/empty, too large) | 5 (11%) |
| Web calls per lookup, clean vs with an access failure | median 2 vs 9 |
| After the first access failure | 42 more web calls in all, median 2; 3 lookups later fetched something, 2 never did; none switched to a browser tool |
| Domains with an access failure | 6, none failing in 2+ sessions |

- **Access failures are expensive when they happen.** Lookups that hit one ran to a median of 9 web calls.
- **They are rare, and they don't repeat.** 5 lookups in 64 transcripts. No site failed in two sessions, so no breadcrumb from an earlier session would have helped here.
- **Most failures are dead links, not hard sites.** Gone (404/410) is the largest class, mostly expired job postings, and a site record can't fix those.

Limits: one machine, mostly this research project plus some job-search sessions, about 30 days of transcripts, 5 access-failure lookups. A shared registry pools sites across users, so repeats across developers matter more than repeats on one machine. That needs the script run on other machines.

## 2026-11-02: miss-0.7, searches count toward the card bar (`--iteration miss-0.7`, `out_miss-0.7_probe/`)

Why: in probe-0.1 the related questions with the most room to save (oracle −33% median) were the ones whose cold run searched, fetched once and was refused a card, since miss-0.2 counts fetches only. miss-0.7 is miss-0.5 with `BC_SEARCHES=1`: a search counts toward the bar again, and the 2,000-token pull and miss-0.4's rules stay. miss-0.2 had stopped counting searches because of pypi's search-then-write loop, before miss-0.4 and miss-0.5 narrowed who writes.

Fixes found on the way: miss mode never logged WebSearch calls (only enforced-* installed `log_search.py`), so miss-0.7 installs that hook alongside the Stop hook. `BC_NOTE_SITE` is now on for miss-0.6 only (it was `MISS[5:]`).

Run: probe-0.1's 36 pairs, reps 1-2, with cold, warm-related and warm-related-nowrite under miss-0.7. That's 216 runs, scored against probe-0.1's no-registry rows (copied; they don't depend on the policy). The 5-hour limit hit once and the driver waited. `out_miss-0.7_probe/report.py` gives the token table.

| | miss-0.5 | miss-0.7 |
|---|---|---|
| Cold runs storing a card (of 72) | 24 | 30 (5 after a search and one fetch) |
| Warm-related, tokens median / weighted | +9% / +22% | +15% / +27% |
| Read-only related, tokens | −0% / −3% | +3% / −14% |
| Read-only related, cold stored nothing (empty registry), tokens | −0% / −3% | +4% / −13% |
| Same in dollars (`cost_usd`): warm-related | +8% / +6% | +14% / +7% |
| Dollars: read-only related | −1% / +1% | +3% / −7% |
| Dollars: read-only related, cold stored | +2% / −1% (n=24) | +3% / −13% (n=30) |
| Dollars: warm-related, cold stored nothing | +8% / +5% | +25% / +21% |
| Dollars: cold + one read-only reuse vs no registry (rep 1) | +8% / +8% | +12% / +9% |
| Warm-related runs that wrote (all on misses) | 20/72 | 23/72 (6 via a search and one fetch) |

- **The new cards are hit or miss.** Of the 5 added cards, 2 halved their related question: cachekit 102k → 48k (4 → 2 web calls) and stripe-invoice 58k → 27k (5 → 2). One was flat (embrace), and astro's related question was already cheap (12k) and got dearer (26k, 13k).
- **Most of the aggregate is noise.** Read-only runs on an *empty* registry should match the baseline, but they came out at −13% tokens. That's the noise floor for a token-weighted mean at n≈40 with 200k+ outliers. Medians are flat for both policies.
- **The token metric overstates write cost.** "Total" counts cache reads at full weight. A cold write adds ~40k total tokens but only ~1.7k uncached (+$0.004 median), because it's extra turns over a cached context. In dollars every result here shrinks toward zero: miss-0.5's +22% warm-related is +6%, and read-only −3% is +1%. Earlier LOG entries use the same metric, so their gains and losses are overstated too, in both directions.
- **Warm writes on misses cost more** (+21% vs +5% in dollars) because miss-0.7 lets more of them earn a card. In a shared registry those are first writes, the same as cold runs, and are paid back by later readers. One reuse is the least favourable accounting.
- **Wrong answers are not card-caused.** All 4 pydantic EllipsisType misses are on a question that only the source answers. The r2 cold registry was empty, and miss-0.5 missed it too.

Verdict: miss-0.7 does what it was meant to: more cards, and large savings where the related question was expensive. At 2 reps it can't be told apart from miss-0.5 on totals (net +9% vs +8% in dollars over one reuse). Keep it as a candidate. The bigger finding is the metric: rescore earlier results in dollars before comparing policies further.

## 2026-11-02: every iteration rescored in five measures (`rescore.py`, not an iteration)

Why: miss-0.7 found that total tokens count cache reads at full weight, which makes a write look far dearer than it is billed. Dollars aren't the answer for everyone either. API users pay `cost_usd`, but Pro and Max plans meter usage against 5-hour and weekly caps by a formula that isn't published, so we don't know how they weight cache reads, cache writes and output. `rescore.py` therefore scores each main results folder (narrow-0.1 to miss-0.5) in five measures:
- total tokens
- uncached tokens: total minus cache reads
- dollars
- output tokens
- peak context: the largest single call's input, read from `stream.jsonl`, which is how full the context window gets

It uses `report.py`'s rows, arms and baselines, and its token cuts match `report.py` (lean-0.1 multi-fetch related −27%, read-only −28%). Copied baseline rows are matched to their own iteration's run folder by total. Every row has a peak except narrow-0.1's no-write related runs, whose folders weren't kept. Full tables are in `out_rescore.md`.

Hard set, multi-fetch tasks (9; miss-0.5 has 7, since it reran its own no-write runs), weighted change:

| | Net, tokens | Net, uncached | Net, $ | Net, output | Related, tokens | Related, uncached | Related, $ | Related, peak |
|---|---|---|---|---|---|---|---|---|
| narrow-0.1 | +50% | +15% | +20% | +41% | +47% | +10% | +11% | - |
| map-0.1 | +43% | +11% | +13% | +58% | +6% | −9% | −14% | −20% |
| route-0.1 | +7% | −16% | −16% | +36% | −30% | −31% | −38% | −39% |
| lean-0.1 | −9% | −14% | −19% | +10% | −35% | −27% | −38% | −35% |
| lean-0.2 | +1% | −14% | −15% | +10% | −20% | −24% | −29% | −29% |
| enforced-0.1 | +17% | −6% | −3% | +25% | −13% | −21% | −21% | −19% |
| enforced-0.2 | +4% | −18% | −11% | +10% | −19% | −30% | −28% | −27% |
| miss-0.1 | −18% | −15% | −8% | −9% | −32% | −25% | −23% | −20% |
| miss-0.2 | −15% | −17% | −19% | +6% | −42% | −32% | −43% | −43% |
| miss-0.3 | +9% | −11% | −6% | +13% | −24% | −29% | −31% | −30% |
| miss-0.4 | +2% | −11% | −8% | +13% | −36% | −29% | −35% | −33% |
| miss-0.5 | −4% | −11% | −6% | +1% | −37% | −24% | −26% | −21% |

Net is a write plus one related reuse. coldonly-0.1 matches lean-0.1 in these columns, since they share runs.

- **The real split is whether cache reads count.** Uncached tokens and dollars agree within about 7 points on net for every policy after map-0.1. Total tokens is the odd one out, by up to 23 points. So a plan meter that discounts cache reads should see roughly the dollar result, and one that counts them in full should see the token result.
- **A related reuse is cheaper in every measure.** On multi-fetch tasks, every policy after map-0.1 cuts related questions in tokens, uncached tokens, dollars and peak context, and nearly all cut output too. Peak context falls 19-43%, which matters to plan users apart from caps: a fuller window means earlier compaction.
- **Net over one reuse depends on the measure.** Uncached and dollars: −3% to −19% for every policy after map-0.1. Total tokens: −18% to +17%. Output alone: worse for every policy but miss-0.1 (+1% to +36%), since a write is output.
- **The best policy depends on the measure, within noise.** In dollars, lean-0.1 and miss-0.2 lead (−19%). In uncached tokens, enforced-0.2 and miss-0.2 do (−18%, −17%). In total tokens, miss-0.1 and miss-0.2 do (−18%, −15%). miss-0.5, the policy kept on token results, is never best on net. miss-0.7's empty-registry check put the noise floor for a weighted mean at about ±13% (n≈40), and these are 9 tasks, so none of these leads is established.
- **Cheap pages lose in every measure.** On miss-0.5's easy set (24 one-fetch tasks), net over one reuse is +16% tokens, +20% uncached, +18% dollars and +12% output. A one-fetch run has little cached context, so discounting cache reads makes the write *dearer* in relative terms. miss-0.5's break-even estimate (about 1 multi-fetch lookup in 6, from tokens) needs a larger multi-fetch share under uncached tokens or dollars.
- **Library docs lose in every measure checked.** From miss-0.7's entry, write plus one reuse is +8-9% in dollars as well as worse in tokens. The cards miss, so the metric can't rescue it.

Verdict: no measure flips the overall picture. Breadcrumbs save on a reuse of a multi-fetch hard task in every measure, and lose on cheap pages and library docs in every measure. On net over one reuse, every policy after map-0.1 saves in uncached tokens and dollars, but only some do in total tokens. Whether plan users see that depends on how plans meter cache reads, which isn't published. Report results in all five measures from now on, and state which ones a conclusion holds in.

## Next

- **Check how a plan meters cache reads.** Read `/usage` before and after a batch of runs on the plan, and compare the change with total and uncached tokens. That decides which column applies to plan users.
- **Policy choice, if hard sites matter.** Rerun lean-0.1 and miss-0.5 on the 9 hard multi-fetch tasks, with new no-write runs shared by both, reps 4-6. Score them with `rescore.py`. Do this after the cross-user access-failure counts, since those decide whether hard sites are common enough to matter.
- **Measure demand for access knowledge on hard sites.** Done on this machine (2026-11-02 above): rare and not repeated. Next, send `access_failures.py` to the developer and other users; cross-user repeats of the same failing site are what a shared registry needs.
- **If library docs are revisited**, file cards by library rather than landing page, and write raw-source URL patterns (`raw.githubusercontent.com/<repo>/<tag>/...`) as site records. The oracle caps a route-only breadcrumb at about −12% on this workload.

## 2026-11-02: head-0.1, lookup cost on popular reference pages (`tasks_head.yaml`, `out_head-0.1/`)

Why: in a large shared registry, any popular page is almost surely carded already, so per-person repeats stop mattering. Savings then scale with (share of lookups on popular pages) × (share of those that take several fetches) × (saving per reuse). This measures the second term. `research/scripts/route_reuse.py` and `research/route-reuse-prompt.md` (cross-machine page and domain counts) are written but not sent: with a handful of users over 30 days, little overlap would say almost nothing.

Tasks: 24 canonical reference pages of widely used technologies (Python, Node, MDN, PostgreSQL, Docker, Kubernetes, React, TypeScript, npm, git, GitHub Actions, AWS Lambda, Go, Cargo, Redis, curl, Flask, pytest, Vite, pandas), none used by `tasks.yaml`. Two facts per page, near 30% and 70% of the cleaned page where a crisp fact sat there, otherwise the nearest one; four were swapped because the cleaner drops that part of the page (k8s probe defaults table, npm `name` rules). All 48 verified. Runs: cold-nowrite and cold-nowrite-related under miss-0.7, reps 1-2, 96 runs, 96/96 correct. Cleaned sizes: 14 of 24 pages exceed one 10k-token fetch.

| No registry, 96 runs | Runs | Tokens | Dollars | Median total |
|---|---|---|---|---|
| 1 web call | 49 (51%) | 26% | 23% | 12.1k |
| 2 web calls | 29 (30%) | 25% | 28% | 21.1k |
| 3+ web calls | 18 (19%) | 49% | 48% | 59.5k |

- **Half of popular-page lookups take one fetch,** against 13% on the hard multi-fetch tasks (87% need 2+). Size doesn't decide it: node fs (117k tokens), go net/http (50k), the Dockerfile reference (29k) and GitHub's events page (19k) are one fetch every time, because `section=` hits a heading named after the option.
- **Two-call runs are a missed section guess.** Flask, MDN Set-Cookie and git-rebase all guess a `section=` that isn't a heading, get the outline, then fetch the right section. A card's section map would save the first call, roughly the outline's cost.
- **The cost sits in a few pages.** cargo manifest (5-9 calls), curl man page (4-7), pytest reference (2-7), npm package.json (2-4), k8s probes (1-6) and git-rebase (2-4): 6 of 24 pages, half the tokens. These are the hard-set pattern (option entries that aren't headings, very long pages).
- **Searches are rare** (8 of 96 runs): the question names the docs, and agents go straight to the URL.

Field data on the first term's companion, multi-call share across users: TraceLab (uw-syfi/TraceLab v0.0.2, CC BY 4.0; tool names and result sizes, no URLs) has 5,346 Claude Code web calls from 29 users. Split into lookups with GAP=3, 76% of 964 lookups take 2+ calls (per-user median 70%, range 31-92% for the 18 users with 5+ lookups), and those hold 96% of web-result chars. Web results are 1.3% of all tool-result chars (WebFetch returns a summary, so this understates pulled pages). This machine and the developer's had about 50%.

Outside data on concentration (the first term): none found that ranks pages. Mintlify (Apr 2026, Cloudflare logs, ~790M requests/30 days) puts AI agents at 45% of docs traffic, 96% of it Claude Code and Cursor, with no per-page breakdown. Adyen's docs: 11.6% automated, and four targets (homepage, robots.txt, API explorer, POS release notes) take 54% of AI requests, mostly agents finding their way in. Ahrefs (137k domains, May 2026): 97% of llms.txt files got no requests. Context7 publishes no per-library counts.

Verdict: on popular pages, a breadcrumb can save on about half the lookups, which carry about three quarters of the cost, but only a fifth of lookups are the hard-set kind where savings measured −32% to −44%. Applying the hard-set cuts to 3+ call runs and a guessed −15% to 2-call runs, net of the +7% fixed cost on 1-call runs, gives roughly −20% in tokens across popular pages. That's an estimate; the warm arms below measure it.

### Reuse arms (`python out_head-0.1/drive.py reuse`, `out_head-0.1/report.py`)

cold, then warm-same-nowrite and warm-related-nowrite on the cold registries, reps 1-2: 144 more runs, 240/240 correct, no usage limit. Pages are grouped by their no-registry cost (mean web calls over the four baseline runs). Cells are mean of per-task changes / weighted change.

| | Pages | Cold stored | Write | Same, read-only | Related, read-only | Net over one reuse |
|---|---|---|---|---|---|---|
| All, tokens | 24 | 24/48 | +33% / +26% | −17% / −43% | −8% / −28% | +12% / +0% |
| All, dollars | | | +38% / +8% | −7% / −36% | −9% / −23% | +6% / −7% |
| One call, dollars | 10 | 0/20 | +31% / +31% | −7% / −7% | −8% / −7% | +9% / +9% |
| Two calls, dollars | 10 | 16/20 | +61% / +33% | +9% / −8% | +7% / −3% | +16% / +14% |
| Three+ calls, dollars | 4 | 8/8 | −4% / −19% | −48% / −66% | −49% / −52% | −26% / −34% |
| Three+ calls, tokens | | | +12% / +3% | −66% / −76% | −59% / −63% | −20% / −26% |

- **Where a lookup is expensive, reuse cuts it by more than half** (cargo manifest, curl, pytest reference, npm package.json): related −63% tokens, −52% dollars, larger than the hard set's −32%. The write pays for itself within the first reuse.
- **Two-call pages get cards that don't help.** 16 of 20 cold runs stored one, at +33% dollars, and reuse saves 3-8%. The missed-section-guess call a card would save is cheap next to the run's fixed cost. These cards are the policy's main loss on this set.
- **One-call pages store nothing** (0/20) and reuse is flat in tokens, so the fixed cost is the +8-9% net from the write-side runs.
- **Weighted, savings come from the few expensive pages.** All 24: related −28% tokens / −23% dollars weighted, but −8% / −9% as a per-page mean. In a shared registry with many reuses per card, the write amortizes away and the related column is the long-run figure.

Verdict: on popular pages breadcrumbs pay where the lookup is expensive, and that's where the cost is. Across the 24, a read-only related reuse is −23% in dollars (weighted), close to the hard set's result, at 2 reps, with 4 pages driving it. The policy wastes its writes on two-call pages: a bar of 3+ web calls, or a higher pull, would drop them.

## Next

- **Raise the card bar to drop two-call cards.** Score miss-0.7 with a 3-call bar on this set: rerun cold under it, or count which stored cards the bar would have refused. Two-call pages would move from +14% net to about the one-call +9%.
- **Concentration.** Ask a docs host (Mintlify, Read the Docs) or Context7 for the share of agent requests that land on their top 1%/10% of pages, or on pages requested by 2+ distinct clients a month. No public source has it.

## 2026-11-03: a 3-call card bar on head-0.1, replayed offline (`out_head-0.1/bar3.py`, not an iteration)

Why: two-call pages get cards that cost more to write than reuse saves (head-0.1 above). This asks what a bar of 3 web calls (searches counting, as in miss-0.7) would have done, using the 240 existing runs and no new ones.

Method: a cold run that stored a card with fewer than 3 web calls is treated as refused. Its reuse runs then start from an empty registry, which is exactly cold-nowrite / cold-nowrite-related on the same task and rep, so those runs stand in. The refused cold run's own cost is cold-nowrite plus the write prompt's fixed cost, measured on the one-call pages, where no cold run stored anything. That fixed cost is taken two ways: as a percentage (+17% tokens, +31% dollars) or as a flat amount per run (2.1k tokens, $0.0039).

The bar refuses 17 of 24 stored cold runs: 14 of 16 on two-call pages, and 3 of 8 on three+ pages (npm package.json r1-r2 and pytest reference r2, which happened to find the answer in 2 calls).

| Net, write + one related reuse, weighted | Actual | Bar 3, % fixed cost | Bar 3, flat fixed cost |
|---|---|---|---|
| Two-call pages, tokens | +28% | +16% | +13% |
| Two-call pages, dollars | +14% | +21% | +13% |
| All 24, tokens | +0% | −5% | −6% |
| All 24, dollars | −7% | −4% | −8% |

- **In tokens the bar helps:** two-call pages go from +28% to about +15%, and all 24 from break-even to about −5%.
- **In dollars it's a wash.** A refused two-call run's write costs $0.0085 over cold-nowrite, and $0.0039 of that is the fixed prompt cost the run pays anyway. The remaining ~$0.0046 is about what reuse of those cards saved. Which way the result tips depends on how the fixed cost scales, and the two models give opposite signs.
- **Three+ pages barely notice.** Losing 3 of 8 cards moves related reuse from −52% to −52% in dollars, and from −63% to −62% in tokens: the other rep's card, or the page's other question, still carries the saving.

Verdict: the head-0.1 prediction (two-call pages from +14% to about +9% in dollars) doesn't hold. The write call is a small part of the two-call loss in dollars. Most of it is the fixed cost of the write-side prompt, which a card bar doesn't remove. A 3-call bar is worth having for tokens and costs nothing elsewhere, but the larger dollar lever is that fixed cost. (Corrected below: measured on the expensive pages, the bar costs more than it saves in dollars.)

## Next

- **Measure the fixed cost directly.** Run cold under a bar of 3 on the two-call pages (20 runs) to replace the modelled refused-run cost with a measured one. That settles the dollar column.
- **Shrink the write-side prompt.** +31% in dollars on one-call pages is pure overhead. Try a shorter miss note, or one that appears only once the bar is passed.

## 2026-11-03: miss-0.8, a 3-call card bar (`--iteration miss-0.8`, `out_miss-0.8/`)

Why: the replay above couldn't settle the dollar column, because it had to model what a refused cold run costs. This measures it.

What changed from miss-0.7: `BC_MIN_CALLS=3`. write refuses page cards from runs with fewer than 3 web calls (fetches, renders and searches together), and the note says so: "whenever getting it took 3 or more web calls (fetches, renders and searches together). write refuses page cards from runs with fewer". The fetch-result nudge and Stop hook use the same bar.

Runs: cold on head-0.1's 10 two-call pages, reps 1-2, 20 runs, 20/20 correct. Only k8s probes (6-7 web calls) stored cards, so it alone got warm-same-nowrite and warm-related-nowrite (4 runs, 4/4 correct). Every other cold run stored nothing, and its reuse is the no-registry run, as in the replay. Agents made no refused write attempts. Baselines are head-0.1's cold-nowrite runs from the night before (`out_miss-0.8/report.py`).

| Two-call pages, weighted | Write | Related | Net, write + one related reuse |
|---|---|---|---|
| Tokens, miss-0.7 | +62% | −7% | +28% |
| Tokens, miss-0.8 | +21% | +0% | **+11%** |
| Dollars, miss-0.7 | +33% | −3% | +14% |
| Dollars, miss-0.8 | +24% | +0% | **+11%** |
| Output, miss-0.7 | +61% | −13% | +28% |
| Output, miss-0.8 | +11% | +0% | +6% |

- **The bar helps in every measure,** and more in dollars than either replay model gave (+21% and +13%). Tokens and output fall the most: the 14 cards the bar now refuses were what made the write runs long.
- **What's left is the fixed cost.** 18 of 20 runs stored nothing and still cost +24% in dollars over no-registry runs. That's the write-side prompt plus the lookup, the same cost seen on one-call pages (+31%).
- **Across all 24 pages,** swapping these runs in for the two-call pages moves the net from +0% to −6% in tokens and from −7% to −8% in dollars. That leaves the three+ pages at miss-0.7, which the replay says loses almost nothing under the bar. Measured under the bar too (next entry), all 24 are −3% tokens and −4% dollars, worse in dollars than miss-0.7's −7%.

Verdict (corrected in the next entry): on two-call pages the bar drops the cards that don't pay, and helps in every measure. The remaining loss there is the fixed cost of the write-side prompt. Whether to keep the bar depends on the expensive pages, which this entry didn't measure.

## Next

- **Shrink the write-side prompt.** +24-31% in dollars on runs that store nothing is now the policy's main cost on popular pages. Try a shorter miss note, or one that's sent only once a run passes the bar.
- **Check miss-0.8 on the three+ pages and the hard set** with a few cold runs, to confirm the bar doesn't cost cards there.

## 2026-11-03: miss-0.8 on expensive pages (`python out_miss-0.8/drive.py expensive`, `out_miss-0.8/report.py`)

Why: confirm the 3-call bar doesn't cost cards where they pay: head-0.1's four three+ pages (against its miss-0.7 runs) and the 9 hard multi-fetch tasks (against miss-0.5's reps 1-2, the last iteration run on them; miss-0.7 differs from it only in counting searches). Cold, reps 1-2, then read-only reuse wherever a cold run stored a card: 26 cold and 34 reuse runs.

Correctness: 58/60. The two misses are sonatype-guava, where both cold runs answered 33.8.0-jre from Maven's own `maven-metadata.xml`. Guava has released since the task was written (expect is 33.7.2), so the answer key is stale and the agents were right. The expected answer is left as is, so earlier runs still score the same.

| Weighted, dollars | Cards stored | Write | Same, read-only | Related, read-only | Net |
|---|---|---|---|---|---|
| Three+ head pages, miss-0.7 | 8/8 | −19% | −66% | −52% | −34% |
| Three+ head pages, miss-0.8 | 6/8 | −2% | −61% | −51% | −23% |
| Hard multi-fetch, miss-0.5 | 16/18 | +30% | −29% | −20% | +0% |
| Hard multi-fetch, miss-0.8 | 11/18 | +46% | −19% | −16% | +9% |

- **Three+ head pages keep their saving.** Related reuse is −51% against −52%. The only cards lost are npm package.json's, whose cold runs took 2 calls both times. The write column moved from −19% to −2% with no change in what was stored: 2 reps of cold runs that vary from 2 to 10 calls (pytest went 7/2 → 5/5, cargo 6/10 → 6/6).
- **The hard set loses one site that matters: sonatype-guava.** Both cold runs took 2 fetches (the JavaScript page, then `maven-metadata.xml`), so the bar refused both cards, and related reuse went from −67% to 0%. That is most of the related column's change (−20% → −16%). Cards also went missing for bash-histsize r2, gha-matrix-max-jobs r2 and nginx-keepalive-requests r2, but each task's other rep's card wasn't affected and their related savings held (−21%, +20% and −16%, against −24%, +91% and −17%).
- **The hard-set write column has one outlier.** git-gc-auto went +33% → +268% on a cheap baseline ($0.027) when one cold run took 6 calls, but the write cost is higher on 7 of the 9 hard tasks, not just that one. The hard set's baselines are also a week older than these runs.

Across the sets, write plus one related reuse, weighted, miss-0.7/0.5 → miss-0.8:

| | Tokens | Dollars |
|---|---|---|
| All 24 head pages | +0% → −3% | −7% → −4% |
| Hard multi-fetch, 9 tasks | +12% → +20% | +0% → +9% |
| Hard multi-fetch without sonatype, 8 tasks | +13% → +22% | +4% → +11% |

- **Sonatype isn't the main loss.** Without it the hard set is still 7 points worse in dollars, and related reuse barely moves (−17% → −16%). The loss is in the write runs: hard-set cold runs averaged 3.6 web calls under miss-0.8, against 3.2 under miss-0.5.
- **The cause isn't settled.** The note's new wording ("3 or more web calls") may lead agents to make an extra call to clear the bar. Or it's drift: the miss-0.5 runs and their baselines are 3-8 days older, and sites change (guava did). A same-day miss-0.7 cold control on the hard set would tell them apart. It was skipped for now.

Verdict: in dollars the 3-call bar is worse overall. It helps only on two-call pages (+14% → +11%), and loses more on the expensive pages and the hard set, where the money is. miss-0.7 stays the default. The bar's measured gain is too small to be worth a second try unless the control shows the hard-set loss is drift.

## Next

- **Same-day control, if the bar is revisited:** the 9 hard tasks cold under miss-0.7, reps 1-2 (18 runs). If those also cost about +46% in dollars, the miss-0.8 loss is drift. If they stay near +30%, the bar's wording costs money.
- **Shrink the write-side prompt** (from the miss-0.8 entry). +24-31% in dollars on runs that store nothing is still the policy's main cost on cheap pages, and doesn't depend on the bar.
- **Fix sonatype-guava's expected answer** (33.7.2 → 33.8.0), with a note that runs before 2026-11-03 are scored against the old one.

## 2026-11-03: concentration, an ask for docs hosts and a Wikimedia stand-in (not an iteration)

Why: savings in a shared registry scale with how much of agent demand lands on pages someone else already looked up. No public source ranks agent requests by page (head-0.1 above), so this gets the records from people who have the logs.

- **`research/scripts/agent_concentration.py`**, for a site owner to run on 30 days of access logs (nginx/Apache, Cloudflare Logpush JSON, CloudFront/W3C; gzip ok; Python 3.10+, standard library only). For agent traffic (Claude-User, ChatGPT-User, Perplexity-User and other named assistants), generic HTTP clients and human traffic, it prints only aggregates: the share of requests on the top 1%, 10% and 25% of pages, pages fetched by 2+ and 5+ clients, and the share of requests for a page another client of the same kind fetched earlier. That last figure is the share a registry could serve from someone else's breadcrumb. Crawlers, assets, robots.txt, non-GET and 4xx/5xx requests are left out, and `/x`, `/x/`, `/x.md` and `/x/index.html` count as one page. Checked against a hand-worked synthetic log in all three formats.
- **`research/concentration-ask.md`**: the message, recipients (Mintlify, Read the Docs, GitBook, Context7, self-hosted open-source docs) and what to do before sending. Not sent.
- **`research/scripts/wikimedia_concentration.py`**: the stand-in. Wikimedia's pageview_complete dumps give every article's daily views, split into user and automated traffic (bots that don't identify themselves). That's reference lookups, not docs and not AI agents, so it shows how long the tail is, not the registry's number.

English Wikipedia, 2026-10-01 (one day; dumps in the session scratchpad, not kept):

| | Views | Pages | Top 1% of pages | Top 10% | Top 100 pages | Views on pages viewed 2+ times |
|---|---|---|---|---|---|---|
| User | 206M | 9.8M | 56% | 85% | 10% | 98% |
| Automated | 61M | 12.4M | 49% | 70% | 27% | 88% |

- **Reference lookups are concentrated.** A tenth of the pages take 85% of human views in a day, and 98% of views land on a page that got at least one other view that day.
- **Automated traffic has a longer tail and a heavier head.** 12% of its views are a page's only view that day, against 2% for users. A hundred pages take 27% of it, likely a few bots hammering the same pages. 43% of automated views are on the users' top 1% of pages.
- **This is an upper bound for a registry.** Wikimedia counts views, not distinct clients, so a client fetching a page twice counts as a repeat. The docs-host script counts distinct clients for that reason.

## Next

- **Send the ask** (`research/concentration-ask.md`) once it has a sample output from a real log.
- **If no host answers,** repeat the Wikimedia count over 30 days rather than one, and for a technical wiki subset, to see how the repeat share grows with the window.

## 2026-11-03: how a Pro plan meters cache reads (`out_meter-0.1/`, not an iteration)

Why: the rescore entry found that results split on whether cache reads count. API users pay dollars, which discount cache reads to a twentieth of input, but plan users are metered against 5-hour and weekly caps by an unpublished formula. This measures it.

Method (`out_meter-0.1/drive.py`): three synthetic batches on sonnet, each mostly one token type. **out**: 3,000-word stories, no tools (95% of dollars are output). **write**: "reply OK" under a unique ~53k-token system prompt, so the whole prompt is a cache write (100%). **read**: 25 `echo` calls under one fixed ~53k prompt, so every turn re-reads it (87% cache reads). The plan meter is the endpoint behind `/usage` (`api.anthropic.com/api/oauth/usage`), in whole percent. It lags spend by a minute or more and returns 429 if polled often, so each batch reads it once at the start and once settled at the end (two readings 90 s apart that agree). Nothing else used the account during a batch. Prices fitted from the runs' own `cost_usd` match exactly: input $2/M, cache write $4/M, cache read $0.10/M, output $10/M.

| Batch (`report.py`) | Runs | Dollars | Cache write | Cache read | Output | 5-hour meter | Points per $ |
|---|---|---|---|---|---|---|---|
| out | 18 | $1.11 | $0.06 | $0.00 | $1.05 | +12 | 10.8 |
| write | 6 | $1.28 | $1.28 | $0.00 | $0.00 | +9 | 7.0 |
| read | 9 | $1.51 | $0.07 | $1.32 | $0.13 | +11 | 7.3 |

Solved per token type: cache writes 7.0 points per dollar, cache reads 6.9, output 11.0.

- **Cache reads are metered at their dollar price.** The read batch did 13.1M cache-read tokens. Counted like input, that's $26 and about 180 points, against the 11 seen. Per dollar, reads and writes are within a point.
- **Output costs about 1.6× its dollar price** on the meter, relative to cache writes. In tokens: an output token meters like 3.9 cache-write tokens, and a cache read like 0.025.
- **So for plan users the dollar column applies, with output weighted ×1.6.** Total tokens, which count cache reads in full, is the wrong measure for both plans and the API. Writes hurt a bit more on a plan than in dollars, since a write is output.
- **Scale:** at about 7 points per dollar, a 5-hour window holds about $14 of sonnet cache traffic at API prices, or about $9 of output. The weekly meter rose 73% → 82% over about 70 five-hour points, so a week is roughly 8 windows. Both figures are coarse, given the 1-point resolution.

Limits: one sample per batch, so the 1-point resolution is ±8-11% on each. The out batch's start reading (7%) came 60 s after the probe, before the settle wait was added, so it could be a point low, which would make output ×1.45. The read batch spanned the 02:00 reset because the machine slept. Six runs died in sleep (negative timeouts), and the nine that finished all fell in the new window, which opened when the machine woke, so it's read from 0%. The earlier write batch and the first read batch crashed on 429s and are kept in `meter.jsonl` but not scored. They agree with the table within a couple of points. Sonnet only, and the formula could differ for Opus or change at any time.

Verdict: a Pro plan meters roughly in dollars, with output counting more. The rescore's dollar results hold for plan users, a little worse wherever a policy adds output.

## Next

- **Add a plan measure to `rescore.py`:** dollars with output ×1.6. Check whether any verdict that held in dollars flips. Most likely to flip are the write-side nets, since output was already the one measure where writes lost.
- **Keep the machine awake for long batches** (`powercfg /change standby-timeout-ac 0`, or run under a keep-awake). Sleep cost two batches here.

## 2026-11-03: miss-0.9 and miss-0.10, page-card instructions deferred (`out_miss-0.9/`, `out_miss-0.10/`)

Why: dollars are the measure (meter-0.1 above), and the policy's main loss on popular pages is a fixed cost on runs that store nothing: +31% on one-call pages and +24% on two-call pages under the 3-call bar. Every run that misses gets the ~320-token note, whether or not it ever passes the bar.

What changed (`BC_DEFER=1`): a lookup that misses now sends only a short site-record note (97 tokens): "If you learn how to get content from any page on the site (an API or raw-source URL pattern with {name} in it, Markdown versions, JavaScript needed), write a site record before answering. A fetch result will say if a page card is wanted too." The fetch that passes the bar carries the page-card instructions (203 tokens) in place of the old one-line nudge. A run that is already past the bar when it looks up gets the full note, as before. Site records stay open to every run, because one-fetch site records can pay on other pages of the site (miss-0.6: jetbrains −92%), while page cards from one-call pages don't. On head-0.1, the related question on a one-call page averaged 1.1 web calls (1.15 on miss-0.5's easy set, 1.13 on route-0.1's), and none of the 51 such pages took 3+. The Stop hook now points to "the fetch result's note". miss-0.9 has miss-0.7's bar, and miss-0.10 has miss-0.8's bar of 3 web calls.

Runs: cold on head-0.1's 10 one-call and 10 two-call pages, reps 1-2, for each iteration: 80 runs, $2.34, 80/80 correct, 5-hour meter 27% → 44%, weekly 83% → 85%. Baselines are head-0.1's cold-nowrite runs from 2026-11-02, as in miss-0.8 (`out_miss-0.9/report.py`).

| Cold vs no-write, weighted | One call: $ | Tokens | Output | Sites stored | Two calls: $ | Tokens | Output | Cards stored |
|---|---|---|---|---|---|---|---|---|
| miss-0.7 | +31% | +17% | +15% | 0 | +33% | +62% | +61% | 16/20 |
| miss-0.9 | +24% | +15% | +17% | 4 | +24% | +51% | +61% | 16/20 |
| miss-0.8 | | | | | +24% | +21% | +11% | 2/20 |
| miss-0.10 | +17% | +13% | +20% | 5 | +12% | +23% | +20% | 3/20 |

- **Deferring cuts about 9-12 points in dollars at either bar.** Two-call pages go from +33% to +24% (bar 2) and from +24% to +12% (bar 3), with the same cards stored. On one-call pages, runs that store nothing went from +31% to +19% and +12%. Their extra cache writes fell from 850 tokens to 650 and 420.
- **The one-call difference between miss-0.9 and miss-0.10 is noise.** At one web call the bar never comes into play, so those runs were identical, yet they differ by 7 points (+24% vs +17%). That's the noise floor at 20 runs a cell. A fixed cost of about +12-19% remains. Only ~100 tokens of it is the new note. The rest may be drift against day-old baselines, or the write tool and miss prompt. A same-day no-write control would tell.
- **The short note brings in junk site records.** 9 of 40 one-call runs (react-useeffect, tsconfig, vite-server) wrote site records saying "plain fetch works; the section parameter returns just that section". That describes our fetch tool, not the site, and no later agent saves anything from it. Those runs cost +43-60%, so the 9 junk writes are most of what's left on one-call pages. Under the old note, these pages stored no site records at all.
- **Writes still slip through under the bar** (1 refused per iteration), as before.

Verdict: deferring works, with 9-12 points saved in dollars on cheap pages at either bar and the same cards stored. It's a net gain once the site note stops inviting records with no pattern in them. miss-0.10 is the cheapest yet on cheap pages (+17% / +12%), but bar 3 cost cards on the hard set under miss-0.8 (sonatype-guava), so the bar still has to be decided on the expensive pages.

## Next

- **Tighten the site note (miss-0.11):** ask only for an API or raw-source URL pattern, Markdown versions or a JavaScript requirement, and say "not that a plain fetch works". Or have the registry refuse site records from under-bar runs that carry none of those, so the agent learns it at write time. Rerun the one-call pages (20 runs) to check that the junk records go away.
- **Then step 2:** miss-0.9 or miss-0.10 (with the tightened note) on head-0.1's three+ pages and the 9 hard multi-fetch tasks, cold plus read-only reuse, against miss-0.7 and miss-0.8. That decides the bar. Weekly usage is at 85% and resets 2026-11-07, so step 2 waits for the reset.
- **Same-day no-write control** on the one-call pages (20 runs), to tell drift from the fixed cost that remains.

## 2026-11-04: miss-0.11, a tighter site-record note (`out_miss-0.11/`)

Why: miss-0.9's short note drew site records on 9 of 40 one-call runs that only said "plain fetch works; the section parameter returns just that section", at +43-60% a run.

What changed from miss-0.10 (`BC_SITE_STRICT=1`): the note now reads "Write a site record before answering only if you found something a later agent would not get from a plain fetch of the page: an API or raw-source URL pattern with {name} in it, Markdown versions of pages, or that pages need JavaScript. Not that a plain fetch or the section parameter works: that is true of most sites." It's ~150 tokens, against 97.

Runs: cold on head-0.1's 10 one-call pages and the hard set's 5 one-fetch API tasks (terraform, galaxy, artifacthub, puppet, jetbrains), reps 1-2, plus same-day cold-nowrite runs on the one-call pages. 50 runs, $0.85, 50/50 correct after regrading. Both galaxy runs answered 14.0.0, which is right: the key said 13.5.0 and now accepts 13.5.0 or any later version, as guava's does. Weekly usage went from 86% to 87% (`out_miss-0.9/report.py`).

| Cold vs no-write, one-call pages, weighted | Dollars | Tokens | Output | Junk site records |
|---|---|---|---|---|
| miss-0.7, vs 11-02 no-write | +31% | +17% | +15% | 0 |
| miss-0.9, vs 11-02 | +24% | +15% | +17% | 4 |
| miss-0.10, vs 11-02 | +17% | +13% | +20% | 5 |
| miss-0.11, vs 11-02 | +26% | +8% | +4% | 0 |
| **miss-0.11, vs same-day no-write** | **+11%** | **+3%** | **+1%** | 0 |

- **The junk records are gone,** and with them the extra output and turns: miss-0.11 one-call runs take the same turns, output and cache reads as no-write runs.
- **The old baselines had drifted.** Same-day no-write runs on these pages cost 13% more than head-0.1's from 2026-11-02, mostly cache writes (+400 tokens a run) at the same turns. Claude Code was 2.1.314 both days, so it's likely the pages. Every miss-0.8 to miss-0.10 figure above is against the 11-02 runs, so their one-call and two-call costs are overstated by an unknown amount, up to ~13 points.
- **What's left on one-call pages is about +11% in dollars and +3% in tokens.** That's cache writes: ~390 tokens a run, of which the note is ~150. Down from +31% under miss-0.7, but drift accounts for some of that drop.
- **API site records hold.** 8 of 10 cold runs stored one, every one with a `{placeholder}` URL pattern (terraform, galaxy, artifacthub, puppet 2/2 each). miss-0.5 got 7 of 10 on the same reps. jetbrains still gets none (0/2, as under miss-0.5), so miss-0.6's finding stands: opaque-ID patterns like `{pluginId}` aren't written. Cost matches miss-0.5 (+31% vs +31% in dollars, on miss-0.5's October baselines).

Verdict: miss-0.11 is the write side to keep for cheap pages. It defers the page-card instructions, asks only for site records that carry something a fetch doesn't, and costs about +11% in dollars and +3% in tokens on one-call pages against a same-day baseline, with API site records intact. The bar (2 or 3 calls) is still open.

## Next

- **Step 2, after the weekly reset (2026-11-07):** miss-0.11 and a bar-2 version of it on head-0.1's three+ pages and the 9 hard multi-fetch tasks, cold plus read-only reuse, with same-day cold-nowrite runs. That decides the bar. Rerun the two-call pages under the same day's baseline too.
- **Stale answer keys:** `run.py verify` fails on openvsx-rust-analyzer, amo-ublock-version, flathub-gimp-release and terraform-aws-provider's related question. Give them the same at-or-above patterns before any easy-set run.
- **Always run a same-day no-write control.** Day-old baselines drifted 13% on cheap pages, which is as large as most effects being measured.

## 2026-11-04: a plan measure, fixed answer keys and step 2's driver (not an iteration)

**Plan measure.** `rescore.py` has a sixth measure, `plan`: dollars with sonnet's output weighted 1.6×, as meter-0.1 found a Pro plan counts it. Sonnet's output is read from each run's `stream.jsonl`, because runs that search also bill Haiku (WebSearch), up to ~900 output tokens a run, and the meter was only measured on sonnet. Haiku's output stays at its dollar price. `out_head-0.1`, `out_miss-0.8` and `out_miss-0.9`'s reports print it too.

- **No verdict flips.** Across every iteration and group in `out_rescore.md`, plan is within 6 points of dollars (route-0.1's write, +26% → +32%), and within 4 everywhere else. The only sign change is route-0.1's read-only net, −1% → +1%. In the later reports it's within 3 points (miss-0.8 two-call write +24% → +23%, hard write +46% → +47%; miss-0.11 one-call +11% → +10% against same-day no-write). Weighting output barely moves relative changes, since the baselines' output is weighted too.
- So dollars stays the measure to quote, with plan beside it as a check.

**Answer keys.** openvsx-rust-analyzer (0.4.3103, now 0.4.3107), amo-ublock-version (1.75.0, now 1.75.4), flathub-gimp-release (3.2.6, now 3.2.8) and terraform-aws-provider's related question (8.9.0, now 8.10.0) accept their old version or any later one, as guava and galaxy do. Earlier rows keep their grade. `run.py verify` passes on both task files (gnu.org timed out once, then passed).

**Step 2's driver** (`out_miss-0.12/drive.py`, `report.py`). miss-0.12 is miss-0.11 with miss-0.9's bar (no call minimum), so the two differ only in the bar. On head-0.1's two-call and three+ pages and the 9 hard multi-fetch tasks, reps 1-2, phase 1 runs same-day cold-nowrite and cold-nowrite-related (into `out_miss-0.12`) task by task beside cold under both iterations. Phase 2 runs read-only reuse on each cold run that stored a record. The driver runs `verify` on the 23 tasks first and stops if a key fails. `--dry` estimates ~300 runs and ~$17 from earlier runs at the same bar: about 117 five-hour points (a bit over one window, which the driver waits out) and ~15 weekly points. The report was checked on a stand-in layout (miss-0.8's runs as miss-0.11, head-0.1's and miss-0.5's as miss-0.12, with their old baselines) and reproduces `out_miss-0.8/report.py`'s miss-0.8 lines exactly. Its miss-0.12 reuse arms differ where a cold run stored nothing, since those count as the baseline, as miss-0.8's did.

## Next

- **Run step 2 after the weekly reset (2026-11-07):** `../.venv/Scripts/python out_miss-0.12/drive.py`, then `../.venv/Scripts/python out_miss-0.12/report.py` (the system Python lacks httpx; every verify fails under it). Keep the machine awake.

## 2026-11-04: a month of Wikimedia pageviews (`research/scripts/wikimedia_month.py`, not an iteration)

Why: the one-day Wikimedia count (2026-11-03 above) left open how repeat demand grows when a breadcrumb outlives the day it was written. This reads October 2026's monthly pageview_complete file, whose rows carry each title's views per day, and asks: of a day's views, how many land on a page that was also viewed on an earlier day (the day before, the 7 days before, or any earlier day)? Counting by day keeps one client's burst of reloads from counting as a repeat, though a client that comes back daily still does. A second set of figures covers the 56,576 titles tagged by the Computing, Software, Computer science, Linux and Computer security WikiProjects (fetched from the PageAssessments API). The script was checked against a hand-worked synthetic dump. Dumps (15 GB) are in the session scratchpad and not kept.

English Wikipedia, user (human) views, October 2026. The automated file wasn't counted: the run was stopped for low memory and is set aside for now.

| | Views | Pages | Top 1% / 10% of pages | Top 1,000 pages | Viewed once in the month | Viewed the day before | In the 7 days before | Any earlier day |
|---|---|---|---|---|---|---|---|---|
| All | 6.1B | 49.1M | 79% / 97% | 12% | 48% of pages, 0.4% of views | 97.6% | 99.1% | 99.4% |
| Computing WikiProjects | 89M | 56k | 45% / 80% | 53% | 0.9% of pages, 0.0% of views | 99.4% | 99.6% | 99.6% |

The last three columns cover days 8-31, so the 7-day lookback is complete.

- **Human reference lookups repeat almost completely over a month.** 97.6% of a day's views land on a page someone viewed the day before. The one-day figure (98% on pages viewed 2+ times that day) barely moves with a longer window, because it was already near the ceiling.
- **Computing articles repeat even more, with a wide head:** 1,000 pages take half the views, and under 1% of tagged pages get only one view in the month. The list is of established, tagged articles, which biases it toward popular pages.
- **This is as far as Wikimedia goes.** At ~99% the upper bound rules nothing out. What decides a registry's savings is how much of a page's demand comes from clients other than the first, and views can't separate many agents needing a page from a few clients returning to it. Only distinct-client logs answer that, so the docs-host ask (`research/concentration-ask.md`) is the remaining route.

## Next

- **Concentration is set aside (decided 2026-11-04):** demand is assumed concentrated enough for a shared registry to pay, and the ask is not sent. The script and the ask stay in `research/` if it's revisited.

## 2026-11-04: more expensive pages for step 2 (`tasks_head.yaml`, screen in `out_head-0.2/`, not an iteration)

Why: head-0.1's three+ group is 4 pages, and two of them carry its −52% (curl −88% / −91%, cargo −41% / −61%; without curl the other three are −37%). Step 2 would add reps on the same 4 pages, not more pages.

Candidates were long single-page references, checked first with the harness's own fetch for size and headings. 11 pages went into `tasks_head.yaml`, two facts each near 30% and 70% of the page, with `verify` passing on all of them. Each was screened with cold-nowrite and cold-nowrite-related, rep 1 only: 22 runs, $2.25, 22/22 correct. One ffmpeg answer was regraded: the expect pattern was wrong, not the answer.

| Mean web calls, rep 1 | Pages (calls on question / related) |
|---|---|
| 3+, added to step 2 | apache-core (6 / 6), vim-options (7 / 4), haproxy-config (2 / 7), rsync-manpage (5 / 4), systemd-exec (3 / 3), sqlite-pragma (3 / 3), linux-tcp7 (3 / 3) |
| 2 | tmux-manpage, kubelet-flags, ffmpeg-options |
| 1 | gnu-make (a heading names the answer's option) |

- **What predicts a 3+ page is no headings at the option level,** not size. vim options (116k tokens), rsync (61k), systemd.exec (59k) and SQLite PRAGMA (23k) have none in the cleaned page. GNU make (127k) has 85 and took one fetch.
- **Three pages sit at exactly 3** (systemd-exec, sqlite-pragma, linux-tcp7) and may fall into the two-call group at rep 2. Step 2's same-day baselines regroup them.
- `out_miss-0.12/drive.py` now has 11 three+ pages. `--dry` puts step 2 at 414 runs, ~$31 and ~27 weekly points. That's an overestimate: a new page's reuse runs are costed at its baseline, since none has cold runs yet.

## 2026-11-04: miss-0.13, the site-record note waits for a sign of an access route; a no-registry arm (`out_miss-0.13/`)

Why: on pages where breadcrumbs can't save anything, every lookup that misses still sends the site-record note (~150 tokens), and that is miss-0.11's whole +11% on one-call pages. The registry can't tell a cheap page from an API site before anything is fetched, but the web server sees each result, so the note can wait until a result shows something worth recording.

What changed from miss-0.11 (`BC_SITE_SIGNAL=1`):
- **A lookup that misses sends nothing.** It logs the site it looked up.
- **The note comes with a result instead.** It goes once, with the first fetch or render that shows an access route (`bc.common.access_signal`): a render, a JSON or XML response, a host other than the one looked up, or a `.md`/`.txt`/`.json`/`.xml` path. A smoke run showed `/api/` paths can't count, because docs live there too (nodejs.org/api/fs.html).
- **The card side is unchanged:** bar of 3 web calls, deferred card note.
- **Rule 3 names fetch results too:** "Call write only if a lookup or fetch result asks for breadcrumbs". The first batch kept miss-0.11's "a lookup result", and agents refused the note: 10 of 10 API runs got it and none wrote. One said it "came from the fetch", not a lookup. Those 30 cold runs are in `out_miss-0.13/cold_lookup-rule/`, and the cold runs were redone with the new rule.

New arms `noregistry` and `noregistry-related` (`run.py`): web tools only, with no registry and no lookup step in the prompt. Every earlier baseline (cold-nowrite) already makes a lookup call and carries the registry tools, so the LOG's write-side costs never included the lookup itself. Against cold-nowrite, noregistry measures it.

Runs: head-0.1's 10 one-call pages and the 5 one-fetch API tasks, reps 1-2. Cold under miss-0.13, cold-nowrite and noregistry ran side by side (`out_miss-0.13/drive.py`), with the cold runs redone an hour later. 120 runs plus 3 smoke runs, $1.96, all correct after one regrade: terraform-aws-provider's key now accepts 6.71.0 or later, since 6.72.0 is out. `out_miss-0.9/report.py` prints both tables.

| Dollars, mean / weighted | One-call pages | One-fetch API |
|---|---|---|
| miss-0.11 cold vs its same-day no-write | +15% / +11% | – |
| **miss-0.13 cold vs same-day no-write** | **−1% / −1%** | +66% / +40% |
| Lookup only: cold-nowrite vs noregistry | +16% / +4% | +23% / −2% |
| Site records stored | 0 / 20 (no note sent) | **10 / 10**, all with a `{placeholder}` pattern |

- **On cheap pages the write side now costs nothing.** No one-call run got a note, and cold matches no-write in every measure (tokens −3%, output −3%, plan −1%). The fixed cost that miss-0.7 to miss-0.11 cut from +31% to +11% is gone.
- **API site records come back complete.** 10 of 10, against 8 of 10 under miss-0.11 and 7 of 10 under miss-0.5. jetbrains stored one for the first time under any miss iteration (2 of 2, `{pluginId}`), and every record names the `select` that keeps the response small, the detail miss-0.6 found missing. The note arrives with the JSON in context, which may be why. The API cold runs cost +40% in dollars because they write: that's the first-write cost, paid back by reuse, which this batch didn't run.
- **The lookup itself costs +4% to +16% in dollars on a one-call page** compared with no registry, and about nothing on API pages. In tokens it's +68%, nearly all cache reads from the extra turn. It's now the whole floor on cheap pages, and the only way below it is folding the lookup into fetch.

Verdict: miss-0.13 is the write side to keep. It costs nothing where breadcrumbs can't help, and it writes better site records where they can. Step 2 now runs it against **miss-0.14** (miss-0.13 with miss-0.12's bar, no call minimum), so the bar is decided on this write side (`out_miss-0.12/drive.py` and `report.py`; same tasks, baselines and estimate).

## Next

- **Run step 2 after the weekly reset (2026-11-07):** `../.venv/Scripts/python out_miss-0.12/drive.py`, then `../.venv/Scripts/python out_miss-0.12/report.py` (the system Python lacks httpx; every verify fails under it), with 11 three+ pages, comparing miss-0.13 and miss-0.14. Keep the machine awake.
- **Reuse of the new API site records** (warm-related-nowrite on miss-0.13's 10 API registries, 10 runs) shows whether the `select` hints pay. It's cheap, so add it to step 2 or run it before.
- **Folding lookup into fetch** is the only remaining lever on cheap pages, and it's worth at most the +4% to +16% measured above.
- **Concentration is set aside** (decided 2026-11-04, above).

## 2026-11-08: step 2, paired: the card bar and trace-built cards (`out_miss-0.12/drive.py`, `report.py`, `report.md`)

Why: the planned step 2 ran miss-0.13 (bar 3) and miss-0.14 (bar 2) as two cold arms, 414 runs, scored as write plus one reuse. Two problems. Under miss-0.13 and miss-0.14 nothing mentions the bar until a fetch passes it, so both run alike up to the second web call, and two separate cold arms mostly measure rep noise. And in a shared registry a write is paid once and read many times, so the question is how many reuses pay a write back, not one. The rewrite runs cold under miss-0.14 only and reads bar 3 off each run's call log (`bar3.py`: a page card stored within 2 web calls is refused; its cold cost becomes the same-day cold-nowrite run, its reuse the no-registry run). It adds a trace arm: `out_trace-0.1/build.py` builds a route card from each cold-nowrite run's trace with no agent writing. The card holds the call that held the answer, with its arguments and size, plus the attempts that failed, and is filed under the page the run looked up. It has no site records and no URL patterns. That is what a registry serving the fetch tool could store on its own. `bar3.py` reproduces the 2026-11-03 offline replay on head-0.1 exactly (17 of 24 refused).

Agreed before running: bar 2 unless two-call cards fail to make reads cheaper; trace cards become the default if their related reuse is within ~5 points of agent-written cards.

Runs: 30 tasks (head-0.1's 10 two-call and 11 three+ pages, the 9 hard multi-fetch tasks), reps 1-2, rep 3 on the 8 tasks where bar 3 refuses a card. Same-day cold-nowrite, cold-nowrite-related and miss-0.14 cold; noregistry-related at rep 1; warm-related-nowrite on every stored registry and every trace registry; the 10 API site records from miss-0.13 with same-day related baselines. 380 runs, 379 correct. warm-same was dropped. Before the run, sonatype-guava's two answer checks moved to Maven Central's `maven-metadata.xml`: central.sonatype.com's internal API returns a security-service block to this machine. Questions and grading are unchanged. The lid closed overnight and paused the run about 8 hours; three runs timed out after answering, with complete usage.

Dollars, weighted change against same-day no-write (mean of per-task changes in `report.md`). Write is the cold run; related is one read-only related reuse; 10 reuses is write plus 10 related reuses; break-even is reuses to pay back the write.

| | Write | Related | 1 reuse | 10 reuses | Break-even |
|---|---|---|---|---|---|
| Two calls, bar 2 | +29% | −2% | +13% | +1% | 14 |
| Two calls, bar 3 | +14% | −0% | +7% | +1% | ~690 |
| Two calls, trace | 0 | −7% | −4% | −7% | 0 |
| Three+, bar 2 | −3% | −16% | −9% | −15% | 0 |
| Three+, bar 3 | −4% | −11% | −7% | −10% | 0 |
| Three+, trace | 0 | −1% | −0% | −1% | 0 |
| Hard, bar 2 = bar 3 | +24% | −21% | −2% | −18% | 0.8 |
| Hard, trace | 0 | −41% | −24% | −38% | 0 |
| **All 30, bar 2** | +8% | **−15%** | −4% | **−13%** | 0.5 |
| **All 30, bar 3** | +5% | **−12%** | −3% | **−10%** | 0.4 |
| **All 30, trace** | 0 | **−14%** | −7% | **−13%** | 0 |

Plan (output ×1.6) is within 3 points of dollars everywhere. In tokens, trace is weaker (all-30 related −10% against −24% for bar 2), because trace reuse runs read more cache. Dollars stays the measure.

- **The bar: bar 2 (miss-0.14) wins overall, though the rule's condition is met.** Cards on two-call pages don't make reads cheaper (−2% weighted, +12% mean per page on the runs that stored one), and they take 14 reuses to pay back. That's the condition the rule set for bar 3. But bar 3 also refuses cards from 2-call runs on expensive pages (haproxy-config r1 and r3). Those carry the three+ gap, −16% against −11%. Across all 30 pages bar 2 is 3 points better at 10 reuses. That's well inside the noise: the same arm varies a median 16% between reps on a single task. Bar 3 refused 22 of 55 page cards: 20 of 23 on two-call pages, 2 of 21 on three+ pages, none on the hard set. Either bar is defensible; the gap is too small to matter next to trace cards.
- **Trace cards match agent-written cards with no write cost,** which meets the agreed rule. Related reuse across all 30 is −14% against −15%, and on the runs where miss-0.14 stored a page card the two tie (−10% / −10%). With nothing to write, trace is best at one reuse (−7% against −4%) and ties at 10 (−13%).
- **Trace cards win the hard set and lose where an agent generalizes.** Hard set: −41% against −21%. sonatype-guava is −78% against −6%, because a trace card filed under central.sonatype.com points straight at `maven-metadata.xml`, while agents' cards took 2 calls and were often refused. rust-vec-extract-if −29% against +63%, nginx −59% against −38%. Three+ pages: −1% against −16%. curl-manpage is −88% with the agent's card, which names the pattern `cmdline-opts/{option}.md`. With the trace card it's −4%: that card holds the start offset that answered a different option. systemd-exec (+88%), vim-options (+40%) and sqlite-pragma (+19%) also lose with trace cards, which send readers to an offset or section specific to another question.
- **Accuracy:** 125/126 reuse runs correct. The miss was an agent-written card: py-subprocess's card routes to `#popen-constructor`, and the reader answered from that section without reaching the priority-class constants. Trace cards: 0 wrong.
- **API site records don't pay on related reuse:** −1% weighted over 10 runs (terraform, galaxy and artifacthub −7% to −8%, puppet +2%, jetbrains +10%). These tasks already take one fetch, so the `select` hints have nothing left to save.
- **The lookup itself**, related question at rep 1 against noregistry-related, has a median of +5%. The +45% mean comes from two runs on the hard set (bash-histsize +395%, git-gc-auto +494%) with nearly the same web calls: run-to-run variance, not the lookup. This matches miss-0.13's +4% to +16%.

Verdict: the bar question is settled for the write-side policy, at bar 2 (miss-0.14), by a margin inside the noise. The larger result is that a card built from the trace, with no agent writing and no write cost, saves as much on reuse as an agent-written one: −14% against −15% related, −13% each at 10 reuses. It wins on hard-access sites and loses where the saving is a URL pattern only an agent would write. The viability bar (30% on related) is still not met on popular pages: −13% to −15% here.

## Next

- **Trace cards plus agent-written patterns (trace-0.2):** keep the trace card as the default and drop question-specific `start` offsets and sections from it, which misdirected systemd, vim and sqlite. Keep miss-0.13's site-record note, which asks agents only for URL patterns, the curl/cargo kind of saving. Rerun the three+ pages and the hard set the same way, with new same-day baselines.
- **The product shape this points to:** a registry that serves fetch builds cards with no agent writing and folds the lookup into fetch. That removes the write cost (this entry) and the lookup step (+4% to +16%, miss-0.13). Worth sketching in PLAN.md before more write-policy iterations.
- **Close the lid-sleep gap:** set the lid action to do nothing on AC for long batches, or run them on a machine that stays up.

## 2026-11-09: trace-0.2, trace cards without start offsets, and agent-written site records (`out_trace-0.2/drive.py`, `report.py`, `report.md`)

Why: step 2's trace cards lost on systemd, vim and sqlite, apparently because the card's `start` offset found the first question's answer and sent the related question to the wrong part of the page. They also lost on curl, where an agent-written card names the pattern `cmdline-opts/{option}.md`. trace-0.2 tests both fixes. Three registries, all built with no agent writing a page card:

- **v1:** step 2's trace card (`out_trace-0.1/build.py`), from each same-day cold-nowrite run.
- **v2:** the same card, lean: no `start` offset, and when the route is the whole page with no section, the whole page's size rather than the slice that answered. Same source run as v1.
- **trace-0.2:** a cold run under the new trace-0.2 iteration (miss-0.13's site-record note only; `run.py` sets the page-card bar out of reach, so no card note is sent), with a lean card from that run's trace merged into its registry next to any site record the agent wrote.

Runs: step 2's 30 tasks, reps 1-2. Phase 1: same-day cold-nowrite, cold-nowrite-related, trace-0.2 cold. Phase 2: warm-related-nowrite on all three registries. 360 runs, $24.90. The first launch at 09:39 hit the 5-hour limit, then the machine slept and lost power at 18:06 (an unclean shutdown) without running anything. Its 12 failed rows are kept in `out_trace-0.2_aborted-1109/`. The relaunch ran 18:33 to 23:34, paused 20:28 to 23:10 by the usage limit.

Dollars, weighted change against same-day no-write (mean / weighted per group in `report.md`):

| | Write | Related | 10 reuses |
|---|---|---|---|
| Two calls, v1 / v2 / trace-0.2 | 0 / 0 / +5% | −4% / −10% / −8% | −4% / −9% / −7% |
| Three+, v1 / v2 / trace-0.2 | 0 / 0 / −7% | −33% / −8% / −12% | −29% / −7% / −11% |
| Hard, v1 / v2 / trace-0.2 | 0 / 0 / +18% | −14% / −16% / −9% | −13% / −15% / −7% |
| **All 30, v1 / v2 / trace-0.2** | 0 / 0 / +0% | **−23% / −11% / −11%** | **−21% / −10% / −10%** |

The median per-task change on related reuse (added to `report.md` 2026-11-10) is −6% / −8% / −6% across all 30: a tie. The weighted change follows a few expensive runs, and on these 60 pairs one run makes most of the v1/v2 gap.

- **The v1/v2 gap is one run, not the offset.** Only 20 of 60 card pairs differ at all; the other 40 are byte-identical (one of them empty), because those runs used no offset. On the 20 that differ, related reuse costs $1.70 under v1 and $1.70 under v2. On the 40 identical pairs v2 costs 32% more in total ($2.31 against $1.74), but the median pair differs 4%. The gap is haproxy-config r1: with the same card, the v1 reader took 4 web calls ($0.05) and the v2 reader asked for a section `sha2([<avalanche>])` that doesn't exist, then paged through the manual by offset (11 web calls, $0.41, above no-write's $0.29). Without that pair the gap is +12%, without the top three −2%. That run is also haproxy's −80% / +8% in `report.md`. Dropping the offset neither fixed systemd, vim and sqlite nor hurt anything.
- **Run-to-run noise is a heavy tail, not a floor** (corrected 2026-11-10; this entry first read the 32% as a ~30% noise floor). Most reuse runs on the same card repeat within a few percent; now and then a reader misses the card's route and wanders, and on an expensive page one such run moves a weighted group figure by 10 points or more. So group gaps on the weighted measure don't separate arms at 2 reps: step 2's (bar 2 against bar 3, 3 points; trace against agent cards, 1 point) and this entry's. Medians are steadier but still move with a few tasks (three+: v1 −13%, v2 −2%; hard: v1 −8%, v2 −22%).
- **Agent-written site records don't pay yet.** They were stored in 11 of 60 cold runs (curl, npm, rsync, systemd, vim, git-gc-auto, sonatype-guava), all with a URL pattern; none on two-call pages. curl's −42% under trace-0.2 against −90% / −87% on v1 / v2 isn't the site record: in r1 the trace-0.2 cold run wrote no site record and its card routes to the whole man page, so reuse costs what no-write does ($0.095 against $0.094). In r2, with a site record and a card to `cmdline-opts/keepalive-cnt.md`, it costs $0.013, level with v1 and v2. The trace-0.2 cold run costs nothing extra across all 30 (+0% weighted) but +18% on the hard set.
- **Accuracy:** cold 60/60, no-write 120/120, reuse 179/180. The miss is py-subprocess r2 on v2, the same `#popen-constructor` card that missed in step 2.

Verdict: no change to the card. Without the offset the card is no better and no worse (median −6% against −8%), and site records add little at this sample size. The larger finding is the shape of the noise: identical cards repeat within a median 4%, and the 32% gap between them is one reader that missed the route. Card variants now differ less than such runs move a group, so the typical trace card saves about 6-8% on related reuse, and what decides the headline is how often a reader wanders.

## Next

- **Rescore step 2 on medians** (`out_miss-0.12/report.py`): its bar 2 / bar 3 and trace / agent-card gaps were read on the weighted measure.
- **Read the runs that wander, not more card variants:** haproxy v2 r1, rust-vec-extract-if (+160% to +266% on every arm), py-subprocess, vim-options. Do readers ignore the card, guess section names, or page by offset? A card that fixes that (say, the page's real heading form) is worth more than offset or section tweaks.
- **More reps only where a rescored gap is still close:** the 40 identical-card pairs here already measure the same card twice, so a separate floor batch isn't needed.
- **Folding lookup into fetch** and the product sketch in PLAN.md still stand (2026-11-08).
- **Close the lid-sleep gap** (2026-11-08): this batch lost a morning to it.

## 2026-11-10: trace-0.3, checked offline and not run: the cheapest of several traces (`out_trace-0.3/check.py`)

Why: a trace card is only as good as the route its one source run found. curl's was −4% in step 2, built from a run that answered from the man page, and −90% in trace-0.2, built from runs that found `cmdline-opts/keepalive-cnt.md`. The proposal (PLAN.md, 2026-11-10) was a v3 registry that pools every cold-nowrite trace on a page, keeps the route returning the fewest tokens, and turns a question term in the route's path into a `{placeholder}` in its notes, as the agent's curl card did. Before spending the ~$3.75 on 60 reuse runs, `check.py` built each v3 card from step 2's and trace-0.2's cold-nowrite traces (4-5 per task) and compared it with trace-0.2's v1 cards.

- **15 of 60 cards differ from v1.** 6 differ only in the start offset, changing the slice by 1-5% (apache, bash, linux-tcp7, sqlite, systemd r2, vim). 4 are likely worse for a different question: render-free-spindown's original question's own 142-token section (`Spinning down on idle`), rsync r1's Debian man page from a 10-call run, haproxy's `#3.2` for the named section (3 tokens smaller) and k8s r1 dropping its section (13 tokens smaller). 3 look better: npm r2 (no card before), gha r2 and pytest r1 (a named section for an offset). systemd r1's change of site is a toss-up.
- **Templating has nothing to do.** It applies only to curl, and trace-0.2's v1 curl cards already route to `cmdline-opts/keepalive-cnt.md` (−90%).
- **The pool is too uniform.** Every trace answers the same original question with the same fetch tool, whose slices cap near 10k tokens, so the cheapest route differs from the latest one mostly in offsets. A real registry pools traces from different questions on a page; testing that needs a third question per page, so the related question scored isn't also a source.

Verdict: v3 isn't run. With 3 likely improvements in 60 cards and the noise above, a null result is the expected outcome and wouldn't tell a small effect from none. On this task set a single-trace card is already near what pooling gives, so card iteration stops here. The default stays the trace card (v1), at about −6% to −8% median on related reuse with no write cost.

## Next

- **Folding lookup into fetch:** the lookup costs about +5% median (miss-0.13; step 2), close to the whole typical card saving. A fetch that checks the registry itself and returns the route's content removes that step. Sketch it in PLAN.md, then measure it against trace-0.2's v1 runs.
- **Rescore step 2 on medians** (`out_miss-0.12/report.py`), so the record of agent cards against trace cards rests on the steadier measure.
- **Close the lid-sleep gap** (2026-11-08) before the next long batch.

## 2026-11-10: Firecrawl /agent on two related questions (not an iteration)

Why: if a fetch provider's own agent does the searching, the calling agent makes one call either way and a breadcrumb has nothing left to cut there. Firecrawl's `/agent` (v2, model `spark-2`) takes a prompt, optional `urls` and an `effort`, and returns an answer with its sources. Probe on the related questions of redis-set and curl-manpage: (A) `/agent` with the prompt only; (B) `/agent` with the v1 card's page and route URLs and `effort: "low"`; (C) a `/scrape` of the page the v1 reader answered from. Script and results are outside the repo (session scratchpad).

| | A: prompt only | B: card URLs, low effort | C: scrape |
| --- | --- | --- | --- |
| curl, time (free run) | 21.1 s | 10.6 s | 0.4 s, 1 credit, 558 chars |
| redis, time (free runs) | 17.3 s | 10.7 s | 0.4 s, 1 credit, 57,691 chars |
| redis, paid run | 8 credits, 36.9 s | 6 credits, 10.8 s | |

- **All seven `/agent` runs were correct.** The first five of a day are free and report `creditsUsed: 0` (a fifth, redis prompt-only, took 21.2 s), so prices come only from the two paid redis runs: 8 credits ($0.030 on Hobby, $0.008 on Standard) with the prompt, 6 with the card's URL.
- **A card hit routes around `/agent`:** one scrape (1 credit, under a second) against 6-8 credits and 11-37 s. Firecrawl's own docs say the same: for a known URL, scrape (or its JSON mode) is cheaper; `/agent` is for when the URLs are unknown. So this mostly confirms their guidance and adds nothing about `/agent` itself.
- **Firecrawl's scrape returns the whole page:** redis is 57,691 chars (about 14k tokens) against the 557-token section the local fetch serves from the same card. On Firecrawl, section slicing is where much of a card's saving would come from.
- **Not a fair test of `/agent`.** Both questions are answered in one or two calls; `/agent` is built for deep tasks across many pages. Passing a card's URLs as `urls` narrows its search to a route recorded for another question, and on a deep task that risks a confident wrong answer, which this task set (one answer, one page) can't catch.

Verdict: `/agent` is dropped from the test plan. Its search loop runs on Firecrawl's side, where breadcrumbs could enter only if Firecrawl used them. The Firecrawl question that matters is the scrape and search path (`firecrawl-mcp`), where the calling agent still pays for wrong pages and whole-page reads: next is a Firecrawl backend for the fold fetch tool.

## Next

- **Firecrawl backend for fold-0.1** (`BC_BACKEND=firecrawl` in `bc/web_server.py`): the same fetch tool with pages from Firecrawl's scrape, sliced locally. Arms: noregistry on stock `firecrawl-mcp`, noregistry on the Firecrawl-backed tool (to separate the tool's slicing from the cards), and fold on the Firecrawl-backed tool with cards built from its own cold runs.
- **Measure fold-0.1 on the local fetch** against trace-0.2's v1 runs, as planned, so the Firecrawl result has a local one to compare with.
- **Rescore step 2 on medians** (`out_miss-0.12/report.py`).
- **Close the lid-sleep gap** (2026-11-08) before the next long batch.

## 2026-11-10: firecrawl-0.1 on redis-set, and a no-question baseline per server (`out_firecrawl-0.1/`)

Why: whether cards still save when pages come from Firecrawl, the question the `/agent` probe set aside. The Firecrawl-backed fetch tool differs from a stock Firecrawl setup in two ways at once (it slices pages, and fold serves cards), so three arms separate them, all on the related question, 1 rep:

- **1, stock:** `noregistry-related` on the stock `firecrawl-mcp` server (3.39.0, launched by `bc/firecrawl_mcp.py`): what a Firecrawl user pays today.
- **2, tool:** `noregistry-related` on our fetch tool with `--backend firecrawl`: Firecrawl's pages, our slicing, no cards.
- **3, fold:** `warm-related-nowrite --iteration fold-0.1 --backend firecrawl`, its card built (`out_trace-0.1/build.py`, v1) from arm 2's run on the original question, since a trace doesn't depend on whether the run had a registry. Cards are built from Firecrawl traces, not reused from local ones: Firecrawl's Markdown has its own headings and sizes.

`baseline` ("Reply with the word OK") ran once per setup with only that arm's servers. The tool definitions load even though baseline allows no tools.

| | Claude $ | Baseline | Net | Credits | Net + credits (Hobby) | Calls |
| --- | --- | --- | --- | --- | --- | --- |
| 1, stock | $0.196 | $0.167 (30 tools, 41,776 tokens) | $0.029 | 6 | $0.052 | 2 scrapes |
| 2, tool | $0.067 | $0.010 (2 tools, 2,420 tokens) | $0.057 | 1 | $0.061 | 1 fetch, whole page (~15k tokens) |
| 3, fold | $0.012 | $0.010 | $0.002 | 1 | $0.006 | 1 fetch, the card's section (618 tokens) |
| source run (arm 2, original question) | $0.020 | | | 2 | | 2 fetches |

All correct. A credit is $0.0038 on Hobby.

- **Cards save as much on Firecrawl as locally:** fold against the tool is −83% in Claude dollars, against −85% on the local fetch (noregistry-related $0.066, fold-0.1 $0.008-0.010). The Firecrawl-built card worked unchanged.
- **Slicing alone doesn't pay here.** Net of each baseline, stock and tool cost about the same ($0.052 and $0.061). The stock agent's first scrape (63 KB) passed Claude Code's tool-output limit and was saved to a file it couldn't read, so it re-scraped with Firecrawl's `query` format, which answers on Firecrawl's side: fewer Claude tokens, about 5 more credits. So on this page the whole saving is the card's, not the tool's.
- **The stock server's overhead is per turn.** Its 30 tool definitions (`crawl`, `agent`, `monitor_*`, `interact` and others) are about 42k tokens, written once and re-read from cache on every later turn. Arm 1 took 3 turns against the baseline's 1, so part of its $0.029 net is still definitions. That is Firecrawl's packaging, not something cards fix, and it is kept out of the card comparison; runs with many turns should report cost per turn too.
- **Section names carry Firecrawl's Markdown:** the card's section is `Optional arguments  Copy link to clipboard`, the docs' anchor text kept in the heading. It works on the Firecrawl backend but wouldn't on the local one, so a route moves between fetch tools only as a URL (PLAN.md).

Verdict: on one task near the best case (redis was −72% locally; the median card saves 6-8%), the card's saving survives the move to Firecrawl, and the tool's slicing adds nothing that Firecrawl's `query` format doesn't. The hard set at 1 rep tests whether that holds where runs take several calls.

## Next

- **firecrawl-0.1 on the hard set** (9 tasks, 1 rep; `out_firecrawl-0.1/drive.py`), all four runs per task, with each arm's baseline subtracted. The stock arm may use only scrape, search and map (and WebSearch): `crawl` and `agent` can spend hundreds of credits in one call. Its definitions still load, so its overhead is unchanged; on redis it used only scrape.
- **Measure fold-0.1 on the local fetch** against trace-0.2's v1 runs (`out_fold-0.1/` has the runs; no LOG entry yet).
- **Rescore step 2 on medians** (`out_miss-0.12/report.py`).
- **Close the lid-sleep gap** (2026-11-08) before the next long batch.

## 2026-11-10: firecrawl-0.1 on the hard set (`out_firecrawl-0.1/drive.py`, `report.py`)

Why: the redis entry above is one task near the best case. This runs the 9 hard multi-fetch tasks the same way, 1 rep: source run, tool, fold and stock (scrape, search and map only), 36 runs and 110 credits.

The redis baselines were cold: the prompt cache was empty, so the tool definitions were written fresh. Back-to-back runs read them from cache, and the first stock run here cost $0.021, under the $0.167 cold baseline. Warm baselines, run right after a cold one, are $0.010 (stock) and $0.002 (tool); `report.py` subtracts the cold or warm one according to whether a run's first turn read the definitions from cache. Credits are exact: ours from each run's `calls.log`, stock's from its scrapes (1 each, 5 with the `query` format, which matched the balance in every job but one where it lagged).

Net per task (Claude dollars less baseline, plus credits at the Hobby price), related question:

| Task | Stock | Tool | Fold | Stock's calls |
| --- | --- | --- | --- | --- |
| bash-histsize | $0.030 | $0.082 | $0.063 | 1 query scrape |
| gha-matrix-max-jobs | $0.080 | $0.385 | $0.043 | 2 searches, 1 query scrape |
| git-gc-auto | $0.029 | $0.035 | $0.037 | 1 query scrape |
| heroku-daily-restart | $0.066 | $0.056 | $0.048 | search, query + Markdown scrape |
| mdn-fetch-credentials | $0.146 | $0.063 | $0.057 | query + 2 Markdown scrapes |
| nginx-keepalive-requests | $0.030 | $0.073 | $0.141 | 1 query scrape |
| render-free-spindown | $0.035 | $0.026 | $0.026 | 1 Markdown scrape |
| rust-vec-extract-if | $0.030 | $0.081 | $0.053 | 1 query scrape |
| sonatype-guava | $0.096 | $0.074 | $0.074 | 2 Markdown scrapes |
| **Total** | **$0.542** | **$0.876** | **$0.541** | |

All 27 correct. Credits: stock 41, tool 30, fold 20.

- **Cards alone (fold against tool): median −9%, total −38%.** The median matches the local fetch's (v1 on the hard set, −8% median in trace-0.2). The total is mostly gha, where the tool run wandered (10 turns, 7 fetches, $0.385) and the fold run didn't. nginx went the other way (+93%). So the card's effect doesn't depend on the fetch backend.
- **The stock agent answers on Firecrawl's side.** It used `query` (a question answered by Firecrawl's model, 5 credits) on 7 of 9 tasks, and on 4 (bash, git-gc, nginx, rust) a single query scrape of a URL it knew was the whole run: 2 turns, $0.030. The tool arm reads the page itself: median +21% against stock, total +62%.
- **Fold against stock: a tie.** Totals $0.541 and $0.542; fold is cheaper on 5 tasks and stock on 4 (median −23%, which is that coin flip). Stock wins where one query on a guessed URL is enough (bash, git-gc, nginx, rust); fold wins where stock read whole Markdown pages or searched (mdn, sonatype, heroku, gha). In Claude dollars alone stock is cheaper ($0.386 against $0.464), and fold's edge is credits (20 against 41). At the Standard price ($0.001 a credit) stock leads by about 12%.
- **The card's "skip the search" value is small here:** these are popular docs, and the stock agent guessed the right URL without a search in 7 of 9 tasks.
- **sonatype got no card:** Firecrawl flattens the Maven XML into one line, which the trace builder doesn't count as a successful fetch. gha's fold run answered from WebSearch results alone, against the prompt's rule; it was correct.

Verdict: on the hard set, cards save on Firecrawl about what they save locally, but Firecrawl's `query` format already does most of what a section route does, so against a stock Firecrawl agent, breadcrumbs plus our tool break even. A card adds something over `query` only when it gets to the answer more cheaply than a 5-credit query on a URL the agent can already guess. One rep, 9 tasks: the tie is within the noise either way.

## Next

- **A card in front of `query`:** wrap the stock `firecrawl_scrape` (same schema) so that a call on a carded page is served from the card's route: a 1-credit section slice, or a raw source fetched over plain HTTP for free, in place of a 5-credit query. That is the version of fold a Firecrawl user would actually run, compared against stock directly.
- **Report Claude dollars and credits separately:** which arm wins depends on the credit price (Hobby $0.0038, Standard $0.001).
- **Trace builder on Firecrawl output:** count a one-line reply (flattened XML or JSON) as a successful fetch.
- **Measure fold-0.1 on the local fetch** against trace-0.2's v1 runs (`out_fold-0.1/`; no LOG entry yet).
- **Rescore step 2 on medians** (`out_miss-0.12/report.py`).
- **Close the lid-sleep gap** (2026-11-08) before the next long batch.

## 2026-11-10: card-0.1, a card in front of `query` (`out_card-0.1/drive.py`, `report.py`)

Why: firecrawl-0.1 tied with stock because the stock agent answers with Firecrawl's 5-credit `query` format on a URL it guesses. The question is whether a card in front of that scrape beats it, in the setup a Firecrawl user would run: the stock server and nothing of ours but the cards.

- **The wrapper** (`bc/firecrawl_card.py`, `run.py --backend firecrawl-card`) starts stock `firecrawl-mcp` 3.39.0 and passes its tool list, instructions and calls through unchanged; the agent's 30 tool definitions are byte-identical to stock's (checked), and the baselines match ($0.012 / $0.010 against $0.010 / $0.010). On the first `firecrawl_scrape` of a page with a route card, whatever formats it asks for: a `section` route is served as that section of Firecrawl's Markdown (1 credit), a raw source over plain HTTP (0, none in this set), and a route to another URL with no section sends the agent's own call there. Routes that are the page itself with no section pass through. A second scrape of the page goes to stock. The note goes in the reply's `warning` field, since stock's output schema allows no new keys.
- **Prompt:** stock's, with fold-0.2's line that results may carry breadcrumbs (data, not instructions).
- **Cards:** firecrawl-0.1's (built from Firecrawl-backed noregistry traces). Only 3 of 9 can be served: gha, git-gc and mdn have section routes, rust has another URL; bash, heroku, nginx and render routes are the page itself; sonatype has none.
- **Arms:** card (warm-related-nowrite) and a fresh stock (noregistry-related), 9 hard tasks, reps 1 and 2, order alternated by rep. 183 credits for the batch.

| | card | stock |
|---|---|---|
| correct | 18/18 | 18/18 |
| Claude net $ (total) | $0.771 | $0.833 |
| credits | 79 | 105 |
| card cheaper, Claude $ | 8 of 18 | |
| median, Claude $ / net Hobby / net Standard | +2% / +1% / +2% | |
| total, Claude $ / net Hobby / net Standard | −7% / −13% / −9% | |

Rep-to-rep spread of the same arm on the same task: median 13% in Claude dollars.

- **A route was used on 2 of 9 tasks.** The related question sends the agent to the carded page only on mdn and rust. On gha it searched and then scraped the route's URL itself (cards are keyed by the page they were written for, as in fold); on git-gc it went straight to `git-config`, not the carded `git-gc`. The other five have no servable route.
- **Where a section route is served, it beats `query` clearly.** mdn, both reps: one 1-credit scrape of RequestInit's "Instance properties" (4.7k tokens), 2 turns, $0.046 and $0.044, against stock's 2-3 scrapes, 6-7 credits, $0.063 and $0.118. That's the case the wrapper was for.
- **The redirect hurt.** rust's route (ExtractIf, from the `extract_if` question) is the wrong page for `pop_if`: the agent's query went there, came back empty, and it scraped Vec.html again, then fought the 600k-char page (r1: 8 turns, 16 credits, $0.096 against stock's $0.029). A route to another URL is an earlier question's answer page, not a cheaper way to read this one.
- **heroku is cheaper in the card arm with no card served** ($0.025 and $0.023 against $0.051 and $0.052, 1 credit against 2 and 15): both card runs scraped the dyno-shutdown page as Markdown first, and both stock runs searched. Only the prompt line differs; two reps isn't enough to call that a prompt effect, and it's about half the total gap.
- **Everything else is a tie,** as it should be where the wrapper passes calls through (bash, nginx, render, sonatype, git-gc: within a cent).

Verdict: a card in front of `query` wins when it is hit and its route is a section, about −30% to −60% on mdn with 1 credit against 6-7. But with cards keyed to the page an earlier question started from, the related question hits a servable card on 1 task in 9, so overall it's −7% Claude dollars and −13% net at Hobby in total but +2% median, inside the noise. The redirect does harm and should go. What limits a card on Firecrawl here is hit rate, not the saving per hit.

## Next

- **card-0.2:** drop the redirect (name the other URL only), and rerun rust and gha to see that.
- **Hit rate:** key a section route by the page it reads as well (gha's agent scraped the route's own URL), with the section offered, not forced, since it was found for another question.
- **A third question per page** (from trace-0.3): tells whether a section found for one question serves the next, which decides how far the second change can go.
- **heroku:** a third rep of both arms, to see whether the card prompt's line alone changes the first scrape.
- Carried over: trace builder on one-line Firecrawl replies; fold-0.1 on the local fetch (`out_fold-0.1/`); rescore step 2 on medians; the lid-sleep gap.

## 2026-11-11: card-0.2 and a prompt-only arm (`out_card-0.2/drive.py`, `report.py`)

Why: two things in card-0.1 to settle before more work on hit rate. The redirect made rust worse, and heroku was about half of the total gap with no card served, so the card arm's prompt line might have been doing the work.

- **card-0.2** (`--iteration card-0.2`): a route to another URL with no section is named in the reply's `warning`, and the agent's own scrape goes to stock as asked. card-0.1's redirect stays behind `BC_CARD_REDIRECT=1` (`--iteration card-0.1`). Only rust has such a route, so card-0.2 ran on rust only (r1-r2); on the other 8 tasks the wrapper behaves as in card-0.1, and those runs stand in.
- **promptonly:** card-0.2's wrapper and prompt on an empty registry, 9 tasks, r1-r2. It separates the prompt line from the cards.
- **stock r3:** a third stock rep on all 9, for 3 reps.
- 29 runs, 198 credits, all correct. Each arm is compared on per-task means over reps.
- **Dropped:** promptonly bash r1, the batch's first run after the cache had expired overnight. It paid to write the 42k tokens of tool definitions ($0.179 against $0.019 for r2), which neither setup's baseline measures, since both read them from cache.

| | Claude $ median / total | net Hobby median / total | cheaper on |
|---|---|---|---|
| promptonly vs stock (the prompt line alone) | +1% / +8% | 0% / +15% | 4 / 9 |
| card-0.2 vs promptonly (the cards, net of the line) | −17% / −17% | −32% / −29% | 5 / 9 |
| card-0.1 vs stock (3 stock reps) | +5% / −2% | +2% / −11% | 2 / 9 |
| card-0.2 vs stock | +1% / −10% | +1% / −18% | 3 / 9 |

Rep-to-rep spread, stock and promptonly: median 21% in Claude dollars.

- **Dropping the redirect fixes rust:** card-0.2 is $0.041 and 11 credits per run against stock's $0.042 and 11.3, where card-0.1 was $0.072 and 14.5. The named URL didn't pull the agent off course.
- **The prompt line alone saves nothing:** median 0, total worse (promptonly had a 9-turn nginx run and a 4-turn git-gc run that stock never had). The agents open the same way: stock's first web call was a scrape in 24 of 27 runs, promptonly's in 15 of 17.
- **heroku is not a card effect, and not clearly the prompt's:** promptonly heroku r1 matched card-0.1's two runs (2 turns, 1 credit), r2 matched stock (4 turns). Which page the agent guesses first decides heroku, and 2-3 reps can't separate that from luck.
- **The cards' saving is mdn, the one task where a section was served:** $0.045 and 1 credit against stock's $0.085 and 8 (3 reps). Take out mdn and heroku and card-0.2 is level with stock on the other 7.
- **"card-0.2 vs promptonly" overstates the cards,** since promptonly's own outliers (nginx, git-gc) are in its denominator; against stock, which has 3 reps, the total is −10% in Claude dollars and −18% net at Hobby, and the median +1%.

Verdict: card-0.2 does no harm where it isn't hit and saves about half where a section route is served. The prompt line doesn't explain card-0.1's gain. So the card's value on Firecrawl is per hit, as card-0.1 found, and these cards hit 1 task in 9. Whether that can rise is the question for the next step: matching the route's own page, and a third question per page to see whether a section found for one question serves another.

## Next

- **Keep going on Firecrawl first (decided 2026-11-11; PLAN):** card-0.3 serves a recorded section when the agent scrapes the route's own page, with a way back to Firecrawl's full reply; and a third question per page tests whether a section found for one question serves another. Where the main effort lies (Firecrawl or the local fetch) is decided after those runs.
- **A truly cold baseline per setup** (first run after the cache expires), so a cold first run can be kept instead of dropped.
- Carried over: trace builder on one-line Firecrawl replies; fold-0.1 on the local fetch (`out_fold-0.1/`); rescore step 2 on medians; the lid-sleep gap.

## 2026-11-11: card-0.3, matching the route's own page (`out_card-0.3/drive.py`)

Why: cards are keyed by the page an earlier question started from, and related questions often scrape a different one. card-0.3 (`--iteration card-0.3`, `BC_CARD_ROUTE_MATCH=1`) also serves a section route when the agent scrapes the page the route reads, noting that the section was found for another question (and which), and that a second scrape gets Firecrawl's own reply.

- **Reach, checked offline before any run:** across the 27 stock runs and card-0.1/0.2's runs on the 9 hard tasks, only gha's related question scrapes a page a section route reads without the card's own page (workflow-syntax, the matrix question's route). git-gc's agents go to git-config (route: git-gc), heroku's to dyno-shutdown-behavior (route: dyno-restarts, no section), rust's route has no section, mdn already hits, sonatype has no card. So card-0.3 ran gha only, r1-r2; on the other 8 it behaves as card-0.2.
- **gha r1:** answered from the smartscope blog after the GitHub changelog and never scraped workflow-syntax; no card served. $0.086, 4 turns.
- **gha r2:** scraped workflow-syntax last and was served the matrix section (877 tokens, 1 credit), which doesn't hold the background-steps answer; it answered from the blog it had already read, without a second scrape. $0.079, 5 turns.
- Against stock's 3 reps on gha ($0.080 mean) card-0.3 is $0.082, level, inside the spread; card-0.1/0.2 on gha was $0.090.

Verdict: matching by the route's page does no harm (the one wrong section cost 1 credit and was ignored) but adds no hits that matter on these tasks: the only new match served a section for another question. The 9 related questions can't measure hit rate further, because each points at a different section or page than its card. That is what the third question per page is for; card-0.3 stays on as the wrapper for it.

## 2026-11-11: third-0.1, a third question per page (`out_card-0.3/drive_third.py`, `report_third.py`)

Why: the related questions can't measure whether a stored section serves another question, since each points at a different section or page than its card (card-0.3 above). Each of the 9 hard tasks now has a `third` question (tasks.yaml) on the page firecrawl-0.1's card routes to, answer checked at the source (`run.py verify`: all OK). New conditions `warm-third-nowrite` and `noregistry-third`.

- Of the 9 cards only 3 have a section route, so only those can be served: **mdn** (the third answer, the keepalive body limit, is in the stored section, Instance properties), **git-gc** (the gc --auto hook is in HOOKS, not the stored CONFIGURATION) and **gha** (the 50 MB job-output total is in jobs.<job_id>.outputs, not the stored matrix section). 3 reps of each arm. The other 6 routes are a whole page or an offset, which the wrapper passes to stock: 1 rep each, as a no-harm check.
- Arms: card-0.3 with firecrawl-0.1's cards, against stock firecrawl-mcp. 32 runs including 2 baselines, 168 credits, 15/15 correct per arm.
- **Baselines:** the card baseline ran first on a cold cache ($0.168, nothing read from cache), so the card arm is netted of card-0.1's two warm card baselines ($0.011); stock's own here was warm ($0.012). No task run was cold.

| task (reps) | what card-0.3 did | card $ net / cr | stock $ net / cr |
|---|---|---|---|
| mdn (3) | served the right section, 3/3 | $0.043 / 1 | $0.095 / 15.7 |
| git-gc (3) | served the wrong section, then a 5-credit `query`, 3/3 | $0.031 / 6 | $0.068 / 1 |
| gha (3) | wrong section by route match in r2-r3, then a full `markdown` scrape and a `query`; r1 used the alias URL, no match | $0.032 / 6.3 | $0.010 / 5 |
| other 6 (1 each) | passed to stock; rust got a named-URL note | $0.037 median | $0.023 median |

Card-0.3 vs stock: section-route tasks −54% median and −38% total in Claude dollars (−25% median, −38% total net at Hobby); the other 6 +30% median, +72% total (rust $0.085 and 21 credits against $0.019 and 6, 8 turns, after the named-URL note); all 9 +19% median, +8% total.

- **A right section saves as before:** mdn is about half of stock's Claude dollars and 1 credit against 16, like card-0.1/0.2's mdn hit. Stock's agents wandered (fetch, Request/keepalive, RequestInit, a search) in all 3 runs.
- **A wrong section didn't mislead:** no wrong answers. What it costs depends on the agent's next step. On git-gc the agent sent a `query`, which came to $0.03 below stock (stock read the whole page's Markdown for 1 credit) but 5 credits more. On gha it re-scraped the 180k-character page as `markdown` with `maxAge: 0` and then queried, about 3x stock, whose agents went straight to a `query` on the alias URL (`writing-workflows/workflow-syntax-for-github-actions`), which no card matches.
- **The other 6 should be level by construction** (the wrapper forwards as is). At 1 rep they are noise apart from rust, where the note naming ExtractIf.html came before an 8-turn run. card-0.2's 2 rust runs with the same note were level with stock, so this is one run, not yet a finding.
- **Hit rate is still open:** these third questions were written to land on carded pages, so they measure a hit's value, not how often hits happen. On the 9 tasks, 3 cards hold a section, and one of their 3 third questions fell inside the stored section.

Reading the runs more closely:

- **gha's wrong section came from a question the wrapper ignored.** In r2-r3 the agent's first call was a `query` whose prompt was the third question itself ("What is the maximum total size of all job outputs…"). card-0.3 matches by page alone, so it served the matrix section anyway. The agent then re-scraped as `markdown` (212k characters, past the tool-output limit, saved to a file it couldn't read without Bash) and sent a second `query`.
- **git-gc's credits:** stock read the whole page's Markdown (35k characters, 1 credit), which holds HOOKS. The card arm got CONFIGURATION (9k characters, 1 credit), then a 5-credit `query`: fewer tokens, more credits. Its first call had no prompt, so the wrapper had nothing to check against.
- **mdn's saving is routing, not slicing:** every agent starts on the fetch() page, which doesn't hold the answer (stock's first `query` there returned "the page does not contain this"). The card, built from an earlier fetch() question, points at RequestInit's Instance properties, so the first call gets the answer.
- **The other 6 tasks:** on bash, nginx, render and sonatype the wrapper did nothing, so their gaps are run-to-run variation (bash: both arms' first `query` returned junk, and the card-arm agent then pulled the 50 KB page while the stock agent went to the right page). Totals across all 9 are $0.325 for card against $0.300 for stock; without rust, $0.240 against $0.281 (−15%).

Verdict: on Firecrawl a served section is worth about half a task when it holds the answer, and most of that is the route to another page. When it doesn't hold the answer, the answer stays right and the cost depends on the recovery. And when the agent asks a `query`, the wrapper already has the question and can check the section against it before serving (card-0.4).

## 2026-11-11: card-0.4, the stored section only when it matches the agent's `query` (`out_card-0.4/drive.py`)

- **`bc/section_match.py`:** ranks 15-line windows of the page against the `query` prompt with BM25 (no model call). The stored section is served only if its best window scores at least 0.8 of the page's best; otherwise the call goes to stock as asked, and the 1-credit section scrape is logged as `card-skip`. Heading-sized chunks failed: BM25's length penalty let short intros outscore the long stored sections (7/10). Scrapes without a prompt behave as in card-0.3. `--iteration card-0.4` (`BC_CARD_PROMPT_CHECK=1`, route matching on).
- **Offline, 10 prompts on the three section-route pages** (scratchpad, not kept): 9/10 right. All 4 gha prompts outside the matrix section are skipped (ratios 0.14-0.45) and the matrix question served; the gc --auto hook is skipped (0.65); gc.aggressiveWindow and all 3 mdn questions are served. The miss is gc.auto (0.77): the OPTIONS paragraph that refers to `gc.auto` outscores its CONFIGURATION entry. A miss of that kind sends the call to stock, so it costs the 1-credit scrape, not a wrong answer. The bar stays at 0.8 rather than being tuned to these 10.
- **`_serve` on the first calls from third-0.1:** the gha `query` on workflow-syntax goes to stock (0.14); mdn's on fetch() is still served RequestInit's section.
- **Live, third question, 3 reps each, cache warm, all correct:** mdn $0.043 and 1 credit (served 3/3), as card-0.3. On gha all 3 agents scraped the alias URL (`writing-workflows/workflow-syntax-for-github-actions`), as stock's did, so no card matched and the check never fired: $0.011 and 5 credits, level with stock ($0.010, 5). 18 credits.

Verdict: card-0.4 keeps mdn's saving and does no harm on gha, but these runs didn't exercise the skip itself. Only the offline and `_serve` tests show it. Matching gha's alias URL would exercise it, and would add nothing there: the skip forwards the agent's `query`, the same call stock makes, plus 1 credit.

## Next

- **The rust named-URL note:** 2 more reps of rust third, to see whether the note causes long runs.
- **Hit rate:** decide how to estimate it (questions sampled per site, not written per card) before the Firecrawl-or-local decision (PLAN).
- **A truly cold baseline per setup:** this batch's card baseline was cold and had to be replaced; run a throwaway warm-up first.
- Carried over: trace builder on one-line Firecrawl replies; fold-0.1 on the local fetch (`out_fold-0.1/`); rescore step 2 on medians; the lid-sleep gap.

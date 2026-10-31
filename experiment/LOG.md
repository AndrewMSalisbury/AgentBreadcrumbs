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
| miss-0.5 | Cards need 2,000+ fetched tokens and must be filed under a looked-up site | `out_miss-0.5_smoke/` |

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

# Experiment log

## 2026-10-26: hard set, rep 1, narrow cards

18 hard tasks, Sonnet, one rep. Savings are against cold-nowrite (no registry, no writing). Raw results in `out_hard_r1_narrowcards/`.

| | No-write cold | Warm same | Warm related |
|---|---|---|---|
| Mean total tokens | 25.9k | 19.4k | 41.4k |
| Mean per-task cut | | 0% | -57% (costlier) |
| Fetches + searches | 2.3 | 1.4 | 2.1 |
| Correct | 100% | 100% | 100% |

Write cost averaged +15k tokens per task; 3/18 tasks recover it within 2 reuses.

Cold agents wrote narrow cards. Each held its own answer ("keepalive_requests default (1000)") and only the sections around it, so related questions found nothing useful, fetched again and then paid to merge a section in. Worst cases: gha-matrix +441% (card pointed at the limits page; the related answer is on workflow-syntax), nginx +294%, rust +127%.

Fixed: the pypi related regex rejected "10.0 GB".

## 2026-10-27: hard set, rep 1, page-map cards

The write rule, schema descriptions and write docstring now ask for a map of the whole page: up to 12 main sections, each naming what it covers, with no values. Cold-nowrite rows are reused from 2026-10-26 (its prompt is unchanged; the tool docstrings grew by a few dozen tokens).

### Fix: related baseline

The report compared warm-related with the no-write cost of the *original* question, but several related questions are harder in their own right: Rust `pop_if` loses its version badge under `section=`, and GHA background steps aren't on the page cold agents carded. A new arm, `cold-nowrite-related`, answers the related question with no registry and no writing. Warm-related is now measured against it. Rows for this arm are also appended to `out_hard_r1_narrowcards/` (it never touches the registry), so both reports use the same baseline.

### Results (rep 1, against same-question no-write baselines)

| | Narrow cards | Page-map cards |
|---|---|---|
| Write cost (cold − cold-nowrite) | +15.3k | +34.1k |
| Cut, warm same | 0% | -8% |
| Cut, warm related | -36% | -53% |
| Fetches related (nw → warm) | 2.5 → 2.1 | 2.5 → 2.4 |
| Correct | 100% everywhere | 100% everywhere |

Page-map cards cost twice as much to write: cold agents read more of the page to map it (nginx +280k, git-config +138k). They also did not make related runs cheaper.

Most of the warm-related loss comes from warm agents **writing**, not from reading. In the page-map run, the 9 related runs that wrote averaged +110% against their baseline (pypi, heroku, gha, git-gc, rust, bash and others). The 9 that didn't write were near the ~15% lookup overhead or better (sonatype -53%, mdn -25%, render -16%). Writes also hit schema rejections and retries (`answers` sent as a list, notes over 200 characters).

The card did route correctly when it applied: git-config related went lookup → one fetch at the carded offset. That one fetch was a 9k-token chunk, though, while the no-write agent found the small raw `gc.adoc` file. Fetch-tool limits, not cards, drive several cases: directive anchors on nginx and git-config aren't headings, so `section=` fails, and Rust's `section=` drops the stable-since badge.

### Read-only warm related (`warm-related-nowrite`)

Same registries, related question, write forbidden: this separates what reading saves from what warm agents spend writing. Run for both card styles; 36/36 correct, no write calls.

| Related, vs cold-nowrite-related | Narrow cards | Page-map cards |
|---|---|---|
| With writing (warm-related) | 36% higher | 53% higher |
| Read-only | 1% lower | 4% lower |
| hard_access / docs / coding | -16% / +1% / +14% | -8% / +3% / -6% |

- Writing explains the whole warm-related loss. Without it, warm related costs about the same as no breadcrumbs.
- Reading saves almost nothing on related questions either. Savings appear only where a cold agent took a wrong route that a card or site record avoids: sonatype -71%/-58% (direct API), puppet -33% both, bash -44%/-18%, mdn -11%/-31%.
- Lookup overhead without the write rule is about 2-3% (terraform, galaxy, artifacthub), not the ~15% seen with it. Most of that 15% was the longer write rule in the system prompt, not the lookup.
- Cards can send agents the expensive way: git-config related is +31%/+38% because the card points at a 9k-token chunk of the HTML page, while no-write agents find the small raw `gc.adoc`. One outlier: narrow-card rust read-only took 11 fetches and +104%; page-map rust was -25%.

Verdict for the hard set at rep 1: L1 cards fail the ≥30% bar on related questions, read-only or not. The value seen comes from access routes (APIs, raw sources), not section maps.

## Later

- **Writing policy.** Warm agents should rarely write: writing turned a ~0% read result into +36-53%. Write only on an empty lookup, or let the registry merge sections from fetch logs instead of agent-written records.
- **Route-first breadcrumbs.** Record the cheapest way to get a page's content (raw source, API, Markdown version) rather than a section map, since that's where every saving came from.

- **Skip lookup on one-fetch pages.** On tasks that cold agents answer with a single fetch, warm runs cost about 10% more: the lookup adds tokens and saves nothing. Try telling agents when a lookup is worth it, or folding breadcrumbs into fetch results.
- **Reps 2 and 3.** Every number above is a single run; single runs like gha's 140k related run may be outliers. Run 3 reps per arm before drawing conclusions.

## 2026-10-28: hard set, reps 2 and 3, page-map cards

Same code and prompts as the 2026-10-27 page-map run, all six arms, reps 2 and 3 run in parallel. Before running, three answers had moved on and were updated in `tasks.yaml`: hashicorp/google 8.8.1 → 8.9.0, puppetlabs/stdlib 10.1.0 → 10.1.1, puppetlabs/apache 13.4.0 → 13.5.0. 216/216 runs correct. `out/report.md` now averages reps 1-3.

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

## 2026-10-29: www. fix and route-first cards (hard set, reps 1-3)

### Fix: www. hosts

`host_of` and `page_id` now fold `www.` into the bare host, so `www.gnu.org` and `gnu.org` are one site. Stored card URLs keep `www.`. In the page-map runs only bash was affected: its three cold registries were re-keyed and its three warm arms rerun. The page-map totals barely moved (warm related +19%, read-only cut 13%); bash warm-same went from +17% to -18%.

### Route-first cards (`--cards route`, results in `out_route/`)

The page card swaps the section map for `route`: the smallest source with the page's content (raw file, API, Markdown version or the page itself), the fetch arguments that worked on it, a rough size and notes on what failed. The site record asks for URL patterns that work for other pages (`{name}`), and site-wide lookups list each carded page's route. No-write baselines are shared with `out/`, since those arms never touch a registry. 324/324 correct.

| Related question, mean per-task change vs no-write | Page-map | Route |
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

### Lean write policy (`--cards route --write lean`, results in `out_lean/`)

Same route cards, new write rule: no page card on a page answered with one fetch and no search (a site record is still allowed if it adds a URL pattern), and no page card when lookup's card or site pattern already covers the page. A smoke run first showed puppet cold writing a site record after one fetch; that record carried the `{owner}-{name}` API pattern, so the rule was relaxed to allow it rather than tightened. No-write baselines are copied from `out_route/`. All four registry arms rerun, reps 1-3; 216/216 correct.

| Mean per-task change vs no-write | Route | Lean |
|---|---|---|
| Write cost (cold - cold-nowrite) | +19.7k | +9.9k |
| Warm same, all | +13% | +1% |
| Warm related, all | +14% | **-6%** |
| Read-only related, all | -13% | -16% |
| Warm related, hard_access / docs / coding | +44% / +35% / -38% | +13% / +6% / -37% |
| Warm same, coding | -39% | -18% |
| Write cost recovered within 2 reuses | 1/18 | 6/18 |

- The policy works where it was aimed. Warm agents mostly stopped writing on one-fetch pages: sonatype related +12% → -41%, pypi +58% → -27%, puppet +75% → +18%, terraform +47% → +18%. Warm related now comes out cheaper than no-write overall for the first time, but -6% is still far from the 30% bar.
- It also stops writes that were needed. Lean cold agents skipped the page card on multi-fetch coding pages: git-gc 0/3 (each cold run fetched the HTML page, then the raw `gc.adoc`, and wrote nothing), rust 0/3, bash 1/3. With no card, warm same on coding fell from -39% to -18% (rust -44% → +17%, git-gc -34% → -11%). The rule opens with "decide whether to write" and lists three reasons not to, which seems to push agents to under-write.
- Writes still slip through on one-fetch pages: jetbrains related wrote 1/3, artifacthub warm same wrote 3/3 (+58%).

### Lean2: saying when to write (`--write lean2`, results in `out_lean2/`)

Lean reworded to lead with when a page card is expected ("whenever getting it took more than one fetch or render, or a search"), keeping the skips for one-fetch pages and pages a card or site pattern covers. Same setup as lean: baselines from `out_route/`, four registry arms, reps 1-3. A usage limit cut off 48 warm runs (all warm runs for bash, compose, mdn and rust, plus some for nginx, git-gc, gha and r2); they were rerun after the reset. 216/216 correct.

| Mean per-task change vs no-write | Route | Lean | Lean2 |
|---|---|---|---|
| Write cost | +19.7k | +9.9k | +9.9k |
| Warm same, all | +13% | +1% | +2% |
| Warm related, all | +14% | -6% | +5% |
| Read-only related, all | -13% | -16% | -14% |
| Warm related, hard_access / docs / coding | +44% / +35% / -38% | +13% / +6% / -37% | +8% / +14% / -8% |
| Warm same, coding | -39% | -18% | -12% |
| Cold runs that wrote, coding | 100% | 33% | 50% |
| Write cost recovered within 2 reuses | 1/18 | 6/18 | 4/18 |

- The rewording helped on the pages it was aimed at, and hurt elsewhere. git-gc and rust cold runs wrote 2/3 (lean 0/3), and bash 3/3. But mdn cold wrote 1/3 (lean 3/3): r1 and r3 took 4 fetches each and wrote nothing. nginx cold wrote 1/3, so 2 of 3 warm-related nginx runs found no card, paged through the 20k-token page by offset and then wrote one (+78%, lean -57%).
- hard_access and docs keep most of lean's gains (one-fetch pages are still rarely carded), so the skip half of the policy holds. The "write here" half is followed only about half the time, whichever way it's worded.
- Lean2 is no better than lean overall. With 3 reps, single tasks swing by 50-100 points between policies (nginx related -57% → +78%, mdn same -38% → +23%). Those swings come from whether the cold run happened to write, not from what the rule says.

## Next

- **Move the write policy out of the prompt.** Two prompt wordings get the skip half right but leave page cards on multi-fetch pages to chance (33-50% on coding, against 100% under the route rule). Instead: keep the route rule's unconditional "write a card", and have the harness enforce the skip. Count fetches per run (the web and registry servers can share a per-run file) and reject page cards from one-fetch runs, plus page cards for a URL a stored site pattern already covers.
- **Schema retries.** Warm and cold agents still send `answers` as a list and get rejected, costing a retry per write. Accept a list and join it, or say "one string" in the write docstring.
- **Skip lookup on one-fetch pages** still applies: hard_access and docs read-only runs are +1-3% from lookup overhead alone.
- **Subdomains.** `pypi.org` lookups miss the `docs.pypi.org` card, and puppet's site record lands on `forgeapi.puppet.com` while agents look up `forge.puppet.com`. Folding subdomains is a design question, not done.

## 2026-10-29: harness-enforced writes (`--write enforced`, results in `out_enforced/`)

The route rule's "write a page card" stays in the prompt. The harness decides when a card is pointless:

- The web server logs every fetch and render, and a `PreToolUse` hook on WebSearch (passed with `--settings`; it runs under `--setting-sources ""`) logs every search. Both write to the run's `calls.log`.
- `write` refuses a page card, before schema checks so it isn't retried, when the run had at most one fetch and no search, or when a stored site record's URL pattern covers the card's URL or `route.url`. `{name}` matches one path segment, and a placeholder whose name mentions a path or slashes (`{group path with slashes}`) may span several. Site records are always accepted.
- Each fetch or render result ends with a line saying whether a page card from this run would be stored, and the rule tells agents to skip the card when the latest line says no. Without that line, agents would still spend a write turn on cards that get refused.
- Nowrite arms are unchanged (no log, no note), so baselines can be copied from `out_route/` as for lean. Rows record `write_results` (stored / rejected / not_stored).

Smoke (`out_enforced_smoke/`, cold, rep 1): puppet fetched once, saw "would not store" and wrote nothing. git-gc fetched the HTML page, then the raw `gc.adoc`, and stored a route card after one schema rejection.

### Results (reps 1-3)

No-write baselines and the baseline row are copied from `out_lean2/` (originally `out_route/`). All four registry arms ran, reps 1-3 in parallel, with no interruptions. 216/216 correct, and every answer verified at its source before the run.

| Mean per-task change vs no-write | Route | Lean | Lean2 | Enforced |
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

- **The skip works.** On hard_access no arm wrote anything: 0 of 54 cold and warm runs, and the registry never had to refuse a card, because agents always heeded the note. Warm related on hard_access is +1%, the best of any policy. The ~+15% left on one-fetch warm-same runs is the write rule's length in the system prompt, as before. Cold agents also stopped writing site records on one-fetch API pages (puppet wrote one under lean), probably because the note reads as "don't write" when it only covers page cards.
- **Coding cards came back, but not all the way.** 13/18 coding cold runs stored a card (git-gc, bash, mdn and nginx 3/3), against 33-50% under the prompt wordings. Rust stored 1/3, and the other two runs were eligible (2 and 4 fetches plus a search, note said "would store") but never called write. Read-only coding related is -38%, near route's -43%. With writing it's -22%, against route's -38%: nginx related +28% (2.7 fetches) and rust same +28% with only one card.
- **Docs blew up.** Warm-related agents wrote in 12/18 docs runs. A related question usually needs a second page or a search, so the run qualifies, and the "would store a page card" note on every fetch result seems to work as an invitation. gha +93% (110k: more searches than the no-write run, plus a write), github +119%, pypi +165%, render +65%, heroku +27%. Read-only docs related is -11%, so again the loss is all writing.
- **Search loophole.** A search counts like a second fetch, so one search plus one fetch qualifies for a card. 9 of 42 stored cards came from such runs: all 8 pypi writes, plus one github. Pypi agents look up `pypi.org`, miss the `docs.pypi.org` card (the subdomain issue), search, fetch once and write again: write cost +35.5k, and warm runs +165-207%. With writing forbidden, the same agents skip the search and answer in one fetch (11.8k).
- **Schema retries are now the biggest fixed cost.** 36 of 42 stored writes followed a rejection, 34 of them for `answers` sent as a list. Each one is an extra turn over the whole context.

Verdict: harness enforcement fixes what it was aimed at (no writes on one-fetch pages, more cards on multi-fetch coding pages), but overall it's worse than lean (+20% vs -6% with writing). The loss comes from writes the rule allows: warm agents on docs pages and pypi's search-then-write loop. Read-only related is the best yet at -18%, so the registry contents are better. The writes cost more than they save.

## Next

- **Accept `answers` as a list** and join it. It's a cheap change and it affects every arm: 34 of 42 enforced writes paid a retry turn.
- **Show only refusals.** Drop the "would store" note and say only when a card would be refused, to see whether the positive note is what invites the docs writes.
- **Count fetches, not searches,** for eligibility, or count a search only when it led to a page lookup had nothing on. Pypi's loop also needs the subdomain fix.
- **Warm writes on related pages.** Even legitimate warm cards (a second page for a related question) rarely pay back at 3 reps. A stricter test would allow page cards only in runs where lookup returned nothing for the site.


## 2026-10-30: list `answers` accepted (`--write enforced`, results in `out_answers/`)

Same as enforced, with one registry change: a page card whose `answers` is a list of strings has it joined with "; " before any check, so it's stored on the first write instead of rejected. Agents still send a list almost every time. No-write baselines and the baseline row are copied from `out_enforced/`. All four registry arms, hard set, reps 1-3 in parallel. 216/216 correct.

Before the run, `verify` found three easy-set answers had moved (not used here, fixed for later): openvsx rust-analyzer 0.4.3098 → 0.4.3101, amo Dark Reader 4.9.133 → 4.9.134, and the Claude docs dropped "32 MB for standard endpoints". The claude-vision related question now asks for the Messages request limit on the first-party API (128 MB).

| Mean per-task change vs no-write | Route | Lean | Lean2 | Enforced | Answers list |
|---|---|---|---|---|---|
| Write cost | +19.7k | +9.9k | +9.9k | +15.6k | +9.6k |
| Warm same, all | +13% | +1% | +2% | +11% | -1% |
| Warm related, all | +14% | -6% | +5% | +20% | +11% |
| Read-only related, all | -13% | -16% | -14% | -18% | -15% |
| Warm related, hard_access / docs / coding | +44% / +35% / -38% | +13% / +6% / -37% | +8% / +14% / -8% | +1% / +80% / -22% | +17% / +31% / -16% |
| Cold runs that stored a page card, coding | 100% | 33% | 50% | 72% | 50% |
| Write cost recovered within 2 reuses | 1/18 | 6/18 | 4/18 | 5/18 | 5/18 |

- **The retries are gone.** Writes that hit a schema rejection fell from 36 of 42 stored to 6 of 37. The six left are real limit violations: `route/notes` over 200 characters (6) and one `route/select` sent as a string. Write cost fell from +15.6k to +9.6k, as low as lean, and pypi's write cost halved (+35.5k → +16.9k) because its search-then-write loop no longer pays a retry each time.
- **Docs are less bad, for the same reason.** Warm related on docs went from +80% to +31%. Warm agents still write on 8 of 18 docs related runs (pypi and gha 3/3, heroku 2/3), but each write now takes one turn. gha +39% and pypi +109% are still the worst tasks.
- **Coding stored fewer cards this time, and that has nothing to do with the change.** 9/18 coding cold runs stored a card, against 13/18. mdn wrote 0/3 after 4 fetches each (3/3 before), so its warm related runs found nothing and came out +39% (enforced -38%). Bash stored 2/3 and rust 1/3. The note said "would store" on all of them. Whether an eligible agent writes is still up to it.
- **nginx write cost doubled (+105k)**, but from fetching, not writing: cold r1/r2 took 6 and 5 fetches of the 20k-token page (4 and 4 before). There's still one `notes` rejection per nginx run.
- hard_access warm related moved from +1% to +17%, but all of that is artifacthub (-11% both times) and sonatype (-41% → +51%: one of three warm runs wrote a card). The other four are unchanged at about +15%, which is the write rule's length in the prompt.

Verdict: accepting a list is a clear win on what it targets, and the fixed cost of writing is now as low as it's been (+9.6k). Overall it's still worse than lean (+11% vs -6% warm related). What's left is docs agents writing on related pages, plus coding cold runs that don't write when they should. With 3 reps, which tasks end up carded swings the totals by about as much as anything we've changed.

## Next

- **Raise or truncate `route/notes`.** It's the only remaining schema retry (6 of 37 writes, every nginx run). Truncating at 200 characters, with a "(truncated)" marker, would remove it.
- **Show only refusals**, and **count fetches, not searches**: both still apply, aimed at the docs writes.
- **More reps, or fixed cold registries.** Warm results depend mostly on whether the cold run happened to write. To test a reading-side change, reuse one set of cold registries across policies, so the comparison isn't redone on new cold luck.

## 2026-10-30: only cold agents write (results in `out_coldonly/`)

Lean is the best policy so far. This tests one structural change against it: cold agents write under the lean rule, and warm agents only read (no write rule in the prompt, told not to call write). It uses lean's own cold registries, so cold luck is the same on both sides. `warm-related-nowrite` already existed in `out_lean/`. The new `warm-same-nowrite` arm (hard set, reps 1-3, 54 runs) reads the same registries. Rows and cold registries were copied from `out_lean/`. 54/54 correct.

| Mean per-task change vs no-write | Lean (warm agents write) | Only cold writes |
|---|---|---|
| Write cost (cold) | +9.9k | +9.9k (same runs) |
| Warm same, all | +1% | **-3%** |
| Warm related, all | -6% | **-16%** |
| Warm same, hard_access / docs / coding | +12% / +8% / -18% | -9% / 0% / -1% |
| Warm related, hard_access / docs / coding | +13% / +6% / -37% | -4% / -6% / -38% |
| Write cost repaid within 2 reuses | 6/18 | 7/18 |

- **Only cold writes beats lean** on both questions overall, and in every group except coding same. Part of the gain is the write rule's length: dropping it from warm prompts saves about 1.5k per run, which is +10-15% on the ~11k one-fetch tasks (pypi, r2, render, the registry APIs). The rest is warm writes that never paid back (gha same, 4-5 fetches and a write: +20-70%).
- **Coding same (-18% → -1%) is noise, not a loss.** Lean's cold runs left a record for only 6 of 18 coding tasks and 1 of 18 docs tasks, so most warm runs on both arms had an empty registry. Split by registry:

  | Mean change vs no-write | Registry had records (18 runs) | Registry empty (36 runs) |
  |---|---|---|
  | Same, lean warm / read-only | -18% / **-27%** | +19% / +15% |
  | Related, lean warm / read-only | +7% / **-6%** | -1% / -8% |

  Where a record exists, reading without writing is better on both questions. In the empty-registry runs both arms are really no-registry runs, but they still range from -8% to +19%: outliers like git-gc r1 (84k, 5 fetches), bash r1 (96k) and nginx r2 (70k) all had empty registries. That spread is the noise floor at 3 reps.
- The viability bar still fails overall (-16% related, bar -30%). Coding related (-38%) passes, as it has under every route-card policy.

Verdict: warm agents shouldn't write. With that settled, the limit is what cold agents leave behind. Lean leaves too little (no record for most coding and docs tasks), and the route rule leaves a lot at about twice lean's write cost.

## Next

- **Cold-side policy, with warm agents read-only.** Compare route, lean and enforced+list cold registries, all scored read-only. Read-only related arms exist for all three: route -13% (coding -43%), lean -16% (-38%), answers -15% (-33%). Each now needs a `warm-same-nowrite` arm on its own registries, then the comparison is write cost against read-only savings.
- **Truncate `route/notes`** at 200 characters instead of rejecting it (the last schema retry).
- **More reps for the deciding run.** The empty-registry spread (-8% to +19%) is as big as most effects measured here.

## 2026-10-31: write on miss (`--write miss`, results in `out_miss/`)

All agents get the same prompt, and its step 3 is one line ("call write only if a lookup result asks for breadcrumbs"). The first lookup in a run that finds no page card and no site URL pattern for its target ends with the lean rule and the card format (~450 tokens). The registry refuses a page card for a page that already has one. `route/notes` and `access/notes` over 200 characters are now truncated rather than rejected, in every mode. No-write baselines and the baseline row are copied from `out_lean/`. Four registry arms, hard set, reps 1-3. A usage limit cut off 120 warm runs, and a memory-pressure kill stopped the first rerun; the rest were rerun one rep at a time. 215/216 correct: one read-only gha related run (empty registry) concluded no background-step limit is documented.

| Mean per-task change vs no-write | Lean | Only cold writes | Miss |
|---|---|---|---|
| Write cost | +9.9k | +9.9k | **+4.4k** |
| Write cost, hard_access / docs / coding | +8.2k / +3.3k / +18.3k | same | +6.9k / +2.6k / +3.6k |
| Warm same, all | +1% | **-3%** | +4% |
| Warm related, all | -6% | **-16%** | -9% |
| Warm related, hard_access / docs / coding | +13% / +6% / -37% | -4% / -6% / -38% | +4% / +3% / -35% |
| Read-only related, all | -16% | -16% | -5% |
| Write cost repaid within 2 reuses | 6/18 | 7/18 | 7/18 |

- **The registries are nearly empty under both lean and miss.** For 12 of 18 tasks, cold agents left no record in any rep under either policy, and the two policies' registries differ on only two tasks (nginx: lean carded 2 of 3, miss 0; heroku: lean 1, miss 0). Coding cold runs wrote 6/18 under both. Most of the read-only gap (-16% vs -5%) is those two tasks plus baseline noise: pypi, sonatype and git-gc had empty registries under both, yet lean's read-only runs were 24-46% cheaper than miss's.
- **Clean signal: the prompt overhead mostly goes away.** On one-fetch tasks with empty registries, warm related went from +13-18% under lean to +4-11% under miss (terraform and galaxy +18% → +4%, render +14% → +5%, compose +15% → +11%). The note goes only to agents that miss, and ignoring it costs one read.
- **Write cost halved** (+9.9k → +4.4k) with the same number of coding writes, mostly because coding cold runs no longer carry the rule through every turn (+18.3k → +3.6k).
- Warm agents wrote in 2/54 same and a few related runs: the refusal held, and no card was written twice.

Verdict: miss mode is the deployable shape. One prompt, a smaller fixed cost than lean, and the database still grows on misses. But the hard set can't show what the registry is worth when cold agents leave almost nothing: 12 of 18 tasks never get a record. The next step is the cold side: getting a miss to leave a record when the answer took more than one fetch.

## Next

- **Cold-side policy inside miss mode.** The note's lean rule is followed about a third of the time on multi-fetch pages. Try the route rule's unconditional "write a page card" in the note, plus the enforced refusal for one-fetch runs (so the decision isn't left to the agent), or harness-side eligibility in the note itself ("this run has taken N fetches: write a card").
- **More reps, or tasks known to need several fetches.** With most registries empty, a task's result rests on cold luck and baseline noise (±35% on an empty registry).

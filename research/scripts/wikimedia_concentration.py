"""Page concentration in Wikimedia's daily pageviews, human vs automated: a public stand-in.

No docs host publishes how concentrated agent requests are across pages (see
research/concentration-ask.md). Wikimedia publishes every article's daily views, split into
user and automated traffic (automated: clients its heuristics flag as bots that don't say so).
That's reference lookups, not docs and not AI agents specifically, so it shows the shape of
the tail, not the number a registry needs.

Input is one day's pageview_complete files (dumps.wikimedia.org/other/pageview_complete/),
one per agent type. Rows are "wiki title page_id access daily_total hourly"; views are
summed over access methods (desktop, mobile-web, mobile-app) per title, for one wiki.

  python wikimedia_concentration.py pageviews-YYYYMMDD-user.bz2 pageviews-YYYYMMDD-automated.bz2 [--wiki en.wikipedia]
"""
import argparse, bz2, collections, pathlib

ap = argparse.ArgumentParser()
ap.add_argument("files", nargs="+", type=pathlib.Path)
ap.add_argument("--wiki", default="en.wikipedia")
args = ap.parse_args()

views = {}
for path in args.files:
    kind = path.name.split("-")[-1].split(".")[0]  # user / automated
    c = views[kind] = collections.Counter()
    prefix = args.wiki + " "
    with bz2.open(path, "rt", encoding="utf-8", errors="replace") as f:
        for line in f:
            if not line.startswith(prefix):
                continue
            parts = line.split(" ")
            # 6 columns with a page id, 5 without (a known issue in the dumps).
            total = parts[4] if len(parts) >= 6 else parts[3]
            if total.isdigit():
                c[parts[1]] += int(total)

pct = lambda a, b: f"{100 * a / b:.1f}%" if b else "-"
everyone = set().union(*views.values())
for kind, c in views.items():
    ranked = [n for _, n in c.most_common()]
    total, pages = sum(ranked), len(ranked)
    top = lambda share, n=pages: sum(ranked[:max(1, round(n * share))])
    once = sum(1 for n in ranked if n == 1)
    print(f"\n{args.wiki} {kind}: {total} views, {pages} pages viewed")
    print(f"  views on top 1% / 10% / 25% of the pages it viewed: {pct(top(.01), total)} / {pct(top(.10), total)} / "
          f"{pct(top(.25), total)}")
    print(f"  same, ranked against all {len(everyone)} pages anyone viewed: {pct(top(.01, len(everyone)), total)} / "
          f"{pct(top(.10, len(everyone)), total)}")
    print(f"  views on top 100 / 1000 pages: {pct(sum(ranked[:100]), total)} / {pct(sum(ranked[:1000]), total)}")
    print(f"  pages viewed once: {pct(once, pages)} of pages, {pct(once, total)} of views")
    print(f"  views on pages viewed 2+ times that day: {pct(total - once, total)}")
if {"user", "automated"} <= views.keys():
    u, a = views["user"], views["automated"]
    top_user = {p for p, _ in u.most_common(max(1, round(len(u) * .01)))}
    ta = sum(a.values())
    print(f"\nautomated views on the user top 1% of pages: {pct(sum(n for p, n in a.items() if p in top_user), ta)}; "
          f"on pages no user viewed: {pct(sum(n for p, n in a.items() if p not in u), ta)}")

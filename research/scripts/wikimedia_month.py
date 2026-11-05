"""Page concentration in a month of Wikimedia pageviews: how repeat demand grows with the window.

wikimedia_concentration.py counts one day. A registry's breadcrumb outlives the day it was
written, so this reads a monthly pageview_complete file (dumps.wikimedia.org/other/
pageview_complete/monthly/), whose rows carry each title's views per day, and asks: of a
day's views, how many land on a page that was viewed on an earlier day (the day before, the
week before, or any earlier day of the month)? Counting by day rather than by view keeps one
client's burst of reloads from counting as a repeat, though a bot that comes back daily still
does. Views, not distinct clients, so it remains an upper bound.

Rows are "wiki title page_id access monthly_total daily", daily like "A5B6E1" (A = day 1).
Rows are sorted by wiki then title, so a title's access methods are adjacent and summed, and
reading stops after the wiki's block. --titles restricts a second set of figures to a list of
titles (first tab-separated column), e.g. the pages computing WikiProjects tag.

  python wikimedia_month.py pageviews-YYYYMM-user.bz2 [--wiki en.wikipedia] [--titles t.tsv]
"""
import argparse, bz2, re, pathlib
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("file", type=pathlib.Path)
ap.add_argument("--wiki", default="en.wikipedia")
ap.add_argument("--titles", type=pathlib.Path)
ap.add_argument("--days", type=int, default=31)
args = ap.parse_args()
D = args.days
DAY = re.compile(r"([A-_])(\d+)")
subset = set()
if args.titles:
    subset = {l.split("\t")[0].strip() for l in args.titles.open(encoding="utf-8") if l.strip()}


class Acc:
    def __init__(self):
        self.tot, self.same2 = np.zeros(D, np.int64), np.zeros(D, np.int64)
        self.rep = {k: np.zeros(D, np.int64) for k in (1, 7, D)}  # D = any earlier day
        self.months, self.buf = [], []

    def add(self, row):
        self.buf.append(row)
        if len(self.buf) >= 200_000:
            self.flush()

    def flush(self):
        if not self.buf:
            return
        m = np.array(self.buf, np.int64)
        self.buf = []
        self.tot += m.sum(0)
        self.same2 += (m * (m >= 2)).sum(0)
        c = np.concatenate([np.zeros((len(m), 1), np.int64), np.cumsum(m > 0, 1)], 1)  # c[:, d] = days seen before d
        for k, r in self.rep.items():
            before = c[:, :D] - c[:, np.maximum(np.arange(D) - k, 0)]
            r += (m * (before > 0)).sum(0)
        self.months.append(m.sum(1))

    def report(self, name):
        self.flush()
        ranked = np.sort(np.concatenate(self.months))[::-1]
        total, pages = int(ranked.sum()), len(ranked)
        pct = lambda a, b: f"{100 * a / b:.1f}%" if b else "-"
        top = lambda share: int(ranked[:max(1, round(pages * share))].sum())
        once = int((ranked == 1).sum())
        w = slice(7, D)  # days 8.., where a 7-day lookback is complete
        print(f"\n{name}: {total} views, {pages} pages viewed in {D} days")
        print(f"  month, views on top 1% / 10% / 25% of pages: {pct(top(.01), total)} / {pct(top(.10), total)} / "
              f"{pct(top(.25), total)}; top 100 / 1000 pages: {pct(int(ranked[:100].sum()), total)} / "
              f"{pct(int(ranked[:1000].sum()), total)}")
        print(f"  pages viewed once in the month: {pct(once, pages)} of pages, {pct(once, total)} of views")
        print(f"  a day's views on pages viewed 2+ times that day (all days pooled): "
              f"{pct(self.same2.sum(), self.tot.sum())}")
        print(f"  days 8-{D}, a day's views on pages viewed the day before / in the 7 days before / on any earlier day: "
              f"{pct(self.rep[1][w].sum(), self.tot[w].sum())} / {pct(self.rep[7][w].sum(), self.tot[w].sum())} / "
              f"{pct(self.rep[D][w].sum(), self.tot[w].sum())}")
        print("  by day, views on pages viewed on any earlier day: " + ", ".join(
            f"day {d}: {pct(self.rep[D][d - 1], self.tot[d - 1])}" for d in sorted({2, 4, 8, 15, 22, D}) if d <= D))


acc, sub = Acc(), Acc()
prefix, prev, row, unsorted = args.wiki + " ", None, None, 0


def emit(title, row):
    acc.add(row)
    if title in subset:
        sub.add(row)


with bz2.open(args.file, "rt", encoding="utf-8", errors="replace") as f:
    started = False
    for line in f:
        if not line.startswith(prefix):
            if started:
                break
            continue
        started = True
        parts = line.rstrip("\n").split(" ")
        if len(parts) < 6:
            continue
        title = parts[1]
        if title != prev:
            if row is not None:
                emit(prev, row)
            if prev is not None and title < prev and not title.startswith('"'):  # quoted titles sort unquoted
                unsorted += 1
            prev, row = title, [0] * D
        for day, n in DAY.findall(parts[5]):
            d = ord(day) - 65
            if d < D:
                row[d] += int(n)
    if row is not None:
        emit(prev, row)

kind = args.file.name.split("-")[-1].split(".")[0]
print(f"{args.file.name}: {unsorted} titles out of order (each counted as a separate page)")
acc.report(f"{args.wiki} {kind}")
if args.titles:
    sub.report(f"{args.wiki} {kind}, {len(subset)} listed titles")

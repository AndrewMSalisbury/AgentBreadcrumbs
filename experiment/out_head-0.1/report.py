"""head-0.1: what a breadcrumb saves on popular reference pages, in four measures.

  python out_head-0.1/report.py

Same definitions as rescore.py: runs averaged over reps per task, each arm against the
no-write run on the same question, "mean of per-task changes / weighted change". Net is a
write plus one read-only related reuse. Pages are grouped by their no-registry cost, from
the mean web calls of their four baseline runs (both questions, reps 1-2): one call, two,
or three and more.
"""
import collections, json, pathlib, statistics, sys

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE.parent))
from rescore import plan

MEASURES = {"tokens": lambda r: r["usage"]["total"],
            "uncached": lambda r: r["usage"]["total"] - r["usage"]["cache_read"],
            "dollars": lambda r: r["cost_usd"],
            "output": lambda r: r["usage"]["output"],
            "plan": lambda r: r["plan"]}
SINGLE = (("write", "cold", "cold-nowrite"), ("same", "warm-same-nowrite", "cold-nowrite"),
          ("related", "warm-related-nowrite", "cold-nowrite-related"))
WEB = ("mcp__web__fetch", "mcp__web__render", "WebSearch")

rows = [json.loads(l) for l in (HERE / "results.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
runs = collections.defaultdict(list)  # (condition, task) -> rows
for r in rows:
    r["plan"] = plan(r, HERE)
    runs[(r["condition"], r["task"])].append(r)
tasks = sorted({r["task"] for r in rows})


def mean(cond, task, f):
    return statistics.mean(f(r) for r in runs[(cond, task)])


def web(r):
    return sum(v for k, v in r["tool_calls"].items() if k in WEB)


base_calls = {t: statistics.mean(web(r) for c in ("cold-nowrite", "cold-nowrite-related") for r in runs[(c, t)])
              for t in tasks}
groups = {"all": tasks,
          "one call": [t for t in tasks if base_calls[t] <= 1.25],
          "two calls": [t for t in tasks if 1.25 < base_calls[t] < 3],
          "three+ calls": [t for t in tasks if base_calls[t] >= 3]}


def change(ts, arm, base, f):
    """(mean of per-task changes, weighted change); arm and base are lists of conditions summed."""
    a = {t: sum(mean(c, t, f) for c in arm) for t in ts}
    b = {t: sum(mean(c, t, f) for c in base) for t in ts}
    per = statistics.mean(a[t] / b[t] - 1 for t in ts)
    return per, sum(a.values()) / sum(b.values()) - 1


pct = lambda x: f"{100 * x:+.0f}%"
for g, ts in groups.items():
    print(f"\n{g} ({len(ts)} pages)")
    print(f"{'measure':9} " + " ".join(f"{l:>15}" for l, *_ in SINGLE) + f" {'net':>15}")
    for m, f in MEASURES.items():
        cells = [change(ts, [a], [b], f) for _, a, b in SINGLE]
        cells.append(change(ts, ["cold", "warm-related-nowrite"], ["cold-nowrite", "cold-nowrite-related"], f))
        print(f"{m:9} " + " ".join(f"{pct(p) + ' / ' + pct(w):>15}" for p, w in cells))

cold = [r for r in rows if r["condition"] == "cold"]
stored = [r for r in cold if r["write_results"]["stored"]]
print(f"\ncold runs storing a record: {len(stored)}/{len(cold)}")
for g, ts in list(groups.items())[1:]:
    print(f"  {g}: {sum(r['task'] in ts for r in stored)}/{sum(r['task'] in ts for r in cold)}")
print("correct: " + ", ".join(f"{c} {sum(r['correct'] for r in rows if r['condition'] == c)}/"
                              f"{sum(r['condition'] == c for r in rows)}" for c in sorted({r['condition'] for r in rows})))
print("pages by group: " + "; ".join(f"{g}: {', '.join(ts)}" for g, ts in list(groups.items())[1:]))

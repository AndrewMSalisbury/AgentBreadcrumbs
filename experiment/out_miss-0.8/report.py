"""miss-0.8 (3-call card bar) on the two-call pages, against head-0.1's miss-0.7 runs.

  python out_miss-0.8/report.py

Same definitions as out_head-0.1/report.py: runs averaged over reps per task, each arm
against the no-write run on the same question (head-0.1's cold-nowrite and
cold-nowrite-related), "mean of per-task changes / weighted change". A miss-0.8 cold run
that stored nothing left an empty registry, so its reuse runs are the baselines.
"""
import json, pathlib, statistics

HERE = pathlib.Path(__file__).parent
HEAD = HERE.parent / "out_head-0.1"
MEASURES = {"tokens": lambda r: r["usage"]["total"],
            "uncached": lambda r: r["usage"]["total"] - r["usage"]["cache_read"],
            "dollars": lambda r: r["cost_usd"],
            "output": lambda r: r["usage"]["output"]}
WEB = ("mcp__web__fetch", "mcp__web__render", "WebSearch")
FALLBACK = {"warm-same-nowrite": "cold-nowrite", "warm-related-nowrite": "cold-nowrite-related"}


def load(d):
    rows = [json.loads(l) for l in (d / "results.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    return {(r["condition"], r["task"], r["rep"]): r for r in rows}


head, new = load(HEAD), load(HERE)
tasks = sorted({t for c, t, p in new if c == "cold"})
reps = sorted({p for c, t, p in new if c == "cold"})
web = lambda r: sum(v for k, v in r["tool_calls"].items() if k in WEB)


def get(src, cond, t, p):
    if src is new:
        if cond in FALLBACK and not new[("cold", t, p)]["write_results"]["stored"]:
            return head[(FALLBACK[cond], t, p)]
        if cond == "cold" or cond in FALLBACK:
            return new[(cond, t, p)]
    return head[(cond, t, p)]


def change(src, arm, base, f):
    a = {t: statistics.mean(sum(f(get(src, c, t, p)) for c in arm) for p in reps) for t in tasks}
    b = {t: statistics.mean(sum(f(head[(c, t, p)]) for c in base) for p in reps) for t in tasks}
    return statistics.mean(a[t] / b[t] - 1 for t in tasks), sum(a.values()) / sum(b.values()) - 1


ARMS = (("write", ["cold"], ["cold-nowrite"]), ("same", ["warm-same-nowrite"], ["cold-nowrite"]),
        ("related", ["warm-related-nowrite"], ["cold-nowrite-related"]),
        ("net", ["cold", "warm-related-nowrite"], ["cold-nowrite", "cold-nowrite-related"]))
pct = lambda x: f"{100 * x:+.0f}%"
print(f"{len(tasks)} two-call pages, reps {reps}")
print(f"{'':18} " + " ".join(f"{l:>15}" for l, *_ in ARMS))
for m, f in MEASURES.items():
    for label, src in (("miss-0.7", head), ("miss-0.8", new)):
        print(f"{m + ' ' + label:18} " + " ".join(f"{pct(p) + ' / ' + pct(w):>15}"
                                                  for p, w in (change(src, a, b, f) for _, a, b in ARMS)))
for label, src in (("miss-0.7", head), ("miss-0.8", new)):
    cold = [src[("cold", t, p)] for t in tasks for p in reps]
    print(f"\n{label}: cold stored {sum(r['write_results']['stored'] > 0 for r in cold)}/{len(cold)}, "
          f"write calls {sum(r['tool_calls'].get('mcp__registry__write', 0) for r in cold)}, "
          f"refused {sum(r['write_results']['not_stored'] + r['write_results']['rejected'] for r in cold)}, "
          f"correct {sum(r['correct'] for r in cold)}/{len(cold)}")
    print("  web calls: " + ", ".join(f"{t} {'/'.join(str(web(src[('cold', t, p)])) for p in reps)}" for t in tasks))
warm = [r for (c, t, p), r in new.items() if c in FALLBACK]
if warm:
    print(f"\nmiss-0.8 reuse runs: {len(warm)}, correct {sum(r['correct'] for r in warm)}/{len(warm)}")

"""miss-0.8 (3-call card bar) against the iteration each task set last ran under.

  python out_miss-0.8/report.py

Head-0.1's two-call and three+ pages compare with its miss-0.7 runs, the 9 hard multi-fetch
tasks with miss-0.5's (reps 1-2 only, to match). Baselines are each set's own cold-nowrite
and cold-nowrite-related runs. Same definitions as out_head-0.1/report.py: runs averaged over
reps per task, each arm against the no-write run on the same question, "mean of per-task
changes / weighted change". A miss-0.8 cold run that stored nothing left an empty registry,
so its reuse runs are the baselines.
"""
import json, pathlib, statistics, sys

HERE = pathlib.Path(__file__).parent
EXP = HERE.parent
sys.path.insert(0, str(EXP))
from rescore import plan

MEASURES = {"tokens": lambda r: r["usage"]["total"],
            "uncached": lambda r: r["usage"]["total"] - r["usage"]["cache_read"],
            "dollars": lambda r: r["cost_usd"],
            "output": lambda r: r["usage"]["output"],
            "plan": lambda r: r["plan"]}
WEB = ("mcp__web__fetch", "mcp__web__render", "WebSearch")
FALLBACK = {"warm-same-nowrite": "cold-nowrite", "warm-related-nowrite": "cold-nowrite-related"}
REPS = (1, 2)


def load(d):
    out = {}
    for l in (d / "results.jsonl").read_text(encoding="utf-8").splitlines():
        if l.strip():
            r = json.loads(l)
            r["plan"] = plan(r, d)
            out[(r["condition"], r["task"], r["rep"])] = r  # latest row wins
    return out


new = load(HERE)
GROUPS = (("two calls", "miss-0.7", load(EXP / "out_head-0.1"),
           ["flask-config", "git-rebase", "k8s-probes", "mdn-set-cookie", "pandas-read-csv",
            "pg-connections", "pg-numeric", "py-argparse", "py-subprocess", "redis-set"]),
          ("three+ calls", "miss-0.7", load(EXP / "out_head-0.1"),
           ["cargo-manifest", "curl-manpage", "npm-package-json", "pytest-reference"]),
          ("hard multi-fetch", "miss-0.5", load(EXP / "out_miss-0.5"),
           ["bash-histsize", "gha-matrix-max-jobs", "git-gc-auto", "heroku-daily-restart", "mdn-fetch-credentials",
            "nginx-keepalive-requests", "render-free-spindown", "rust-vec-extract-if", "sonatype-guava"]))
ARMS = (("write", ["cold"], ["cold-nowrite"]), ("same", ["warm-same-nowrite"], ["cold-nowrite"]),
        ("related", ["warm-related-nowrite"], ["cold-nowrite-related"]),
        ("net", ["cold", "warm-related-nowrite"], ["cold-nowrite", "cold-nowrite-related"]))
web = lambda r: sum(v for k, v in r["tool_calls"].items() if k in WEB)
pct = lambda x: f"{100 * x:+.0f}%"


def get(old, use_new, cond, t, p):
    if use_new and cond == "cold":
        return new[(cond, t, p)]
    if use_new and cond in FALLBACK:
        return new[(cond, t, p)] if new[("cold", t, p)]["write_results"]["stored"] else old[(FALLBACK[cond], t, p)]
    return old[(cond, t, p)]


def change(old, tasks, use_new, arm, base, f):
    a = {t: statistics.mean(sum(f(get(old, use_new, c, t, p)) for c in arm) for p in REPS) for t in tasks}
    b = {t: statistics.mean(sum(f(old[(c, t, p)]) for c in base) for p in REPS) for t in tasks}
    return statistics.mean(a[t] / b[t] - 1 for t in tasks), sum(a.values()) / sum(b.values()) - 1


for name, old_it, old, tasks in GROUPS:
    if not all(("cold", t, p) in new for t in tasks for p in REPS):
        print(f"\n{name}: miss-0.8 runs not all done, skipped")
        continue
    print(f"\n{name} ({len(tasks)} tasks, reps {REPS[0]}-{REPS[-1]})")
    print(f"{'':18} " + " ".join(f"{l:>15}" for l, *_ in ARMS))
    for m, f in MEASURES.items():
        for label, use_new in ((old_it, False), ("miss-0.8", True)):
            print(f"{m + ' ' + label:18} " + " ".join(f"{pct(p) + ' / ' + pct(w):>15}"
                                                      for p, w in (change(old, tasks, use_new, a, b, f) for _, a, b in ARMS)))
    for label, use_new in ((old_it, False), ("miss-0.8", True)):
        cold = [get(old, use_new, "cold", t, p) for t in tasks for p in REPS]
        warm = [get(old, use_new, c, t, p) for c in FALLBACK for t in tasks for p in REPS]
        print(f"{label}: cold stored {sum(r['write_results']['stored'] > 0 for r in cold)}/{len(cold)}, "
              f"refused {sum(r['write_results']['not_stored'] + r['write_results']['rejected'] for r in cold)}, "
              f"correct cold {sum(r['correct'] for r in cold)}/{len(cold)}, reuse {sum(r['correct'] for r in warm)}/{len(warm)}")
        print("  cold web calls: " + ", ".join(f"{t} {'/'.join(str(web(get(old, use_new, 'cold', t, p))) for p in REPS)}"
                                               for t in tasks))

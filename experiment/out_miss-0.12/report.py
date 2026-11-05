"""Step 2: miss-0.13 (bar of 3 web calls) against miss-0.14 (miss-0.9's bar) on head-0.1's
two-call and three+ pages and the 9 hard multi-fetch tasks, against same-day baselines.

  python out_miss-0.12/report.py

Same definitions as out_miss-0.8/report.py: runs averaged over reps per task, each arm against
the no-write run on the same question, "mean of per-task changes / weighted change". Baselines
are this folder's cold-nowrite and cold-nowrite-related runs, made beside the cold runs (see
drive.py). A cold run that stored nothing left an empty registry, so its reuse runs are the
baselines. Net is a write plus one read-only related reuse. Records stored are counted from
each cold run's registry copy. Plan is dollars with sonnet's output weighted 1.6x (rescore.py).
"""
import json, pathlib, sqlite3, statistics, sys

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
DIRS = {"miss-0.13": EXP / "out_miss-0.13", "miss-0.14": EXP / "out_miss-0.14"}
GROUPS = {"two calls": ["flask-config", "git-rebase", "k8s-probes", "mdn-set-cookie", "pandas-read-csv",
                        "pg-connections", "pg-numeric", "py-argparse", "py-subprocess", "redis-set"],
          "three+ calls": ["cargo-manifest", "curl-manpage", "npm-package-json", "pytest-reference",
                           "apache-core", "haproxy-config", "linux-tcp7", "rsync-manpage", "sqlite-pragma",
                           "systemd-exec", "vim-options"],
          "hard multi-fetch": ["bash-histsize", "gha-matrix-max-jobs", "git-gc-auto", "heroku-daily-restart",
                               "mdn-fetch-credentials", "nginx-keepalive-requests", "render-free-spindown",
                               "rust-vec-extract-if", "sonatype-guava"]}
GROUPS["all"] = [t for ts in GROUPS.values() for t in ts]
# head-0.1's four three+ pages on their own, comparable with its results; the rest were added 2026-11-04.
GROUPS["three+, head-0.1's 4"] = GROUPS["three+ calls"][:4]
GROUPS["three+, added 11-04"] = GROUPS["three+ calls"][4:]
ARMS = (("write", ["cold"], ["cold-nowrite"]), ("same", ["warm-same-nowrite"], ["cold-nowrite"]),
        ("related", ["warm-related-nowrite"], ["cold-nowrite-related"]),
        ("net", ["cold", "warm-related-nowrite"], ["cold-nowrite", "cold-nowrite-related"]))
web = lambda r: sum(v for k, v in r["tool_calls"].items() if k in WEB)
pct = lambda x: f"{100 * x:+.0f}%"


def load(d):
    out = {}
    if (d / "results.jsonl").exists():
        for l in (d / "results.jsonl").read_text(encoding="utf-8").splitlines():
            if l.strip():
                r = json.loads(l)
                r["plan"] = plan(r, d)
                out[(r["condition"], r["task"], r["rep"])] = r  # latest row wins
    return out


def stored(d, t, p):
    """(site records, page cards) in the cold run's registry copy."""
    db = d / "runs" / "cold" / t / f"r{p}" / "registry.sqlite"
    if not db.exists():
        return 0, 0
    with sqlite3.connect(db) as c:
        try:
            return tuple(c.execute(f"SELECT COUNT(*) FROM {tb}").fetchone()[0] for tb in ("sites", "pages"))
        except sqlite3.OperationalError:
            return 0, 0


base = load(HERE)
runs = {it: load(d) for it, d in DIRS.items()}


def get(rows, cond, t, p):
    if cond in FALLBACK and not rows[("cold", t, p)]["write_results"]["stored"]:
        return base[(FALLBACK[cond], t, p)]
    return (base if cond in FALLBACK.values() else rows)[(cond, t, p)]


def change(rows, tasks, arm, against, f):
    a = {t: statistics.mean(sum(f(get(rows, c, t, p)) for c in arm) for p in REPS) for t in tasks}
    b = {t: statistics.mean(sum(f(base[(c, t, p)]) for c in against) for p in REPS) for t in tasks}
    return statistics.mean(a[t] / b[t] - 1 for t in tasks), sum(a.values()) / sum(b.values()) - 1


def done(rows, tasks):
    need = [(c, t, p) for c in FALLBACK.values() for t in tasks for p in REPS]
    return all(k in base for k in need) and all(("cold", t, p) in rows for t in tasks for p in REPS) and all(
        (c, t, p) in rows for c in FALLBACK for t in tasks for p in REPS if rows[("cold", t, p)]["write_results"]["stored"])


for name, tasks in GROUPS.items():
    its = [it for it, rows in runs.items() if done(rows, tasks)]
    if not its:
        print(f"\n{name}: runs not all done, skipped")
        continue
    print(f"\n{name} ({len(tasks)} tasks, reps {REPS[0]}-{REPS[-1]}), against same-day no-write")
    print(f"{'':19} " + " ".join(f"{l:>15}" for l, *_ in ARMS))
    for m, f in MEASURES.items():
        for it in its:
            print(f"{m + ' ' + it:19} " + " ".join(f"{pct(p) + ' / ' + pct(w):>15}"
                                                   for p, w in (change(runs[it], tasks, a, b, f) for _, a, b in ARMS)))
    for it in its:
        rows = runs[it]
        cold = [rows[("cold", t, p)] for t in tasks for p in REPS]
        warm = [get(rows, c, t, p) for c in FALLBACK for t in tasks for p in REPS]
        recs = [stored(DIRS[it], t, p) for t in tasks for p in REPS]
        print(f"{it}: sites {sum(s for s, _ in recs)}, cards {sum(c for _, c in recs)}, runs storing "
              f"{sum(r['write_results']['stored'] > 0 for r in cold)}/{len(cold)}, refused "
              f"{sum(r['write_results']['not_stored'] + r['write_results']['rejected'] for r in cold)}, correct cold "
              f"{sum(r['correct'] for r in cold)}/{len(cold)}, reuse {sum(r['correct'] for r in warm)}/{len(warm)}")
        if name != "all":
            print("  cold web calls: " + ", ".join(f"{t} {'/'.join(str(web(rows[('cold', t, p)])) for p in REPS)}"
                                                   for t in tasks))
    nw = [base[(c, t, p)] for c in FALLBACK.values() for t in tasks for p in REPS]
    print(f"no-write: web calls {statistics.mean(map(web, nw)):.2f}, correct {sum(r['correct'] for r in nw)}/{len(nw)}")

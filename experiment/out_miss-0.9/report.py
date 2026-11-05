"""miss-0.9+ (deferred page-card instructions) on head-0.1's one- and two-call pages, and the hard
set's one-fetch API tasks (against miss-0.5, the last policy run on them).

  python out_miss-0.9/report.py

Cold runs only, against head-0.1's cold-nowrite runs on the same question and rep, beside
miss-0.7 (head-0.1's cold runs) and, on two-call pages, miss-0.8. Same definitions as
out_miss-0.8/report.py: runs averaged over reps per task, "mean of per-task changes /
weighted change". Records stored are counted from each run's registry copy. An iteration
with its own no-write runs on a group also gets a row (marked *) against those.
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
REPS = (1, 2)
ONE_CALL = ["docker-run", "dockerfile", "gha-events", "go-net-http", "lambda-quotas", "node-child-process", "node-fs",
            "react-useeffect", "tsconfig", "vite-server"]
API = ["terraform-aws-provider", "galaxy-community-general", "artifacthub-cert-manager", "puppet-stdlib",
       "jetbrains-rainbow-brackets"]
TWO_CALLS = ["flask-config", "git-rebase", "k8s-probes", "mdn-set-cookie", "pandas-read-csv",
             "pg-connections", "pg-numeric", "py-argparse", "py-subprocess", "redis-set"]
DIRS = {"miss-0.7": EXP / "out_head-0.1", "miss-0.8": EXP / "out_miss-0.8",
        "miss-0.9": EXP / "out_miss-0.9", "miss-0.10": EXP / "out_miss-0.10", "miss-0.11": EXP / "out_miss-0.11",
        "miss-0.5": EXP / "out_miss-0.5"}
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


runs = {it: load(d) for it, d in DIRS.items()}
for group, tasks, base in (("one call", ONE_CALL, runs["miss-0.7"]), ("two calls", TWO_CALLS, runs["miss-0.7"]),
                           ("one-fetch API", API, runs["miss-0.5"])):
    print(f"\n{group} ({len(tasks)} pages, reps {REPS[0]}-{REPS[-1]}), cold against no-write")
    print(f"{'':10}" + "".join(f"{m:>15}" for m in MEASURES) + f"{'web calls':>11}{'sites':>7}{'cards':>7}{'correct':>9}")
    # an iteration that ran its own no-write runs on the group is also shown against those
    lines = [(it, rows, base) for it, rows in runs.items()] +             [(it + "*", rows, rows) for it, rows in runs.items() if rows is not base
             and all(("cold-nowrite", t, p) in rows for t in tasks for p in REPS)]
    for it, rows, b0 in lines:
        if not all(("cold", t, p) in rows for t in tasks for p in REPS):
            continue
        cells = []
        for f in MEASURES.values():
            a = {t: statistics.mean(f(rows[("cold", t, p)]) for p in REPS) for t in tasks}
            b = {t: statistics.mean(f(b0[("cold-nowrite", t, p)]) for p in REPS) for t in tasks}
            m, w = statistics.mean(a[t] / b[t] - 1 for t in tasks), sum(a.values()) / sum(b.values()) - 1
            cells.append(f"{pct(m)} / {pct(w)}")
        cold = [rows[("cold", t, p)] for t in tasks for p in REPS]
        recs = [stored(DIRS[it.rstrip("*")], t, p) for t in tasks for p in REPS]
        print(f"{it:10}" + "".join(f"{c:>15}" for c in cells)
              + f"{statistics.mean(map(web, cold)):>11.2f}{sum(s for s, _ in recs):>7}{sum(c for _, c in recs):>7}"
              + f"{sum(r['correct'] for r in cold):>6}/{len(cold)}")
    nw = [base[("cold-nowrite", t, p)] for t in tasks for p in REPS]
    print(f"{'no-write':10}{'':60}{statistics.mean(map(web, nw)):>11.2f}")
print("\n* against the iteration's own same-day no-write runs")

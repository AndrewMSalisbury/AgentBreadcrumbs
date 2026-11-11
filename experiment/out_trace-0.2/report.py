"""trace-0.2 (drive.py): three kinds of trace registry, each against same-day no-write runs.

  python out_trace-0.2/report.py

  v1         step 2's trace card (trace-0.1), built from the cold-nowrite run
  v2         the same card without the start offset, built from the cold-nowrite run
  trace-0.2  the cold run under trace-0.2 (agents write site records only) and its registry: any
             site record it wrote, plus a v2 card built from its own trace
v1 and v2 cost nothing to write (a registry that serves fetch builds them); trace-0.2's write is
its cold run against cold-nowrite. Same definitions as out_miss-0.12/report.py: runs averaged over
reps per task, "mean of per-task changes / weighted change", break-even in related reuses.
The weighted change follows a few expensive runs, so each group also prints the median per-task
change on related reuse. Last, the v1 and v2 cards that came out identical give two reuse runs of
one card each: the run-to-run spread on the same card.
"""
import json, pathlib, sqlite3, statistics, sys

HERE = pathlib.Path(__file__).parent
EXP = HERE.parent
sys.path.insert(0, str(EXP))
from rescore import plan

MEASURES = {"dollars": lambda r: r["cost_usd"], "plan": lambda r: r["plan"],
            "tokens": lambda r: r["usage"]["total"], "output": lambda r: r["usage"]["output"]}
WEB = ("mcp__web__fetch", "mcp__web__render", "WebSearch")
DIRS = {"base": HERE, "v1": HERE / "v1", "v2": HERE / "v2"}
GROUPS = {"two calls": ["flask-config", "git-rebase", "k8s-probes", "mdn-set-cookie", "pandas-read-csv",
                        "pg-connections", "pg-numeric", "py-argparse", "py-subprocess", "redis-set"],
          "three+ calls": ["cargo-manifest", "curl-manpage", "npm-package-json", "pytest-reference", "apache-core",
                           "haproxy-config", "linux-tcp7", "rsync-manpage", "sqlite-pragma", "systemd-exec",
                           "vim-options"],
          "hard multi-fetch": ["bash-histsize", "gha-matrix-max-jobs", "git-gc-auto", "heroku-daily-restart",
                               "mdn-fetch-credentials", "nginx-keepalive-requests", "render-free-spindown",
                               "rust-vec-extract-if", "sonatype-guava"]}
GROUPS["all"] = [t for ts in GROUPS.values() for t in ts]
ARMS = ("v1", "v2", "trace-0.2")
REPS = (1, 2)
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


rows = {k: load(v) for k, v in DIRS.items()}
B = rows["base"]


def pair(arm, t, p):
    """(write-side run, related reuse run); a registry with nothing in it reuses as the baseline."""
    where = "base" if arm == "trace-0.2" else arm
    reuse = rows[where].get(("warm-related-nowrite", t, p)) or B[("cold-nowrite-related", t, p)]
    return (B[("cold", t, p)] if arm == "trace-0.2" else B[("cold-nowrite", t, p)]), reuse


def sites(t, p):
    """(site records, those with a {placeholder} URL pattern) the trace-0.2 cold agent wrote."""
    db = DIRS["base"] / "runs" / "cold" / t / f"r{p}" / "registry.agent.sqlite"
    if not db.exists():
        return 0, 0
    with sqlite3.connect(db) as c:
        recs = [r for (r,) in c.execute("SELECT record FROM sites")]
    return len(recs), sum("{" in json.dumps(json.loads(r).get("access", {})) for r in recs)


def ready(t):
    need = [("cold-nowrite", t, p) for p in REPS] + [("cold-nowrite-related", t, p) for p in REPS] + \
           [("cold", t, p) for p in REPS]
    return all(k in B for k in need)


def chg(s, pick):
    a = {t: pick(*v)[0] for t, v in s.items()}
    b = {t: pick(*v)[1] for t, v in s.items()}
    return statistics.mean(a[t] / b[t] - 1 for t in s), sum(a.values()) / sum(b.values()) - 1


def sums(arm, tasks, f):
    out = {}
    for t in tasks:
        w = [pair(arm, t, p) for p in REPS]
        out[t] = (statistics.mean(f(a) for a, _ in w), statistics.mean(f(b) for _, b in w),
                  statistics.mean(f(B[("cold-nowrite", t, p)]) for p in REPS),
                  statistics.mean(f(B[("cold-nowrite-related", t, p)]) for p in REPS))
    return out


def table(name, tasks):
    print(f"\n{name} ({len(tasks)} tasks, reps {REPS[0]}-{REPS[-1]}), against same-day no-write")
    print(f"{'':20}{'write':>15}{'related':>15}{'1 reuse':>15}{'10 reuses':>15}{'break-even':>12}")
    for m, f in MEASURES.items():
        for arm in ARMS:
            s = sums(arm, tasks, f)
            cols = [chg(s, lambda a, b, a0, b0: (a, a0)), chg(s, lambda a, b, a0, b0: (b, b0)),
                    chg(s, lambda a, b, a0, b0: (a + b, a0 + b0)),
                    chg(s, lambda a, b, a0, b0: (a + 10 * b, a0 + 10 * b0))]
            extra = sum(v[0] - v[2] for v in s.values())
            save = sum(v[3] - v[1] for v in s.values())
            be = "none" if extra <= 0 else f"{extra / save:.1f}" if save > 0 else "never"
            print(f"{m + ' ' + arm:20}" + "".join(f"{pct(x) + ' / ' + pct(y):>15}" for x, y in cols) + f"{be:>12}")
    f = MEASURES["dollars"]
    b0 = {t: statistics.mean(f(B[("cold-nowrite-related", t, p)]) for p in REPS) for t in tasks}
    med = lambda a: statistics.median(statistics.mean(f(pair(a, t, p)[1]) for p in REPS) / b0[t] - 1 for t in tasks)
    print("related $, median per-task change: " + " / ".join(f"{a} {pct(med(a))}" for a in ARMS))
    st = [sites(t, p) for t in tasks for p in REPS]
    print(f"trace-0.2 site records: {sum(n for n, _ in st)} in {sum(n > 0 for n, _ in st)}/{len(st)} cold runs, "
          f"{sum(k for _, k in st)} with a URL pattern")
    if name != "all":
        f = MEASURES["dollars"]
        print("  related $ per task (" + " / ".join(ARMS) + "), web calls no-write -> " + " / ".join(ARMS) + ":")
        for t in tasks:
            b = statistics.mean(f(B[("cold-nowrite-related", t, p)]) for p in REPS)
            ch = [statistics.mean(f(pair(a, t, p)[1]) for p in REPS) / b - 1 for a in ARMS]
            calls = [("/".join(str(web(pair(a, t, p)[1])) for p in REPS)) for a in ARMS]
            nwc = "/".join(str(web(B[("cold-nowrite-related", t, p)])) for p in REPS)
            n, k = map(sum, zip(*(sites(t, p) for p in REPS)))
            print(f"    {t:26} " + " ".join(f"{pct(x):>6}" for x in ch) + f"   {nwc} -> {' / '.join(calls)}"
                  + (f"   sites {n} ({k} patterned)" if n else ""))
    warm = [r for k in DIRS for (c, t, p), r in rows[k].items() if c == "warm-related-nowrite" and t in tasks]
    cold = [B[("cold", t, p)] for t in tasks for p in REPS]
    nw = [B[(c, t, p)] for c in ("cold-nowrite", "cold-nowrite-related") for t in tasks for p in REPS]
    print(f"correct: cold {sum(r['correct'] for r in cold)}/{len(cold)}, reuse {sum(r['correct'] for r in warm)}/"
          f"{len(warm)}, no-write {sum(r['correct'] for r in nw)}/{len(nw)}")


for name, tasks in GROUPS.items():
    done = [t for t in tasks if ready(t)]
    if len(done) < len(tasks):
        print(f"\n{name}: {len(tasks) - len(done)} of {len(tasks)} tasks not done: "
              f"{', '.join(t for t in tasks if t not in done)}")
    if done:
        table(name, done)


def records(w, t, p):
    with sqlite3.connect(DIRS[w] / "runs" / "cold" / t / f"r{p}" / "registry.sqlite") as c:
        return sorted(r for tb in ("pages", "sites") for (r,) in c.execute(f"SELECT record FROM {tb}"))


f = MEASURES["dollars"]
both = [(t, p) for t in GROUPS["all"] for p in REPS if all(("warm-related-nowrite", t, p) in rows[w] for w in ("v1", "v2"))]
same = sorted(((f(rows["v1"][("warm-related-nowrite", t, p)]), f(rows["v2"][("warm-related-nowrite", t, p)]), t, p)
               for t, p in both if records("v1", t, p) == records("v2", t, p)), key=lambda x: -abs(x[1] - x[0]))
if same:
    gap = lambda s: sum(b for _, b, _, _ in s) / sum(a for a, _, _, _ in s) - 1
    a, b, t, p = same[0]
    print(f"\nidentical v1 and v2 cards: {len(same)} of {len(both)} pairs, related $ v1 {sum(x[0] for x in same):.2f}"
          f" / v2 {sum(x[1] for x in same):.2f} ({pct(gap(same))}); median pair differs "
          f"{statistics.median(abs(y - x) / ((x + y) / 2) for x, y, _, _ in same):.0%}")
    print(f"  largest: {t} r{p} ${a:.3f} / ${b:.3f}; without it {pct(gap(same[1:]))}, without the top 3 {pct(gap(same[3:]))}")

"""Step 2, paired (drive.py): bar 2 (miss-0.14 as run), bar 3 (read off the same runs, bar3.py)
and trace cards (out_trace-0.1), each against same-day no-write runs.

  python out_miss-0.12/report.py

Per task and rep, each policy has a write-side run and a related reuse run:
  bar 2   miss-0.14's cold run; warm-related-nowrite on its registry, or the cold-nowrite-related
          run if it stored nothing (an empty registry)
  bar 3   the same where bar3.py says same or ran on; where it says refused, cold-nowrite (or the
          cold run itself, if it also stored a site record) and the stripped registry's reuse (or
          cold-nowrite-related)
  trace   cold-nowrite, since a registry that serves fetch builds the card with no agent writing;
          warm-related-nowrite on the card built from that run
Runs are averaged over a task's reps, then "mean of per-task changes / weighted change". Break-even
is the number of related reuses after which a policy's write cost is paid back (weighted), and
"n reuses" is write plus n related reuses against the no-write pair. Plan is dollars with sonnet's
output weighted 1.6x (rescore.py).
"""
import json, pathlib, statistics, sys

HERE = pathlib.Path(__file__).parent
EXP = HERE.parent
sys.path.insert(0, str(EXP))
sys.path.append(str(HERE))  # after EXP: rescore imports EXP's report.py
from rescore import plan
from bar3 import classify

MEASURES = {"dollars": lambda r: r["cost_usd"], "plan": lambda r: r["plan"],
            "tokens": lambda r: r["usage"]["total"], "output": lambda r: r["usage"]["output"]}
WEB = ("mcp__web__fetch", "mcp__web__render", "WebSearch")
DIRS = {"base": HERE, "card": EXP / "out_miss-0.14", "bar3": EXP / "out_miss-0.14_bar3",
        "trace": EXP / "out_trace-0.1", "api": EXP / "out_miss-0.13"}
GROUPS = {"two calls": ["flask-config", "git-rebase", "k8s-probes", "mdn-set-cookie", "pandas-read-csv",
                        "pg-connections", "pg-numeric", "py-argparse", "py-subprocess", "redis-set"],
          "three+ calls": ["cargo-manifest", "curl-manpage", "npm-package-json", "pytest-reference",
                           "apache-core", "haproxy-config", "linux-tcp7", "rsync-manpage", "sqlite-pragma",
                           "systemd-exec", "vim-options"],
          "hard multi-fetch": ["bash-histsize", "gha-matrix-max-jobs", "git-gc-auto", "heroku-daily-restart",
                               "mdn-fetch-credentials", "nginx-keepalive-requests", "render-free-spindown",
                               "rust-vec-extract-if", "sonatype-guava"]}
GROUPS["all"] = [t for ts in GROUPS.values() for t in ts]
API = ["terraform-aws-provider", "galaxy-community-general", "artifacthub-cert-manager", "puppet-stdlib",
       "jetbrains-rainbow-brackets"]
POLICIES = ("bar 2", "bar 3", "trace")
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


def cls(t, p):
    return classify(DIRS["card"] / "runs" / "cold" / t / f"r{p}")


def pair(policy, t, p):
    """(write-side run, related reuse run) for one task and rep."""
    cold = rows["card"][("cold", t, p)]
    stored = cold["write_results"]["stored"]
    reuse = rows["card"][("warm-related-nowrite", t, p)] if stored else B[("cold-nowrite-related", t, p)]
    if policy == "bar 2":
        return cold, reuse
    if policy == "bar 3":
        c = cls(t, p)
        if c["bar3"] != "refused":
            return cold, reuse
        if c["sites"]:
            return cold, rows["bar3"][("warm-related-nowrite", t, p)]
        return B[("cold-nowrite", t, p)], B[("cold-nowrite-related", t, p)]
    tr = rows["trace"].get(("warm-related-nowrite", t, p))
    return B[("cold-nowrite", t, p)], tr or B[("cold-nowrite-related", t, p)]


def reps(t):
    return [p for p in (1, 2, 3) if ("cold-nowrite", t, p) in B and ("cold-nowrite-related", t, p) in B
            and ("cold", t, p) in rows["card"]]


def ready(t):
    try:
        return bool(reps(t)) and all(pair(pol, t, p) for pol in POLICIES for p in reps(t))
    except KeyError:
        return False


def sums(policy, tasks, f, n=1, only=None):
    """Per task: (write, n reuses) for the policy and for the no-write pair, averaged over reps."""
    out = {}
    for t in tasks:
        ps = [p for p in reps(t) if only is None or only(t, p)]
        if not ps:
            continue
        w = [pair(policy, t, p) for p in ps]
        out[t] = (statistics.mean(f(a) for a, _ in w), statistics.mean(f(b) for _, b in w),
                  statistics.mean(f(B[("cold-nowrite", t, p)]) for p in ps),
                  statistics.mean(f(B[("cold-nowrite-related", t, p)]) for p in ps))
    return out


def chg(s, pick):
    a = {t: pick(*v)[0] for t, v in s.items()}
    b = {t: pick(*v)[1] for t, v in s.items()}
    return statistics.mean(a[t] / b[t] - 1 for t in s), sum(a.values()) / sum(b.values()) - 1


def table(name, tasks):
    print(f"\n{name} ({len(tasks)} tasks, reps {'/'.join(str(len(reps(t))) for t in tasks)}), against same-day no-write")
    print(f"{'':16}{'write':>15}{'related':>15}{'1 reuse':>15}{'10 reuses':>15}{'break-even':>12}")
    for m, f in MEASURES.items():
        for pol in POLICIES:
            s = sums(pol, tasks, f)
            w, r = chg(s, lambda a, b, a0, b0: (a, a0)), chg(s, lambda a, b, a0, b0: (b, b0))
            n1, n10 = chg(s, lambda a, b, a0, b0: (a + b, a0 + b0)), chg(s, lambda a, b, a0, b0: (a + 10 * b, a0 + 10 * b0))
            extra = sum(v[0] - v[2] for v in s.values())
            save = sum(v[3] - v[1] for v in s.values())
            be = "none" if extra <= 0 else f"{extra / save:.1f}" if save > 0 else "never"
            print(f"{m + ' ' + pol:16}" + "".join(f"{pct(x) + ' / ' + pct(y):>15}" for x, y in (w, r, n1, n10))
                  + f"{be:>12}")
    # trace against agent-written cards, on the runs where miss-0.14 stored a page card
    carded = lambda t, p: rows["card"][("cold", t, p)]["write_results"]["stored"] and cls(t, p)["pages"]
    if any(carded(t, p) for t in tasks for p in reps(t)):
        f = MEASURES["dollars"]
        c = chg(sums("bar 2", tasks, f, only=carded), lambda a, b, a0, b0: (b, b0))
        tr = chg(sums("trace", tasks, f, only=carded), lambda a, b, a0, b0: (b, b0))
        print(f"related $, runs whose cold run stored a page card: agent card {pct(c[0])} / {pct(c[1])}, "
              f"trace card {pct(tr[0])} / {pct(tr[1])}")
    k = [cls(t, p) for t in tasks for p in reps(t)]
    print("bar 3: " + ", ".join(f"{s} {sum(x['bar3'] == s and x['pages'] > 0 for x in k)}" for s in ("same", "ran on", "refused"))
          + f" of {sum(x['pages'] > 0 for x in k)} page cards; site records {sum(x['sites'] for x in k)}; "
          f"cold runs {len(k)}")
    if name != "all":
        print("  cold web calls (bar3 class): " + ", ".join(
            f"{t} " + "/".join(f"{x['calls']}{'*' if x['bar3'] == 'refused' and x['pages'] else ''}"
                               for x in (cls(t, p) for p in reps(t))) for t in tasks) + "   (* refused under bar 3)")
    warm = [r for (c, t, p), r in list(rows["card"].items()) + list(rows["trace"].items()) + list(rows["bar3"].items())
            if c == "warm-related-nowrite" and t in tasks]
    cold = [rows["card"][("cold", t, p)] for t in tasks for p in reps(t)]
    nw = [B[(c, t, p)] for c in ("cold-nowrite", "cold-nowrite-related") for t in tasks for p in reps(t)]
    print(f"correct: cold {sum(r['correct'] for r in cold)}/{len(cold)}, reuse {sum(r['correct'] for r in warm)}/"
          f"{len(warm)}, no-write {sum(r['correct'] for r in nw)}/{len(nw)}; no-write web calls "
          f"{statistics.mean(map(web, nw)):.2f}")
    nr = [t for t in tasks if ("noregistry-related", t, 1) in B and ("cold-nowrite-related", t, 1) in B]
    if nr:
        a = {t: B[("cold-nowrite-related", t, 1)]["cost_usd"] for t in nr}
        b = {t: B[("noregistry-related", t, 1)]["cost_usd"] for t in nr}
        print(f"lookup itself, related rep 1, dollars: cold-nowrite-related vs noregistry-related "
              f"{pct(statistics.mean(a[t] / b[t] - 1 for t in nr))} / {pct(sum(a.values()) / sum(b.values()) - 1)}")


for name, tasks in GROUPS.items():
    done = [t for t in tasks if ready(t)]
    if len(done) < len(tasks):
        print(f"\n{name}: {len(tasks) - len(done)} of {len(tasks)} tasks not done: {', '.join(t for t in tasks if t not in done)}")
    if done:
        table(name, done)

A = rows["api"]
api = [(t, p) for t in API for p in (1, 2) if ("warm-related-nowrite", t, p) in A and ("cold-nowrite-related", t, p) in A]
if api:
    print(f"\nAPI site records (miss-0.13's 5 one-fetch API tasks, {len(api)} task-reps), related, read-only, "
          "against same-day cold-nowrite-related")
    for m, f in MEASURES.items():
        per = {}
        for t, p in api:
            per.setdefault(t, []).append((f(A[("warm-related-nowrite", t, p)]), f(A[("cold-nowrite-related", t, p)])))
        a = {t: statistics.mean(x for x, _ in v) for t, v in per.items()}
        b = {t: statistics.mean(y for _, y in v) for t, v in per.items()}
        print(f"  {m:8} {pct(statistics.mean(a[t] / b[t] - 1 for t in a))} / {pct(sum(a.values()) / sum(b.values()) - 1)}  "
              + ", ".join(f"{t} {pct(a[t] / b[t] - 1)}" for t in a))
    w = [A[("warm-related-nowrite", t, p)] for t, p in api]
    print(f"  correct {sum(r['correct'] for r in w)}/{len(w)}")

"""head-0.1 replayed offline under a 3-web-call card bar (no new runs).

  python out_head-0.1/bar3.py

A cold run with fewer than BAR web calls (fetch, render, search; searches count as in
miss-0.7) would have been refused its card. For such a run:
  - cold: its cost is replaced by cold-nowrite on the same task and rep, scaled by the
    write prompt's fixed cost, measured on the one-call pages (where no cold run stored
    anything) as cold / cold-nowrite per measure, weighted.
  - warm-same-nowrite / warm-related-nowrite of that rep start from an empty registry,
    which is exactly cold-nowrite / cold-nowrite-related, so those runs are used.
Cold runs at or over the bar, and their reuse runs, are kept as measured. Output is the
report.py table, actual vs replayed, for the dollars and tokens measures.
"""
import collections, json, pathlib, statistics, sys

HERE = pathlib.Path(__file__).parent
BAR = int(sys.argv[1]) if len(sys.argv) > 1 else 3
WEB = ("mcp__web__fetch", "mcp__web__render", "WebSearch")
MEASURES = {"tokens": lambda r: r["usage"]["total"], "dollars": lambda r: r["cost_usd"]}
SINGLE = (("write", "cold", "cold-nowrite"), ("same", "warm-same-nowrite", "cold-nowrite"),
          ("related", "warm-related-nowrite", "cold-nowrite-related"))
FALLBACK = {"warm-same-nowrite": "cold-nowrite", "warm-related-nowrite": "cold-nowrite-related"}

rows = [json.loads(l) for l in (HERE / "results.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
run = {(r["condition"], r["task"], r["rep"]): r for r in rows}
tasks = sorted({r["task"] for r in rows})
reps = sorted({r["rep"] for r in rows})
web = lambda r: sum(v for k, v in r["tool_calls"].items() if k in WEB)

base_calls = {t: statistics.mean(web(run[(c, t, p)]) for c in ("cold-nowrite", "cold-nowrite-related") for p in reps)
              for t in tasks}
groups = {"all": tasks,
          "one call": [t for t in tasks if base_calls[t] <= 1.25],
          "two calls": [t for t in tasks if 1.25 < base_calls[t] < 3],
          "three+ calls": [t for t in tasks if base_calls[t] >= 3]}
refused = {(t, p) for t in tasks for p in reps
           if run[("cold", t, p)]["write_results"]["stored"] and web(run[("cold", t, p)]) < BAR}
fixed = {m: sum(f(run[("cold", t, p)]) for t in groups["one call"] for p in reps)
         / sum(f(run[("cold-nowrite", t, p)]) for t in groups["one call"] for p in reps) for m, f in MEASURES.items()}


def cost(cond, t, p, m, replay):
    f = MEASURES[m]
    if replay and (t, p) in refused:
        if cond == "cold":
            return f(run[("cold-nowrite", t, p)]) * fixed[m]
        if cond in FALLBACK:
            return f(run[(FALLBACK[cond], t, p)])
    return f(run[(cond, t, p)])


def change(ts, arm, base, m, replay):
    a = {t: statistics.mean(sum(cost(c, t, p, m, replay) for c in arm) for p in reps) for t in ts}
    b = {t: statistics.mean(sum(cost(c, t, p, m, False) for c in base) for p in reps) for t in ts}
    return statistics.mean(a[t] / b[t] - 1 for t in ts), sum(a.values()) / sum(b.values()) - 1


pct = lambda x: f"{100 * x:+.0f}%"
print(f"bar {BAR}: refuses {len(refused)} of {sum(run[('cold', t, p)]['write_results']['stored'] > 0 for t in tasks for p in reps)} "
      f"stored cold runs; write fixed cost " + ", ".join(f"{m} {pct(v - 1)}" for m, v in fixed.items()))
for g, ts in groups.items():
    n = sum((t, p) in refused for t in ts for p in reps)
    print(f"\n{g} ({len(ts)} pages, {n} cold runs refused)")
    print(f"{'':16} " + " ".join(f"{l:>15}" for l, *_ in SINGLE) + f" {'net':>15}")
    for m in MEASURES:
        for label, replay in (("actual", False), (f"bar {BAR}", True)):
            cells = [change(ts, [a], [b], m, replay) for _, a, b in SINGLE]
            cells.append(change(ts, ["cold", "warm-related-nowrite"], ["cold-nowrite", "cold-nowrite-related"], m, replay))
            print(f"{m + ' ' + label:16} " + " ".join(f"{pct(p) + ' / ' + pct(w):>15}" for p, w in cells))
print("\nrefused: " + ", ".join(f"{t} r{p} ({web(run[('cold', t, p)])})" for t, p in sorted(refused)))

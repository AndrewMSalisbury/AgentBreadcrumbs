"""Headline comparisons for every iteration, in several measures of cost.

  python rescore.py [--md out_rescore.md]

Total tokens count cache reads at full weight, so extra turns over a cached context (a
write) look far dearer than the API bills them. Which measure a user feels depends on how
they pay: API users pay dollars, and subscription plans meter usage by a formula that
isn't published. So this reports each result in every measure we have, to show which
conclusions depend on the choice:
  tokens    every token Claude Code reports, cache reads included
  uncached  tokens minus cache reads (fresh input, cache writes and output)
  dollars   cost_usd, at API prices
  output    output tokens
  plan      dollars with sonnet's output weighted 1.6x: how a Pro plan's meter counts it
            (out_meter-0.1). Sonnet's output is read from the run's stream.jsonl; Haiku's
            (WebSearch) isn't weighted, since the meter was only measured on sonnet
  peak      largest single-call context (input + cache write + cache read), read from
            the run's stream.jsonl: how full the context window gets
Rows and arms are as in report.py: latest row per (condition, task, rep), averaged over
reps per task, each arm against the no-write run on the same question. Each cell is
"mean of per-task changes / weighted change" (weighted = sum over tasks of the arm / sum
of the baseline - 1). Negative is cheaper. Net is a write plus one related reuse,
(cold + warm) vs (cold-nowrite + cold-nowrite-related); read-only net uses
warm-related-nowrite as the reuse. Net isn't given for peak, since peaks don't add.
"""
import argparse, json, pathlib, statistics, sys
from report import load, MULTI_FETCH

ROOT = pathlib.Path(__file__).parent
# Main runs only: smoke tests, sitecheck and pre-metric folders are left out, and the
# probe pairs have their own report (out_miss-0.7_probe/report.py).
DIRS = ("narrow-0.1", "map-0.1", "route-0.1", "lean-0.1", "lean-0.2", "coldonly-0.1", "enforced-0.1",
        "enforced-0.2", "miss-0.1", "miss-0.2", "miss-0.3", "miss-0.4", "miss-0.5")
# (label, arm, baseline): single-run comparisons, then nets over one reuse.
SINGLE = (("write", "cold", "cold-nowrite"), ("same", "warm-same", "cold-nowrite"),
          ("related", "warm-related", "cold-nowrite-related"),
          ("same, read-only", "warm-same-nowrite", "cold-nowrite"),
          ("related, read-only", "warm-related-nowrite", "cold-nowrite-related"))
NET = (("net", "warm-related"), ("net, read-only", "warm-related-nowrite"))
LABELS = [l for l, *_ in SINGLE] + [l for l, _ in NET]
SUMMARY = ("net", "related")  # columns of the summary table, hard/multi-fetch, weighted
# out_meter-0.1: sonnet output at $10/M, metered at about 1.6x its dollar price relative to
# cache writes and reads.
SONNET_OUTPUT = 10e-6
PLAN_OUTPUT = 1.6


def stream(r: dict, home: pathlib.Path) -> list[str] | None:
    """The run's stream.jsonl lines, or None if it can't be found. Copied baseline rows live
    under their own iteration's folder; result.json must match the row."""
    for d in (home, ROOT / f"out_{r.get('iteration')}"):
        run = d / "runs" / r["condition"] / r["task"] / f"r{r['rep']}"
        try:
            if json.loads((run / "result.json").read_text(encoding="utf-8"))["usage"]["total"] != r["usage"]["total"]:
                continue
            return (run / "stream.jsonl").read_text(encoding="utf-8").splitlines()
        except (OSError, ValueError, KeyError):
            continue
    return None


def plan(r: dict, home: pathlib.Path):
    """Dollars with sonnet's output weighted PLAN_OUTPUT, or None without a cost. Without a
    stream, all output is taken as sonnet's."""
    if r.get("cost_usd") is None:
        return None
    out = r["usage"]["output"]
    for line in reversed(stream(r, home) or []):
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        if ev.get("type") == "result":
            out = sum(m.get("outputTokens", 0) for k, m in ev.get("modelUsage", {}).items() if "sonnet" in k)
            break
    return r["cost_usd"] + (PLAN_OUTPUT - 1) * SONNET_OUTPUT * out


def peak(r: dict, home: pathlib.Path):
    """Largest single-call context in the run, or None if its stream can't be found."""
    lines = stream(r, home)
    if lines is not None:
        best = 0
        for line in lines:
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            u = ev.get("message", {}).get("usage") if ev.get("type") == "assistant" else None
            if u:
                best = max(best, u.get("input_tokens", 0) + u.get("cache_creation_input_tokens", 0)
                           + u.get("cache_read_input_tokens", 0))
        return best or None
    return None


def metrics(home: pathlib.Path) -> dict:
    return {"tokens": lambda r: r["usage"]["total"],
            "uncached": lambda r: r["usage"]["total"] - r["usage"]["cache_read"],
            "dollars": lambda r: r.get("cost_usd"),
            "output": lambda r: r["usage"]["output"],
            "plan": lambda r: plan(r, home),
            "peak": lambda r: peak(r, home)}


def per_task(data: dict, metric) -> dict:
    """{condition: {task: mean metric over reps}}, skipping rows without the metric."""
    out = {}
    for cond, tasks in data.items():
        for t, rows in tasks.items():
            vals = [v for v in map(metric, rows) if v is not None]
            if vals:
                out.setdefault(cond, {})[t] = statistics.mean(vals)
    return out


def change(pairs: list) -> tuple | None:
    if not pairs:
        return None
    return (statistics.mean(a / b - 1 for a, b in pairs),
            sum(a for a, _ in pairs) / sum(b for _, b in pairs) - 1)


def score(v: dict, tasks: list, nets: bool) -> dict:
    out = {}
    for label, arm, base in SINGLE:
        out[label] = change([(v[arm][t], v[base][t]) for t in tasks if t in v.get(arm, {}) and t in v.get(base, {})])
    for label, arm in NET:
        conds = ("cold", arm, "cold-nowrite", "cold-nowrite-related")
        ts = [t for t in tasks if all(t in v.get(c, {}) for c in conds)] if nets else []
        out[label] = change([(v["cold"][t] + v[arm][t], v["cold-nowrite"][t] + v["cold-nowrite-related"][t])
                             for t in ts])
    return out


def cell(c) -> str:
    return "-" if c is None else f"{c[0]:+.0%} / {c[1]:+.0%}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--md", help="also write the tables to this Markdown file")
    a = ap.parse_args()
    out, summary = [], []
    for name in DIRS:
        home = ROOT / f"out_{name}"
        if not (home / "results.jsonl").exists():
            continue
        data = load(home / "results.jsonl")
        # Fetches and searches per no-write related run, as report.py counts them, for the multi-fetch group.
        calls = lambda r: sum(n for k, n in r["tool_calls"].items() if k.endswith(("__fetch", "__render", "WebSearch")))
        nwr = {t: statistics.mean(map(calls, rs)) for t, rs in data.get("cold-nowrite-related", {}).items()}
        sets = {t: (rs[0].get("set") or "easy") for t, rs in data.get("cold", {}).items()}
        groups = {"all": list(sets)}
        for st in sorted(set(sets.values())):
            groups[st] = [t for t in sets if sets[t] == st]
            multi = [t for t in groups[st] if nwr.get(t, 0) >= MULTI_FETCH]
            if multi:
                groups[f"{st}/multi-fetch"] = multi
        ms = metrics(home)
        vals = {m: per_task(data, f) for m, f in ms.items()}
        scores = {g: {m: score(vals[m], ts, nets=m != "peak") for m in ms} for g, ts in groups.items()}
        out.append(f"## {name}\n")
        for g, ts in groups.items():
            out.append(f"**{g}** ({len(ts)} tasks)\n\n| Measure | " + " | ".join(LABELS) + " |\n|"
                       + "---|" * (len(LABELS) + 1))
            out += [f"| {m} | " + " | ".join(cell(scores[g][m][l]) for l in LABELS) + " |" for m in ms]
            out.append("")
        if "hard/multi-fetch" in scores:
            s = scores["hard/multi-fetch"]
            summary.append(f"| {name} | {len(groups['hard/multi-fetch'])} | "
                           + " | ".join(" | ".join("-" if s[m][l] is None else f"{s[m][l][1]:+.0%}" for m in ms
                                                   if not (m == "peak" and l.startswith("net")))
                                        for l in SUMMARY) + " |")
    ms = list(metrics(ROOT))
    head = [f"{l}: {m}" for l in SUMMARY for m in ms if not (m == "peak" and l.startswith("net"))]
    text = ("Hard multi-fetch tasks, weighted change. Negative is cheaper.\n\n| Iteration | Tasks | "
            + " | ".join(head) + " |\n|" + "---|" * (len(head) + 2) + "\n" + "\n".join(summary)
            + "\n\nPer iteration, every group: each cell is mean per-task change / weighted change.\n\n"
            + "\n".join(out))
    sys.stdout.reconfigure(encoding="utf-8")
    print(text)
    if a.md:
        pathlib.Path(a.md).write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()

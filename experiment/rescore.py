"""Headline comparisons for every iteration, in total tokens and in dollars (cost_usd).

  python rescore.py [--md rescore.md]

miss-0.7 found that total tokens count cache reads at full weight, so extra turns over a
cached context (a write) look far dearer than they are billed. This puts each
iteration's results side by side in both metrics. Rows and arms are as in report.py:
latest row per (condition, task, rep), averaged over reps per task, each arm against the
no-write run on the same question. Each cell is "mean of per-task changes / weighted
change" (weighted = sum over tasks of the arm / sum of the baseline - 1). Negative is
cheaper. Net is a write plus one related reuse, (cold + warm) vs (cold-nowrite +
cold-nowrite-related); read-only net uses warm-related-nowrite as the reuse.
"""
import argparse, pathlib, statistics, sys
from report import load, MULTI_FETCH

ROOT = pathlib.Path(__file__).parent
# Main runs only: smoke tests, sitecheck and pre-metric folders are left out, and the
# probe pairs have their own report (out_miss-0.7_probe/report.py).
DIRS = ("map-0.1", "route-0.1", "narrow-0.1", "lean-0.1", "lean-0.2", "coldonly-0.1", "enforced-0.1",
        "enforced-0.2", "miss-0.1", "miss-0.2", "miss-0.3", "miss-0.4", "miss-0.5")
METRICS = {"tokens": lambda r: r["usage"]["total"], "dollars": lambda r: r.get("cost_usd")}
# (label, arm, baseline): single-run comparisons, then nets over one reuse.
SINGLE = (("write", "cold", "cold-nowrite"), ("same", "warm-same", "cold-nowrite"),
          ("related", "warm-related", "cold-nowrite-related"),
          ("same, read-only", "warm-same-nowrite", "cold-nowrite"),
          ("related, read-only", "warm-related-nowrite", "cold-nowrite-related"))
NET = (("net", "warm-related"), ("net, read-only", "warm-related-nowrite"))


def per_task(data: dict, metric) -> dict:
    """{condition: {task: mean metric over reps}}, skipping rows without the metric."""
    out = {}
    for cond, tasks in data.items():
        for t, rows in tasks.items():
            vals = [v for v in map(metric, rows) if v is not None]
            if vals:
                out.setdefault(cond, {})[t] = statistics.mean(vals)
    return out


def change(pairs: list) -> str:
    if not pairs:
        return "-"
    mean = statistics.mean(a / b - 1 for a, b in pairs)
    weighted = sum(a for a, _ in pairs) / sum(b for _, b in pairs) - 1
    return f"{mean:+.0%} / {weighted:+.0%}"


def score(v: dict, tasks: list) -> dict:
    out = {}
    for label, arm, base in SINGLE:
        out[label] = change([(v[arm][t], v[base][t]) for t in tasks if t in v.get(arm, {}) and t in v.get(base, {})])
    for label, arm in NET:
        conds = ("cold", arm, "cold-nowrite", "cold-nowrite-related")
        ts = [t for t in tasks if all(t in v.get(c, {}) for c in conds)]
        out[label] = change([(v["cold"][t] + v[arm][t], v["cold-nowrite"][t] + v["cold-nowrite-related"][t])
                             for t in ts])
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--md", help="also write the tables to this Markdown file")
    a = ap.parse_args()
    labels = [l for l, *_ in SINGLE] + [l for l, _ in NET]
    out = []
    for name in DIRS:
        path = ROOT / f"out_{name}" / "results.jsonl"
        if not path.exists():
            continue
        data = load(path)
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
        scores = {m: {g: score(per_task(data, f), ts) for g, ts in groups.items()} for m, f in METRICS.items()}
        rows = [f"| {g} | {len(ts)} | " + " | ".join(f"{scores['tokens'][g][l]} → {scores['dollars'][g][l]}"
                                                     for l in labels) + " |" for g, ts in groups.items()]
        out.append(f"## {name}\n\n| Group | Tasks | " + " | ".join(labels) + " |\n|" + "---|" * (len(labels) + 2)
                   + "\n" + "\n".join(rows) + "\n")
    text = ("Each cell: tokens → dollars, each as mean per-task change / weighted change. "
            "Negative is cheaper.\n\n" + "\n".join(out))
    sys.stdout.reconfigure(encoding="utf-8")
    print(text)
    if a.md:
        pathlib.Path(a.md).write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()

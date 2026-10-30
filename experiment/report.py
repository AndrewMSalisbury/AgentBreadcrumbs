"""Cold vs warm report for the L1 viability experiment.

  python report.py [--results out/results.jsonl] [--md out/report.md]

Uses the latest row per (condition, task, rep) and averages over reps. Savings are
measured against an agent with no registry that writes nothing, on the same
question: cold-nowrite for warm-same, cold-nowrite-related for warm-related. The
cost of writing is cold - cold-nowrite.
"Total" is every token Claude Code reports, cached reads included; "uncached"
leaves cache reads out, since they are billed at ~10%.
"""
import argparse, json, pathlib, statistics, sys

ROOT = pathlib.Path(__file__).parent
ARMS = ("cold", "cold-nowrite", "cold-nowrite-related", "warm-same", "warm-related")
# Each warm arm is measured against a no-write cold run on the same question.
BASE = {"warm-same": "cold-nowrite", "warm-related": "cold-nowrite-related"}
# Optional: warm registry but no writing, to separate what reading saves from what writing costs.
READ_ONLY = "warm-related-nowrite"
# Optional: same question read-only; with READ_ONLY it scores a policy where only cold agents write.
READ_ONLY_SAME = "warm-same-nowrite"
USE_CASES = ("hard_access", "docs", "coding")


def load(path: pathlib.Path) -> dict:
    """Latest row per (condition, task, rep), grouped as {condition: {task: [rows]}}."""
    latest = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            latest[(r["condition"], r["task"], r["rep"])] = r
    out = {}
    for (cond, task, _), r in latest.items():
        out.setdefault(cond, {}).setdefault(task, []).append(r)
    return out


def summarize(rows: list[dict]) -> dict:
    mean = lambda f: statistics.mean(f(r) for r in rows)
    calls = lambda r, *names: sum(n for k, n in r["tool_calls"].items() if k.endswith(names))
    return {"total": mean(lambda r: r["usage"]["total"]),
            "uncached": mean(lambda r: r["usage"]["total"] - r["usage"]["cache_read"]),
            "fetches": mean(lambda r: calls(r, "__fetch", "__render", "WebSearch")),
            "searches": mean(lambda r: calls(r, "WebSearch")),
            "renders": mean(lambda r: calls(r, "__render")),
            "wrote": mean(lambda r: calls(r, "__write") > 0),
            "wall": mean(lambda r: r["wall_s"]),
            "correct": mean(lambda r: r["correct"]),
            "use_case": rows[0]["use_case"], "set": rows[0].get("set") or "easy"}


def pct(new: float, old: float) -> str:
    return f"{(new - old) / old:+.0%}" if old else "n/a"


def table(header: list[str], rows: list[list]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return "\n".join(lines)


def report(data: dict) -> str:
    s = {c: {t: summarize(rs) for t, rs in data.get(c, {}).items()} for c in ARMS + (READ_ONLY, READ_ONLY_SAME)}
    tasks = [t for t in s["cold"] if all(t in s[c] for c in ARMS)]
    ro = s[READ_ONLY] if all(t in s[READ_ONLY] for t in tasks) else None
    ros = s[READ_ONLY_SAME] if ro and all(t in s[READ_ONLY_SAME] for t in tasks) else None
    if not tasks:
        return f"No task has runs in all arms ({', '.join(ARMS)}) yet."
    nw, nwr, cold, same, rel = (s[c] for c in ("cold-nowrite", "cold-nowrite-related", "cold",
                                                "warm-same", "warm-related"))
    out = []

    base = data.get("baseline", {}).get("baseline")
    if base:
        out.append(f"Baseline (no tools, one-word reply): {summarize(base)['total']:,.0f} total tokens.\n")

    rows = [[t, f"{cold[t]['set']}/{cold[t]['use_case']}", f"{cold[t]['total'] - nw[t]['total']:+,.0f}",
             f"{nw[t]['total']:,.0f} → {same[t]['total']:,.0f} ({pct(same[t]['total'], nw[t]['total'])})",
             f"{nwr[t]['total']:,.0f} → {rel[t]['total']:,.0f} ({pct(rel[t]['total'], nwr[t]['total'])})",
             f"{nw[t]['fetches']:.1f} → {same[t]['fetches']:.1f}",
             f"{nwr[t]['fetches']:.1f} → {rel[t]['fetches']:.1f}",
             " / ".join(f"{s[c][t]['correct']:.0%}" for c in ARMS),
             f"{same[t]['wrote']:.0%} / {rel[t]['wrote']:.0%}"]
            + ([f"{ro[t]['total']:,.0f} ({pct(ro[t]['total'], nwr[t]['total'])}), "
                f"{ro[t]['fetches']:.1f} fetches, {ro[t]['correct']:.0%}"] if ro else []) for t in tasks]
    out.append("## Per task\n\nTokens are totals. Each warm arm is compared with a no-write cold run on "
               "the same question: warm same with cold-nowrite, warm related with cold-nowrite-related. "
               "Write cost is cold minus cold-nowrite. Fetches count fetch, render and WebSearch. "
               "Correct is cold / nw / nw related / same / related.\n")
    out.append(table(["Task", "Set/use case", "Write cost", "Same: nw → warm", "Related: nw → warm",
                      "Fetches same", "Fetches related", "Correct", "Warm wrote s / r"]
                     + (["Related, read-only"] if ro else []), rows))

    def group(ts: list[str]) -> dict:
        g = {"n": len(ts), "tasks": ts}
        for c in ARMS:
            for k in ("total", "uncached", "fetches", "correct", "wall", "wrote"):
                g[c, k] = statistics.mean(s[c][t][k] for t in ts)
        # Mean of per-task reductions, so one huge task cannot dominate.
        for c, b in BASE.items():
            g[c, "cut"] = statistics.mean(1 - s[c][t]["total"] / s[b][t]["total"] for t in ts)
        if ro:
            g["ro", "total"] = statistics.mean(ro[t]["total"] for t in ts)
            g["ro", "cut"] = statistics.mean(1 - ro[t]["total"] / nwr[t]["total"] for t in ts)
            g["ro", "correct"] = statistics.mean(ro[t]["correct"] for t in ts)
        g["write"] = statistics.mean(cold[t]["total"] - nw[t]["total"] for t in ts)
        return g

    keys = sorted({(cold[t]["set"], cold[t]["use_case"]) for t in tasks},
                  key=lambda k: (k[0], USE_CASES.index(k[1]) if k[1] in USE_CASES else 9))
    groups = {f"{st}/{uc}": group([t for t in tasks if (cold[t]["set"], cold[t]["use_case"]) == (st, uc)])
              for st, uc in keys}
    sets = sorted({k[0] for k in keys})
    for st in sets:
        groups[f"{st}/all"] = group([t for t in tasks if cold[t]["set"] == st])
    if len(sets) > 1:
        groups["all"] = group(tasks)
    rows = [[name, g["n"], f"{g['write']:+,.0f}",
             f"{g['cold-nowrite', 'total']:,.0f} → {g['warm-same', 'total']:,.0f}",
             f"{g['cold-nowrite-related', 'total']:,.0f} → {g['warm-related', 'total']:,.0f}",
             f"{g['warm-same', 'cut']:.0%}", f"{g['warm-related', 'cut']:.0%}",
             f"{g['cold-nowrite-related', 'uncached']:,.0f} → {g['warm-related', 'uncached']:,.0f}",
             f"{g['cold-nowrite-related', 'fetches']:.1f} → {g['warm-related', 'fetches']:.1f}",
             " / ".join(f"{g[c, 'correct']:.0%}" for c in ARMS),
             f"{g['cold-nowrite-related', 'wall']:.0f} → {g['warm-related', 'wall']:.0f}"]
            + ([f"{g['ro', 'total']:,.0f}, cut {g['ro', 'cut']:.0%}, {g['ro', 'correct']:.0%} correct"] if ro else [])
            for name, g in groups.items()]
    out.append("\n## Per set and use case\n\nMean tokens per task. Cuts are the mean of per-task reductions "
               "against the no-write run on the same question.\n")
    out.append(table(["Group", "Tasks", "Write cost", "Same: nw → warm", "Related: nw → warm",
                      "Cut same", "Cut related", "Uncached related", "Fetches related",
                      "Correct", "Seconds related"] + (["Related, read-only"] if ro else []), rows))

    # Reuses needed to repay the write: write cost over the saving on one related reuse.
    paybacks = {}
    for t in tasks:
        saving = nwr[t]["total"] - rel[t]["total"]
        cost = max(cold[t]["total"] - nw[t]["total"], 0)
        paybacks[t] = cost / saving if saving > 0 else float("inf")

    out.append("\n## Viability bar\n")
    for name in [k for k in groups if k.endswith("/all")] + (["all"] if "all" in groups else []):
        g = groups[name]
        pb = [p for t, p in paybacks.items() if name == "all" or cold[t]["set"] == name.split("/")[0]]
        fewer = g["warm-related", "fetches"] < g["cold-nowrite-related", "fetches"] \
            and g["warm-same", "fetches"] < g["cold-nowrite", "fetches"]
        acc = g["warm-same", "correct"] >= g["cold-nowrite", "correct"] \
            and g["warm-related", "correct"] >= g["cold-nowrite-related", "correct"]
        cut = g["warm-related", "cut"]
        bar = [["Total tokens, warm related vs no-write related", "≥30% lower",
                f"{abs(cut):.0%} {'lower' if cut >= 0 else 'higher'}", "pass" if cut >= 0.30 else "fail"],
               ["Fetches and searches per task", "Lower when warm",
                f"same {g['cold-nowrite', 'fetches']:.1f} → {g['warm-same', 'fetches']:.1f}, related "
                f"{g['cold-nowrite-related', 'fetches']:.1f} → {g['warm-related', 'fetches']:.1f}",
                "pass" if fewer else "fail"],
               ["Answer accuracy", "No worse than no-write",
                f"same {g['cold-nowrite', 'correct']:.0%} → {g['warm-same', 'correct']:.0%}, related "
                f"{g['cold-nowrite-related', 'correct']:.0%} → {g['warm-related', 'correct']:.0%}",
                "pass" if acc else "fail"],
               ["Write cost recovered", "Within 2 reuses",
                f"{g['write']:+,.0f} tokens; {sum(p <= 2 for p in pb)}/{len(pb)} tasks within 2; "
                f"median {statistics.median(pb):.2f} reuses",
                "pass" if statistics.median(pb) <= 2 else "fail"]]
        if ro:
            rc = g["ro", "cut"]
            bar.insert(1, ["Total tokens, read-only warm related vs no-write related", "≥30% lower",
                           f"{abs(rc):.0%} {'lower' if rc >= 0 else 'higher'}", "pass" if rc >= 0.30 else "fail"])
        out.append(f"**{name}** ({g['n']} tasks)\n")
        out.append(table(["Measure", "Bar", "Result", ""], bar) + "\n")

    if ros:  # cold agents write, warm agents only read: both warm arms are the nowrite ones
        def cut(arm, base, ts):
            return statistics.mean(1 - arm[t]["total"] / base[t]["total"] for t in ts)
        rows = []
        for name, g in groups.items():
            ts = g["tasks"]
            pb = [max(cold[t]["total"] - nw[t]["total"], 0) / (nwr[t]["total"] - ro[t]["total"])
                  if nwr[t]["total"] > ro[t]["total"] else float("inf") for t in ts]
            rows.append([name, len(ts), f"{g['write']:+,.0f}",
                         f"{cut(ros, nw, ts):.0%}", f"{cut(ro, nwr, ts):.0%}",
                         f"{statistics.mean(nw[t]['fetches'] for t in ts):.1f} → "
                         f"{statistics.mean(ros[t]['fetches'] for t in ts):.1f}",
                         f"{statistics.mean(ros[t]['correct'] for t in ts):.0%} / "
                         f"{statistics.mean(ro[t]['correct'] for t in ts):.0%}",
                         f"{sum(p <= 2 for p in pb)}/{len(ts)}, median {statistics.median(pb):.2f}"])
        out.append("## Only cold agents write\n\nWarm agents read the cold registry and write nothing "
                   f"({READ_ONLY_SAME}, {READ_ONLY}). Cuts are against the no-write run on the same question; "
                   "reuses to repay the write use the read-only related saving.\n")
        out.append(table(["Group", "Tasks", "Write cost", "Cut same", "Cut related", "Fetches same",
                          "Correct same / related", "Write repaid within 2 reuses"], rows) + "\n")
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", default=str(ROOT / "out" / "results.jsonl"))
    ap.add_argument("--md", help="also write the report to this Markdown file")
    a = ap.parse_args()
    text = report(load(pathlib.Path(a.results)))
    sys.stdout.reconfigure(encoding="utf-8")
    print(text)
    if a.md:
        pathlib.Path(a.md).write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()

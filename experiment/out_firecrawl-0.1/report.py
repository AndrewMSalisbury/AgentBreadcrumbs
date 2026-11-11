"""firecrawl-0.1 report: per task, each arm's Claude dollars, Firecrawl credits and turns, net of
its setup's no-question baseline, with the local fetch's runs for reference.

  python out_firecrawl-0.1/report.py

Arms (all the related question, rep 1): stock = noregistry-related on stock firecrawl-mcp;
tool = noregistry-related on the Firecrawl-backed tool; fold = fold-0.1 on it. Credits: ours from
each run's calls.log ("firecrawl" lines); stock from its scrape calls, 1 per scrape plus 4 for the
`query` format (this matched every job's change in balance in drive.log, which can lag).
Baselines: a run whose first turn read the tool definitions from cache gets the warm baseline
(rep 2, run right after rep 1), else the cold one (rep 1). net = dollars - baseline + credits *
CREDIT. Local: noregistry-related from step 2 (out_miss-0.12) and fold-0.1 hits (out_fold-0.1,
trace-0.2's v1 cards), rep 1.
"""
import json, pathlib, statistics

HERE = pathlib.Path(__file__).parent
EXP = HERE.parent
CREDIT = 19 / 5000  # Hobby


def rows(path: pathlib.Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()] if path.exists() else []


def pick(rs, cond, task, it=None):
    m = [r for r in rs if r["condition"] == cond and r["task"] == task and r["rep"] == 1
         and (it is None or r.get("iteration") == it)]
    return m[-1] if m else None


ours, stock = rows(HERE / "results.jsonl"), rows(HERE / "stock" / "results.jsonl")


def baseline(rs, rep):
    return next(r for r in rs if r["condition"] == "baseline" and r["rep"] == rep)


BASE = {"tool": (baseline(ours, 1), baseline(ours, 2)), "stock": (baseline(stock, 1), baseline(stock, 2))}
BASE["fold"] = BASE["tool"]


def first_turn_cache_read(name: str, r: dict) -> int:
    run = HERE / ("stock" if name == "stock" else "") / "runs" / r["condition"] / r["task"] / "r1"
    for line in (run / "stream.jsonl").read_text(encoding="utf-8").splitlines():
        ev = json.loads(line)
        if ev.get("type") == "assistant":
            return ev["message"]["usage"].get("cache_read_input_tokens", 0)
    return 0


def base_for(name: str, r: dict) -> tuple[float, str]:
    cold, warm = BASE[name]
    if first_turn_cache_read(name, r) >= 0.5 * cold["usage"]["total"]:
        return warm["cost_usd"], "w"
    return cold["cost_usd"], "c"


def credits_of(name: str, r: dict) -> int:
    run = HERE / ("stock" if name == "stock" else "") / "runs" / r["condition"] / r["task"] / "r1"
    if name != "stock":
        log = run / "calls.log"
        return sum(int(l.split("\t")[2]) for l in log.read_text(encoding="utf-8").splitlines()
                   if l.startswith("firecrawl\t")) if log.exists() else 0
    n = 0
    for line in (run / "stream.jsonl").read_text(encoding="utf-8").splitlines():
        ev = json.loads(line)
        for b in ev.get("message", {}).get("content", []) if ev.get("type") == "assistant" else []:
            if b.get("type") == "tool_use" and b["name"].endswith("firecrawl_scrape"):
                n += 1 + 4 * ("query" in (b["input"].get("formats") or []))
    return n


local_noreg = rows(EXP / "out_miss-0.12" / "results.jsonl")
local_fold = rows(EXP / "out_fold-0.1" / "results.jsonl")
tasks = list(dict.fromkeys(r["task"] for r in ours if r["condition"] == "warm-related-nowrite"))
print("baselines cold / warm: tool ${:.3f} / ${:.3f}, stock ${:.3f} / ${:.3f}; a credit is ${:.4f}\n".format(
    *(r["cost_usd"] for k in ("tool", "stock") for r in BASE[k]), CREDIT))
print(f"{'task':26}{'arm':6}{'$':>8}{'base':>8}{'cr':>4}{'turns':>6}{'net':>8}   calls")
nets = {"stock": [], "tool": [], "fold": []}
for t in tasks:
    arms = {"stock": pick(stock, "noregistry-related", t), "tool": pick(ours, "noregistry-related", t),
            "fold": pick(ours, "warm-related-nowrite", t, "fold-0.1")}
    for name, r in arms.items():
        if not r:
            continue
        cr = credits_of(name, r)
        b, state = base_for(name, r)
        net = r["cost_usd"] - b + cr * CREDIT
        nets[name].append((t, net))
        calls = ", ".join(f"{k.rsplit('__', 1)[-1]} {v}" for k, v in r["tool_calls"].items())
        print(f"{t:26}{name:6}{r['cost_usd']:>8.3f}{b:>7.3f}{state}{cr:>4}{r['turns']:>6}{net:>8.3f}   "
              f"{calls}{'' if r['correct'] else '  WRONG'}")
    ln, lf = pick(local_noreg, "noregistry-related", t), pick(local_fold, "warm-related-nowrite", t, "fold-0.1")
    print(f"{'':26}local {'' if not ln else f'noregistry ${ln['cost_usd']:.3f}'}"
          f"{'' if not lf else f', fold ${lf['cost_usd']:.3f}'}\n")


def change(a, b, only=None):
    pairs = [(x, y) for (t, x) in nets[a] for (u, y) in nets[b] if t == u and y > 0 and (only is None or t in only)]
    if not pairs:
        return "n/a"
    med = statistics.median(x / y - 1 for x, y in pairs)
    tot = sum(x for x, _ in pairs) / sum(y for _, y in pairs) - 1
    return f"median {med:+.0%}, total {tot:+.0%} (n={len(pairs)})"


hard = [t for t in tasks if t != "redis-set"]
for label, only in (("all", None), ("hard set", hard)):
    print(f"{label}:")
    print("  net, fold vs tool (cards alone): ", change("fold", "tool", only))
    print("  net, tool vs stock (the tool):   ", change("tool", "stock", only))
    print("  net, fold vs stock (both):       ", change("fold", "stock", only))
print("totals, net $:", {k: round(sum(x for _, x in v), 3) for k, v in nets.items()})
print("correct:", {k: sum(1 for r in (stock if k == 'stock' else ours) if r['condition'] == c and r['correct'])
                   for k, c in (("stock", "noregistry-related"), ("tool", "noregistry-related"),
                                ("fold", "warm-related-nowrite"))})

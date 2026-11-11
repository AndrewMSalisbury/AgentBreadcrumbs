"""card-0.1 report: route cards in front of stock firecrawl-mcp's scrape against stock, per task and rep.

  python out_card-0.1/report.py

Arms (the related question): card = warm-related-nowrite on --backend firecrawl-card; stock =
noregistry-related on --backend firecrawl-mcp. Both load the same 30 tool definitions.
Credits, priced the same way for both arms from what each run called: a scrape passed to Firecrawl
is 1 credit plus 4 for the `query` format, a firecrawl_search 2; a card-served section adds the
credits its scrape logged (a raw source over plain HTTP is 0). drive.log has each job's change in
balance as a check. Baselines: a run whose first turn read the tool definitions from cache gets its
setup's warm baseline (r2, run right after r1), else the cold one (r1).
Claude dollars and credits are reported apart, and net at two credit prices: Hobby ($19 / 5000)
and Standard ($0.001).
"""
import json, pathlib, statistics

HERE = pathlib.Path(__file__).parent
PRICES = {"hobby": 19 / 5000, "standard": 0.001}
TASKS = ["bash-histsize", "gha-matrix-max-jobs", "git-gc-auto", "heroku-daily-restart", "mdn-fetch-credentials",
         "nginx-keepalive-requests", "render-free-spindown", "rust-vec-extract-if", "sonatype-guava"]
ARMS = {"card": (HERE, "warm-related-nowrite"), "stock": (HERE / "stock", "noregistry-related")}


def result(root: pathlib.Path, cond: str, task: str, rep: int) -> dict | None:
    p = root / "runs" / cond / task / f"r{rep}" / "result.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def run_dir(arm: str, task: str, rep: int) -> pathlib.Path:
    root, cond = ARMS[arm]
    return root / "runs" / cond / task / f"r{rep}"


def first_turn_cache_read(d: pathlib.Path) -> int:
    for line in (d / "stream.jsonl").read_text(encoding="utf-8").splitlines():
        ev = json.loads(line)
        if ev.get("type") == "assistant":
            return ev["message"]["usage"].get("cache_read_input_tokens", 0)
    return 0


BASE = {arm: tuple(result(root, "baseline", "baseline", rep) for rep in (1, 2)) for arm, (root, _) in ARMS.items()}


def base_for(arm: str, d: pathlib.Path) -> tuple[float, str]:
    cold, warm = BASE[arm]
    if first_turn_cache_read(d) >= 0.5 * cold["usage"]["total"]:
        return warm["cost_usd"], "w"
    return cold["cost_usd"], "c"


def scrape_credits(name: str, args: dict) -> int:
    if name.endswith("firecrawl_scrape"):
        fmts = args.get("formats") or []
        q = any(f == "query" or (isinstance(f, dict) and f.get("type") == "query") for f in fmts)
        return 1 + 4 * q
    if name.endswith("firecrawl_search"):
        return 2
    return 0


def credits(arm: str, d: pathlib.Path) -> tuple[int, str]:
    """(credits, what the card did: served / redirect / others / '')."""
    if arm == "card":
        lines = (d / "calls.log").read_text(encoding="utf-8").splitlines() if (d / "calls.log").exists() else []
        n, did = 0, []
        for l in lines:
            kind, *rest = l.split("\t")
            if kind == "forward":
                n += scrape_credits(rest[0], json.loads(rest[1]))
            elif kind == "card":
                n += int(rest[2])
                did.append("served")
            elif kind == "card-redirect":
                did.append("redirect")
            elif kind == "card-others":
                did.append("others")
            elif kind == "card-miss":
                did.append("miss")
        return n, ",".join(did)
    n = 0
    for line in (d / "stream.jsonl").read_text(encoding="utf-8").splitlines():
        ev = json.loads(line)
        for b in ev.get("message", {}).get("content", []) if ev.get("type") == "assistant" else []:
            if b.get("type") == "tool_use":
                n += scrape_credits(b["name"], b["input"])
    return n, ""


print("baselines cold / warm: " + ", ".join(f"{a} ${BASE[a][0]['cost_usd']:.3f} / ${BASE[a][1]['cost_usd']:.3f}"
                                             for a in ARMS) + "\n")
print(f"{'task':26}{'rep':>3} {'arm':6}{'$':>8}{'base':>8}{'claude':>8}{'cr':>4}{'turns':>6}   card / calls")
rows = []  # (task, rep, arm, claude net $, credits, correct, did)
for t in TASKS:
    for rep in (1, 2):
        for arm, (root, cond) in ARMS.items():
            r = result(root, cond, t, rep)
            if not r:
                continue
            d = run_dir(arm, t, rep)
            b, state = base_for(arm, d)
            cr, did = credits(arm, d)
            rows.append((t, rep, arm, r["cost_usd"] - b, cr, r["correct"], did))
            calls = ", ".join(f"{k.rsplit('__', 1)[-1]} {v}" for k, v in r["tool_calls"].items())
            print(f"{t:26}{rep:>3} {arm:6}{r['cost_usd']:>8.3f}{b:>7.3f}{state}{r['cost_usd'] - b:>8.3f}{cr:>4}"
                  f"{r['turns']:>6}   {did + ' / ' if did else ''}{calls}{'' if r['correct'] else '  WRONG'}")
    print()

touched = {t for (t, _, arm, *_, did) in rows if arm == "card" and ("served" in did or "redirect" in did)}


def pairs(price: float | None, only=None):
    """(card, stock) per task and rep; price None = Claude dollars only, else net with credits."""
    by = {(t, rep, arm): (c + (cr * price if price is not None else 0)) for (t, rep, arm, c, cr, _, _) in rows}
    return [(by[(t, rep, "card")], by[(t, rep, "stock")]) for t in TASKS for rep in (1, 2)
            if (t, rep, "card") in by and (t, rep, "stock") in by and (only is None or t in only)]


def change(ps) -> str:
    ps = [(x, y) for x, y in ps if y > 0]
    if not ps:
        return "n/a"
    med = statistics.median(x / y - 1 for x, y in ps)
    tot = sum(x for x, _ in ps) / sum(y for _, y in ps) - 1
    wins = sum(x < y for x, y in ps)
    return f"median {med:+.0%}, total {tot:+.0%}, card cheaper in {wins} of {len(ps)}"


print(f"card used (served a route or redirected) on: {sorted(touched)}\n")
for label, only in (("all tasks", None), ("card used", touched), ("card not used", set(TASKS) - touched)):
    print(f"{label}:")
    print(f"  Claude $ only:        {change(pairs(None, only))}")
    for name, p in PRICES.items():
        print(f"  net at {name:9}      {change(pairs(p, only))}")
    cr = {arm: sum(c for (t, _, a, _, c, _, _) in rows if a == arm and (only is None or t in only)) for arm in ARMS}
    print(f"  credits: {cr}")
for arm in ARMS:
    rs = [x for x in rows if x[2] == arm]
    print(f"{arm}: {sum(x[5] for x in rs)}/{len(rs)} correct, Claude net ${sum(x[3] for x in rs):.3f}, "
          f"{sum(x[4] for x in rs)} credits")

# rep-to-rep spread of the same arm on the same task: the noise floor for the gaps above
spread = [abs(a / b - 1) for t in TASKS for arm in ARMS
          for a, b in [tuple(x[3] for x in rows if x[0] == t and x[2] == arm)] if b > 0] \
    if all(len([x for x in rows if x[0] == t and x[2] == arm]) == 2 for t in TASKS for arm in ARMS) else []
if spread:
    print(f"\nrep-to-rep spread, same arm and task (Claude $): median {statistics.median(spread):.0%}")

"""card-0.2 report: card-0.1's gain split into the prompt line and the cards, and card-0.2 on rust.

  python out_card-0.2/report.py

Arms, the related question, per task the mean over reps:
  stock       noregistry-related on stock firecrawl-mcp: out_card-0.1/stock r1-r2, out_card-0.2/stock r3
  promptonly  the card arm's wrapper and prompt with an empty registry (out_card-0.2/promptonly, r1-r2)
  card-0.1    the card arm with firecrawl-0.1's cards, redirect on (out_card-0.1, r1-r2)
  card-0.2    the same without the redirect: rust only (out_card-0.2/card, r1-r2); elsewhere card-0.1's
              runs stand in, since the wrapper behaves the same on every other task
Costs are Claude dollars net of the setup's baseline (card-0.1's, cold or warm by the first turn's
cache read), and credits priced as in out_card-0.1/report.py. A run whose first turn read nothing from
cache paid to write the ~42k tokens of tool definitions; no baseline measures that (both setups'
baselines read them from cache), so such a run is dropped and named (promptonly bash r1, the batch's
first run after the cache had expired overnight: $0.179 against $0.019 for r2).
"""
import json, pathlib, statistics

HERE = pathlib.Path(__file__).parent
C1 = HERE.parent / "out_card-0.1"
PRICES = {"hobby": 19 / 5000, "standard": 0.001}
TASKS = ["bash-histsize", "gha-matrix-max-jobs", "git-gc-auto", "heroku-daily-restart", "mdn-fetch-credentials",
         "nginx-keepalive-requests", "render-free-spindown", "rust-vec-extract-if", "sonatype-guava"]
W, N = "warm-related-nowrite", "noregistry-related"


def dirs(arm: str, t: str) -> list[pathlib.Path]:
    if arm == "stock":
        return [C1 / "stock/runs" / N / t / "r1", C1 / "stock/runs" / N / t / "r2", HERE / "stock/runs" / N / t / "r3"]
    if arm == "promptonly":
        return [HERE / "promptonly/runs" / W / t / f"r{r}" for r in (1, 2)]
    if arm == "card-0.2" and t == "rust-vec-extract-if":
        return [HERE / "card/runs" / W / t / f"r{r}" for r in (1, 2)]
    return [C1 / "runs" / W / t / f"r{r}" for r in (1, 2)]


def load(p: pathlib.Path):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


BASE = {"stock": [load(C1 / "stock/runs/baseline/baseline" / f"r{r}" / "result.json") for r in (1, 2)],
        "card": [load(C1 / "runs/baseline/baseline" / f"r{r}" / "result.json") for r in (1, 2)]}


def cold_cache(d: pathlib.Path) -> bool:
    for line in (d / "stream.jsonl").read_text(encoding="utf-8").splitlines():
        ev = json.loads(line)
        if ev.get("type") == "assistant":
            return ev["message"]["usage"].get("cache_read_input_tokens", 0) == 0
    return False


def baseline(arm: str, d: pathlib.Path) -> float:
    cold, warm = BASE["stock" if arm == "stock" else "card"]
    for line in (d / "stream.jsonl").read_text(encoding="utf-8").splitlines():
        ev = json.loads(line)
        if ev.get("type") == "assistant":
            hit = ev["message"]["usage"].get("cache_read_input_tokens", 0) >= 0.5 * cold["usage"]["total"]
            return (warm if hit else cold)["cost_usd"]
    return cold["cost_usd"]


def price(name: str, args: dict) -> int:
    if name.endswith("firecrawl_scrape"):
        q = any(f == "query" or (isinstance(f, dict) and f.get("type") == "query") for f in args.get("formats") or [])
        return 1 + 4 * q
    return 2 if name.endswith("firecrawl_search") else 0


def credits(arm: str, d: pathlib.Path) -> tuple[int, list[str]]:
    if arm != "stock":
        n, did = 0, []
        log = d / "calls.log"
        for l in log.read_text(encoding="utf-8").splitlines() if log.exists() else []:
            kind, *rest = l.split("\t")
            if kind == "forward":
                n += price(rest[0], json.loads(rest[1]))
            elif kind == "card":
                n += int(rest[2])
            if kind.startswith("card"):
                did.append(kind.removeprefix("card-") if kind != "card" else "served")
        return n, did
    n = 0
    for line in (d / "stream.jsonl").read_text(encoding="utf-8").splitlines():
        ev = json.loads(line)
        for b in ev.get("message", {}).get("content", []) if ev.get("type") == "assistant" else []:
            if b.get("type") == "tool_use":
                n += price(b["name"], b["input"])
    return n, []


ARMS = ("stock", "promptonly", "card-0.1", "card-0.2")
runs = {}  # (arm, task) -> [(claude net, credits, correct, turns, did, first scrape or search)]
for arm in ARMS:
    for t in TASKS:
        out = []
        for d in dirs(arm, t):
            r = load(d / "result.json")
            if not r:
                continue
            if cold_cache(d):
                print(f"dropped (cold cache, ${r['cost_usd']:.3f}): {arm} {t} {d.name}")
                continue
            cr, did = credits(arm, d)
            first = next((k.rsplit("__", 1)[-1] for k in r["tool_calls"]), "")
            out.append((r["cost_usd"] - baseline(arm, d), cr, r["correct"], r["turns"], did, first))
        runs[(arm, t)] = out

print(f"{'task':26}" + "".join(f"{a:>22}" for a in ARMS))
print(f"{'':26}" + "".join(f"{'$ net  cr  turns':>22}" for _ in ARMS))
for t in TASKS:
    cells = []
    for a in ARMS:
        rs = runs[(a, t)]
        if not rs:
            cells.append(f"{'-':>22}")
            continue
        m = statistics.mean
        bad = sum(not x[2] for x in rs)
        cells.append(f"{m(x[0] for x in rs):>10.3f}{m(x[1] for x in rs):>5.1f}{m(x[3] for x in rs):>5.1f}"
                     f"{'  ' + str(bad) + 'X' if bad else '':>2}")
    print(f"{t:26}" + "".join(cells))
print()


def mean_cost(arm: str, t: str, p: float | None) -> float:
    rs = runs[(arm, t)]
    return statistics.mean(x[0] + (x[1] * p if p is not None else 0) for x in rs)


def compare(a: str, b: str, p: float | None) -> str:
    ps = [(mean_cost(a, t, p), mean_cost(b, t, p)) for t in TASKS if runs[(a, t)] and runs[(b, t)]]
    med = statistics.median(x / y - 1 for x, y in ps)
    tot = sum(x for x, _ in ps) / sum(y for _, y in ps) - 1
    return f"median {med:+.0%}, total {tot:+.0%}, cheaper on {sum(x < y for x, y in ps)} of {len(ps)}"


for a, b, what in (("promptonly", "stock", "the prompt line and wrapper alone"),
                   ("card-0.1", "promptonly", "card-0.1's cards, net of the prompt"),
                   ("card-0.2", "promptonly", "card-0.2's cards, net of the prompt"),
                   ("card-0.1", "stock", "card-0.1 against stock (3 stock reps)"),
                   ("card-0.2", "stock", "card-0.2 against stock")):
    print(f"{what}:")
    print(f"  Claude $       {compare(a, b, None)}")
    for name, p in PRICES.items():
        print(f"  net {name:9}  {compare(a, b, p)}")

print("\nfirst web tool per run (does the prompt line change the opening move?):")
for a in ("stock", "promptonly"):
    firsts = [x[5] for t in TASKS for x in runs[(a, t)]]
    print(f"  {a:11} " + ", ".join(f"{k} {firsts.count(k)}" for k in sorted(set(firsts))))
print("heroku first tools:", {a: [x[5] for x in runs[(a, 'heroku-daily-restart')]] for a in ("stock", "promptonly", "card-0.1")})
print("rust card-0.2:", [(round(x[0], 3), x[1], x[3], x[4]) for x in runs[("card-0.2", "rust-vec-extract-if")]],
      " card-0.1:", [(round(x[0], 3), x[1], x[3], x[4]) for x in runs[("card-0.1", "rust-vec-extract-if")]])
spread = [abs(x[0] / y[0] - 1) for a in ARMS[:2] for t in TASKS
          for i, x in enumerate(runs[(a, t)]) for y in runs[(a, t)][i + 1:] if y[0] > 0]
print(f"rep-to-rep spread, stock and promptonly pairs (Claude $): median {statistics.median(spread):.0%}")
for a in ARMS:
    rs = [x for t in TASKS for x in runs[(a, t)]]
    print(f"{a}: {sum(x[2] for x in rs)}/{len(rs)} correct")

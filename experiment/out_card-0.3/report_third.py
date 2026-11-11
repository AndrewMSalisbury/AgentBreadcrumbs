"""third-0.1 report: card-0.3 against stock on the third question (drive_third.py).

  python out_card-0.3/report_third.py

Per task, the mean over reps of Claude dollars net of the setup's own baseline (this batch's, run
first so the cache was warm) and of Firecrawl credits, priced as in out_card-0.1/report.py. A run
whose first turn read nothing from cache is dropped and named. For the card arm, what the wrapper
did on each run: served (the page's own card), route (matched by the page the route reads),
named, others, miss.
"""
import json, pathlib, statistics

HERE = pathlib.Path(__file__).parent
PRICES = {"hobby": 19 / 5000, "standard": 0.001}
SECTION = ["gha-matrix-max-jobs", "git-gc-auto", "mdn-fetch-credentials"]
OTHER = ["bash-histsize", "heroku-daily-restart", "nginx-keepalive-requests", "render-free-spindown",
         "rust-vec-extract-if", "sonatype-guava"]
COND = {"card": "warm-third-nowrite", "stock": "noregistry-third"}


def load(p: pathlib.Path):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


BASE = {a: load(HERE / a / "runs/baseline/baseline/r1/result.json") for a in COND}
# The card baseline ran first in the batch, on a cold cache ($0.1675, 0 tokens read from cache), so it
# measures the cache write no task run paid. The card arm is netted of card-0.1's two warm card baselines.
_c1 = [load(HERE.parent / "out_card-0.1/runs/baseline/baseline" / f"r{r}" / "result.json")["cost_usd"] for r in (1, 2)]
print(f"card baseline here ${BASE['card']['cost_usd']:.4f} (cold); using card-0.1's warm mean ${statistics.mean(_c1):.4f}")
BASE["card"] = {"cost_usd": statistics.mean(_c1)}


def first_usage(d: pathlib.Path) -> dict:
    for line in (d / "stream.jsonl").read_text(encoding="utf-8").splitlines():
        ev = json.loads(line)
        if ev.get("type") == "assistant":
            return ev["message"]["usage"]
    return {}


def price(name: str, args: dict) -> int:
    if name.endswith("firecrawl_scrape"):
        q = any(f == "query" or (isinstance(f, dict) and f.get("type") == "query") for f in args.get("formats") or [])
        return 1 + 4 * q
    return 2 if name.endswith("firecrawl_search") else 0


def credits(arm: str, d: pathlib.Path) -> tuple[int, list[str]]:
    if arm == "card":
        n, did = 0, []
        log = d / "calls.log"
        for l in log.read_text(encoding="utf-8").splitlines() if log.exists() else []:
            kind, *rest = l.split("\t")
            if kind == "forward":
                n += price(rest[0], json.loads(rest[1]))
            elif kind in ("card", "card-route"):
                n += int(rest[2])
            if kind.startswith("card"):
                did.append("served" if kind == "card" else kind.removeprefix("card-"))
        return n, did
    n = 0
    for line in (d / "stream.jsonl").read_text(encoding="utf-8").splitlines():
        ev = json.loads(line)
        for b in ev.get("message", {}).get("content", []) if ev.get("type") == "assistant" else []:
            if b.get("type") == "tool_use":
                n += price(b["name"], b["input"])
    return n, []


def scrapes(d: pathlib.Path) -> list[str]:
    out = []
    for line in (d / "stream.jsonl").read_text(encoding="utf-8").splitlines():
        ev = json.loads(line)
        for b in ev.get("message", {}).get("content", []) if ev.get("type") == "assistant" else []:
            if b.get("type") == "tool_use":
                i = b["input"]
                out.append(b["name"].rsplit("__", 1)[-1].replace("firecrawl_", "") + ":"
                           + str(i.get("url") or i.get("query") or "")[-60:])
    return out


runs = {}  # (arm, task) -> [dict]
for arm, cond in COND.items():
    for t in SECTION + OTHER:
        out = []
        for d in sorted((HERE / arm / "runs" / cond / t).glob("r*")):
            r = load(d / "result.json")
            if not r:
                continue
            if first_usage(d).get("cache_read_input_tokens", 0) == 0:
                print(f"dropped (cold cache, ${r['cost_usd']:.3f}): {arm} {t} {d.name}")
                continue
            cr, did = credits(arm, d)
            out.append({"net": r["cost_usd"] - BASE[arm]["cost_usd"], "cr": cr, "ok": r["correct"],
                        "turns": r["turns"], "did": did, "calls": scrapes(d), "rep": d.name,
                        "answer": r["answer"][:70]})
        runs[(arm, t)] = out

m = statistics.mean
print(f"baselines: card ${BASE['card']['cost_usd']:.4f}, stock ${BASE['stock']['cost_usd']:.4f}\n")
print(f"{'task':26}{'card $ net  cr turns':>24}{'stock $ net  cr turns':>24}   card did")
for t in SECTION + OTHER:
    cells = []
    for a in COND:
        rs = runs[(a, t)]
        bad = sum(not x["ok"] for x in rs)
        cells.append(f"{m(x['net'] for x in rs):>12.3f}{m(x['cr'] for x in rs):>6.1f}{m(x['turns'] for x in rs):>5.1f}"
                     + (f" {bad}X" if bad else "  ") if rs else f"{'-':>25}")
    print(f"{t:26}" + "".join(cells) + "   " + "; ".join(",".join(x["did"]) or "-" for x in runs[("card", t)]))
print()


def cost(a: str, t: str, p: float | None) -> float:
    return m(x["net"] + (x["cr"] * p if p is not None else 0) for x in runs[(a, t)])


def compare(ts: list[str], p: float | None) -> str:
    ps = [(cost("card", t, p), cost("stock", t, p)) for t in ts if runs[("card", t)] and runs[("stock", t)]]
    if not ps:
        return "-"
    med = statistics.median(x / y - 1 for x, y in ps)
    tot = sum(x for x, _ in ps) / sum(y for _, y in ps) - 1
    return f"median {med:+.0%}, total {tot:+.0%}, cheaper on {sum(x < y for x, y in ps)} of {len(ps)}"


for label, ts in (("section-route tasks (gha, git-gc, mdn)", SECTION), ("other 6", OTHER), ("all 9", SECTION + OTHER)):
    print(f"card-0.3 vs stock, {label}:")
    print(f"  Claude $       {compare(ts, None)}")
    for name, p in PRICES.items():
        print(f"  net {name:9}  {compare(ts, p)}")

print("\nper run, section-route tasks:")
for t in SECTION:
    for a in COND:
        for x in runs[(a, t)]:
            print(f"  {t[:12]:12} {a:5} {x['rep']} ${x['net']:.3f} {x['cr']:>2}cr {x['turns']}t "
                  f"{'ok ' if x['ok'] else 'BAD'} {','.join(x['did']) or '-':12} {' | '.join(x['calls'])}")
for a in COND:
    rs = [x for t in SECTION + OTHER for x in runs[(a, t)]]
    print(f"{a}: {sum(x['ok'] for x in rs)}/{len(rs)} correct")

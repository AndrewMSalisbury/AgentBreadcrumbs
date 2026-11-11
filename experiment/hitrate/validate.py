"""Live check of the offline hit-rate model on gha (LOG 2026-11-11).

  python hitrate/validate.py --dry     # seeds, predictions and the runs it would make
  python hitrate/validate.py           # runs them (warm-same-nowrite, card-0.4) and compares

One random order of gha's questions (SEED); the first K are seeds and become a registry the way
curve.py's first-card model builds cards (keyed by the seed's start page, routing to its answer
page and the heading holding its anchor). Held-out questions are picked across the predicted
outcomes, run once each on the card arm (no stock arm: the check is whether the wrapper does what
the model predicts, which the call log shows), and the logged outcome is compared with the
prediction. The question is the Stack Overflow title; answers aren't graded.
"""
import json, pathlib, random, sqlite3, subprocess, sys, time

HERE = pathlib.Path(__file__).parent
EXP = HERE.parent
sys.path.insert(0, str(EXP))
sys.path.insert(0, str(HERE))
from bc.common import page_id, host_of, _firecrawl_key
import curve

SITE, SEED, K = "gha", 7, 50
PICK = {"right-same": 3, "right-other": 3, "wrong": 4, "named": 2, "miss": 2}
OUT = EXP / "out_hitrate-0.1"
PY = str(EXP.parent / ".venv" / "Scripts" / "python.exe")
BUDGET = 90


def heading_anchor(apid: str, section: tuple[int, int] | None) -> str | None:
    if not section:
        return None
    tree = curve.trees[apid]
    return next((h[3] for h in tree["heads"] if h[0] == section[0]), None)


def setup():
    qs = [q for q in curve.prepare(top=False, canonical=False) if q["site"] == SITE]
    ids = [r for r in curve.rows if r["site"] == SITE and curve.start.get(str(r["answer_id"]))]
    for q, r in zip(qs, ids):
        q["row"] = r
    order = qs[:]
    random.Random(SEED).shuffle(order)
    seeds, held = order[:K], order[K:]
    cards = {}
    for s in seeds:
        cards.setdefault(s["start"], []).append(s) if s["start"] not in cards else None
    preds = [(q, curve.outcome(q, cards, route_match=True)) for q in held]
    picked = []
    for o, n in PICK.items():
        picked += [(q, p) for q, p in preds if p == o][:n]
    return seeds, cards, preds, picked


def registry(cards: dict, path: pathlib.Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE IF NOT EXISTS sites (site TEXT PRIMARY KEY, record TEXT NOT NULL, written_at TEXT NOT NULL)")
        db.execute("CREATE TABLE IF NOT EXISTS pages (id TEXT PRIMARY KEY, site TEXT NOT NULL, record TEXT NOT NULL, written_at TEXT NOT NULL)")
        for key, (s,) in cards.items():
            start_url = curve.start[str(s["row"]["answer_id"])]
            route = {"url": curve.trees.get(s["answer"], {}).get("url") or s["row"]["doc_url"]}
            if (a := heading_anchor(s["answer"], s["section"])):
                route["section"] = a
            rec = {"id": key, "schema": "0.2", "url": start_url, "tier": "L1", "answers": s["row"]["title"][:120],
                   "route": route, "provenance": {"writer": "hitrate-model"}}
            db.execute("INSERT OR REPLACE INTO pages VALUES (?, ?, ?, ?)", (key, host_of(start_url), json.dumps(rec), "2026-11-11"))


def credits() -> int:
    import httpx
    r = httpx.get("https://api.firecrawl.dev/v2/team/credit-usage", timeout=30,
                  headers={"Authorization": f"Bearer {_firecrawl_key()}"})
    return r.json()["data"]["remainingCredits"]


def logged(run_dir: pathlib.Path) -> str:
    kinds = [l.split("\t")[0] for l in (run_dir / "calls.log").read_text(encoding="utf-8").splitlines()] \
        if (run_dir / "calls.log").exists() else []
    for k, name in (("card", "served"), ("card-route", "served (route match)"), ("card-skip", "skipped"),
                    ("card-named", "named"), ("card-miss", "section not found")):
        if k in kinds:
            return name
    return "no card"


def main():
    dry = "--dry" in sys.argv
    seeds, cards, preds, picked = setup()
    from collections import Counter
    print(f"{SITE}: {K} seeds -> {len(cards)} cards ({sum(bool(c[0]['section']) for c in cards.values())} with a section);"
          f" {len(preds)} held out, predicted: {dict(Counter(p for _, p in preds))}")
    tasks = [{"id": f"so{q['row']['answer_id']}", "set": "hitrate", "use_case": "docs", "question": q["row"]["title"],
              "expect": ["."]} for q, _ in picked]
    import yaml
    (OUT).mkdir(exist_ok=True)
    (OUT / "tasks.yaml").write_text(yaml.safe_dump(tasks, sort_keys=False, allow_unicode=True), encoding="utf-8")
    for t in tasks:
        registry(cards, OUT / "runs/cold" / t["id"] / "r1/registry.sqlite")
    if dry:
        for q, p in picked:
            print(f"  {p:12} start {q['start'][-55:]:55}  {q['row']['title'][:70]}")
        return
    start = credits()
    for (q, p), t in zip(picked, tasks):
        run_dir = OUT / "runs/warm-same-nowrite" / t["id"] / "r1"
        if not (run_dir / "result.json").exists():
            if start - credits() > BUDGET:
                print("budget reached")
                break
            subprocess.run([PY, str(EXP / "run.py"), "warm-same-nowrite", "--rep", "1", "--out", str(OUT), "--backend",
                            "firecrawl-card", "--iteration", "card-0.4", "--tasks", str(OUT / "tasks.yaml"), "--task", t["id"]],
                           cwd=EXP, capture_output=True)
    rows = []
    for (q, p), t in zip(picked, tasks):
        run_dir = OUT / "runs/warm-same-nowrite" / t["id"] / "r1"
        if not (run_dir / "result.json").exists():
            continue
        from start import first_scrapes
        first = first_scrapes(run_dir / "stream.jsonl") or ""
        rows.append({"id": t["id"], "predicted": p, "logged": logged(run_dir), "start_guess": q["start"],
                     "first_scrape": page_id(first) if first else "", "same_start": page_id(first) == q["start"] if first else False,
                     "cost": json.loads((run_dir / "result.json").read_text(encoding="utf-8"))["cost_usd"],
                     "title": q["row"]["title"]})
    (OUT / "validate.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
    for r in rows:
        print(f"  {r['predicted']:12} -> {r['logged']:22} start {'same' if r['same_start'] else 'DIFF'}  "
              f"${r['cost']:.3f}  {r['title'][:60]}")
    print(f"credits spent: {start - credits()}")


if __name__ == "__main__":
    main()

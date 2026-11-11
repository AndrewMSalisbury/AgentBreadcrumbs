"""worth-0.1: what a pooled card's section is worth on the local fetch, served by the agent's question or as an outline.

  python out_worth-0.1/drive.py --dry      # the tasks, their predicted outcomes and the job count
  python out_worth-0.1/drive.py            # registries, a warm-up run per arm, then every job
  python out_worth-0.1/drive.py --report   # cost per arm and outcome

curve-0.1 gave hit rates: after 75 earlier gha questions a pooled card serves the right section to
12% and a wrong one to 18%. This prices a hit. Each question's registry pools the trace cards of the
other 98 curve-0.1 runs (leave-one-out), every seed's section route kept with the question it
answered. Questions are chosen by the outcome hitrate/score.py predicts for them under that registry,
since a random 24 would hold about 3 right hits: all 14 predicted right, 10 of the 18 wrong, and 4
misses as a control (the arms' prompt and tool text with no card). Three arms, reps 1-2:

  stock     noregistry (fetch, render, WebSearch; no cards)
  question  warm-same-nowrite, worth-0.1q: fetch takes the agent's question and serves the stored
            section bc.section_match.best ranks as answering it, else the page
  outline   warm-same-nowrite, worth-0.1o: a carded page's headings and stored sections in place of it

Each arm gets its own folder (stock/, question/, outline/) since the two card arms share a condition.
Before the jobs, one throwaway run per arm on a seed question (warmup/), so no arm starts cold.
"""
import collections, concurrent.futures as cf, datetime, json, pathlib, random, sqlite3, statistics, subprocess, sys, threading, time

import yaml

HERE = pathlib.Path(__file__).parent
EXP = HERE.parent
sys.path.insert(0, str(EXP))
sys.path.insert(0, str(EXP / "hitrate"))
sys.argv = sys.argv[:1] + [a for a in sys.argv[1:]]  # score.py reads --out only
import score  # noqa: E402
import build  # noqa: E402  (out_trace-0.1, on score's path)
from bc.common import page_id, host_of  # noqa: E402

PY = str(EXP.parent / ".venv" / "Scripts" / "python.exe")
CURVE = EXP / "out_curve-0.1"
TASKS = HERE / "tasks.yaml"
REPS = (1, 2)
WORKERS = 4
WAIT = 15 * 60
ARMS = {"stock": ("noregistry", None), "question": ("warm-same-nowrite", "worth-0.1q"),
        "outline": ("warm-same-nowrite", "worth-0.1o")}
PICK = {"right": 14, "wrong": 10, "miss": 4}
lock = threading.Lock()


def log(msg: str) -> None:
    with lock, open(HERE / "drive.log", "a", encoding="utf-8") as f:
        f.write(f"{datetime.datetime.now():%m-%d %H:%M:%S} {msg}\n")


def seeds() -> dict[str, dict]:
    """curve-0.1's runs (score.runs) with each run's card record, by task id."""
    out = {}
    for r in score.runs():
        if "key" in r:
            r["card"] = build.card(CURVE / "runs/noregistry" / r["id"] / "r1" / "stream.jsonl", lean=True)
        out[r["id"]] = r
    return out


def predicted(rs: dict) -> dict[str, str]:
    out = {}
    for q in rs.values():
        cards = {}
        for s in rs.values():
            if s["id"] != q["id"] and "key" in s:
                cards.setdefault(s["key"], []).append(s)
        out[q["id"]] = score.outcome(q, cards)
    return out


def chosen(pred: dict) -> dict[str, str]:
    rng = random.Random(0)
    out = {}
    for o, n in PICK.items():
        ids = sorted(t for t, p in pred.items() if p == o)
        out.update({t: o for t in (ids if len(ids) <= n else rng.sample(ids, n))})
    return out


def registry(path: pathlib.Path, rs: dict, held: str) -> int:
    """The pooled registry for one held-out question: one record per card page, every other seed's route."""
    pages = {}
    for s in rs.values():
        if s["id"] == held or "key" not in s:
            continue
        rec = pages.setdefault(s["key"], {**s["card"], "id": s["key"], "routes": []})
        rec["routes"].append({**s["card"]["route"], "for": s["question"]})
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    with sqlite3.connect(path) as db:
        db.executescript("""CREATE TABLE sites (site TEXT PRIMARY KEY, record TEXT NOT NULL, written_at TEXT NOT NULL);
            CREATE TABLE pages (id TEXT PRIMARY KEY, site TEXT NOT NULL, record TEXT NOT NULL, written_at TEXT NOT NULL);
            CREATE INDEX pages_site ON pages (site);""")
        db.executemany("INSERT INTO pages VALUES (?, ?, ?, ?)",
                       [(k, host_of(v["url"]), json.dumps(v, ensure_ascii=False), "2026-11-11") for k, v in pages.items()])
    db.close()
    return len(pages)


def result(arm: str, task: str, rep: int, root: pathlib.Path = HERE) -> dict | None:
    cond = ARMS[arm][0]
    try:
        return json.loads((root / arm / "runs" / cond / task / f"r{rep}" / "result.json").read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return None


def limited(r: dict) -> bool:
    a = (r.get("answer") or "").lower()
    return r["exit_code"] != 0 and "limit" in a and "hit your" in a


def run(arm: str, task: str, rep: int, root: pathlib.Path = HERE) -> str:
    cond, it = ARMS[arm]
    while True:
        r = result(arm, task, rep, root)
        if r is not None and not limited(r):
            return f"{arm:8} {task} r{rep}  {r['turns']} turns  ${r['cost_usd'] or 0:.3f}"
        cmd = [PY, "run.py", cond, "--task", task, "--rep", str(rep), "--tasks", str(TASKS), "--out", str(root / arm)]
        if it:
            cmd += ["--iteration", it]
        subprocess.run(cmd, cwd=EXP, stdin=subprocess.DEVNULL, capture_output=True)
        r = result(arm, task, rep, root)
        if r is None:
            log(f"{arm} {task} r{rep} left no result.json; retrying in 60 s")
            time.sleep(60)
        elif limited(r):
            log(f"usage limit at {arm} {task} r{rep}; retrying in 15 min")
            time.sleep(WAIT)


def setup(rs: dict, pick: dict) -> None:
    curve = {t["id"]: t for t in yaml.safe_load((CURVE / "tasks.yaml").read_text(encoding="utf-8"))}
    warm = sorted(t for t in rs if t not in pick)[0]
    TASKS.write_text(yaml.safe_dump([curve[t] for t in sorted(pick)] + [curve[warm]], sort_keys=False, allow_unicode=True),
                     encoding="utf-8")
    (HERE / "chosen.json").write_text(json.dumps({"warmup": warm, "tasks": pick}, indent=1), encoding="utf-8")
    for t in list(pick) + [warm]:
        for arm in ("question", "outline"):
            for root, reps in ((HERE, REPS), (HERE / "warmup", (1,))):
                for p in reps:
                    if root == HERE and t == warm or root != HERE and t != warm:
                        continue
                    registry(root / arm / "runs" / "cold" / t / f"r{p}" / "registry.sqlite", rs, t)


def calls(arm: str, task: str, rep: int) -> list[str]:
    f = HERE / arm / "runs" / ARMS[arm][0] / task / f"r{rep}" / "calls.log"
    return f.read_text(encoding="utf-8").splitlines() if f.exists() else []


def report() -> None:
    pick = json.loads((HERE / "chosen.json").read_text(encoding="utf-8"))["tasks"]
    rows = collections.defaultdict(lambda: collections.defaultdict(list))
    served = collections.Counter()
    for t, o in pick.items():
        for p in REPS:
            for arm in ARMS:
                r = result(arm, t, p)
                if r and not limited(r):
                    rows[o][arm].append(r["cost_usd"] or 0)
                    if arm != "stock":
                        kinds = [l.split("\t", 1)[0] for l in calls(arm, t, p)]
                        served[(arm, o, "served" if "fold" in kinds else "declined" if "fold-declined" in kinds else "none")] += 1
    print(f"{'outcome':8} {'n':>3}  " + "  ".join(f"{a:>17}" for a in ARMS) + "   (total $, median $)")
    for o in PICK:
        line = f"{o:8} {len(rows[o]['stock']):>3}  "
        for arm in ARMS:
            v = rows[o][arm]
            line += f"  {sum(v):7.3f} {statistics.median(v) if v else 0:8.4f} "
        print(line)
    for o in PICK:
        for arm in ("question", "outline"):
            print(f"{arm:8} {o:6} " + ", ".join(f"{k} {served[(arm, o, k)]}" for k in ("served", "declined", "none")))


def main():
    rs = seeds()
    pred = predicted(rs)
    pick = chosen(pred)
    if "--report" in sys.argv:
        report()
        return
    jobs = [(arm, t, p) for p in REPS for t in sorted(pick) for arm in ARMS]
    if "--dry" in sys.argv:
        print(collections.Counter(pred.values()), "->", collections.Counter(pick.values()))
        print(f"{len(jobs)} jobs + {len(ARMS)} warm-up, about ${0.036 * (len(jobs) + len(ARMS)):.2f}")
        return
    import ctypes
    ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)  # ES_CONTINUOUS | ES_SYSTEM_REQUIRED
    setup(rs, pick)
    log(f"start: {len(pick)} tasks {dict(collections.Counter(pick.values()))}, {len(jobs)} jobs")
    warm = json.loads((HERE / "chosen.json").read_text(encoding="utf-8"))["warmup"]
    with cf.ThreadPoolExecutor(len(ARMS)) as ex:  # the throwaway warm-up, one per arm, together
        for msg in ex.map(lambda a: run(a, warm, 1, HERE / "warmup"), ARMS):
            log(f"warm-up {msg}")
    with cf.ThreadPoolExecutor(WORKERS) as ex:
        for msg in ex.map(lambda j: run(*j), jobs):
            log(msg)
    log("done")
    report()


if __name__ == "__main__":
    main()

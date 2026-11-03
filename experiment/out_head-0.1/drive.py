"""head-0.1: lookup cost on popular reference pages, no registry, two at a time.

  python out_head-0.1/drive.py            # cold-nowrite and cold-nowrite-related, reps 1-2
  python out_head-0.1/drive.py reuse      # also cold, then warm-same-nowrite and warm-related-nowrite
  python out_head-0.1/drive.py --rebuild  # only rebuild results.jsonl

Tasks are tasks_head.yaml: 24 canonical reference pages of widely used technologies, two
facts each. Finished runs are skipped, so rerunning resumes. A run that hits the usage limit
is retried every 15 minutes.
"""
import json, pathlib, subprocess, sys, threading, time, datetime

import yaml

HERE = pathlib.Path(__file__).parent
EXP = HERE.parent
TASKS = EXP / "tasks_head.yaml"
PY = sys.executable
WAIT = 15 * 60
REPS = (1, 2)
lock = threading.Lock()


def log(msg: str) -> None:
    with lock, open(HERE / "drive.log", "a", encoding="utf-8") as f:
        f.write(f"{datetime.datetime.now():%m-%d %H:%M:%S} {msg}\n")


def result(cond: str, task: str, rep: int) -> dict | None:
    try:
        return json.loads((HERE / "runs" / cond / task / f"r{rep}" / "result.json").read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return None


def limited(r: dict) -> bool:
    return r["exit_code"] != 0 and "limit" in r["answer"].lower() and "hit your" in r["answer"].lower()


def stream(name: str, jobs: list[tuple[str, str, int]]) -> None:
    for cond, task, rep in jobs:
        r = result(cond, task, rep)
        while r is None or limited(r):
            subprocess.run([PY, "run.py", cond, "--task", task, "--rep", str(rep), "--tasks", str(TASKS),
                            "--iteration", "miss-0.7", "--out", str(HERE)], cwd=EXP,
                           stdin=subprocess.DEVNULL, capture_output=True)
            r = result(cond, task, rep)
            if r is None:
                log(f"{name}: {cond} {task} r{rep} left no result.json; retrying in 60 s")
                time.sleep(60)
            elif limited(r):
                log(f"{name}: usage limit at {cond} {task} r{rep} ({r['answer'][:70]}); retrying in 15 min")
                time.sleep(WAIT)
            else:
                log(f"{name}: {cond:22} {task:24} r{rep}  {'OK ' if r['correct'] else 'BAD'} "
                    f"{r['usage']['total']:>7}")


def phase(jobs: list) -> None:
    a, b = jobs[0::2], jobs[1::2]
    ts = [threading.Thread(target=stream, args=(n, j)) for n, j in (("A", a), ("B", b))]
    for t in ts:
        t.start()
    for t in ts:
        t.join()


def rebuild() -> None:
    rows = [r for r in (json.loads(p.read_text(encoding="utf-8"))
                        for p in sorted((HERE / "runs").glob("*/*/r*/result.json"))) if not limited(r)]
    (HERE / "results.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    log(f"results.jsonl rebuilt: {len(rows)} rows")


def main():
    if "--rebuild" not in sys.argv:
        ids = [t["id"] for t in yaml.safe_load(TASKS.read_text(encoding="utf-8"))]
        log(f"start: {len(ids)} tasks, reps {REPS}")
        phase([(c, t, r) for r in REPS for t in ids for c in ("cold-nowrite", "cold-nowrite-related")])
        if "reuse" in sys.argv:  # cold writes, then read-only reuse of its registry
            phase([("cold", t, r) for r in REPS for t in ids])
            phase([(c, t, r) for r in REPS for t in ids for c in ("warm-same-nowrite", "warm-related-nowrite")])
    rebuild()


if __name__ == "__main__":
    main()

"""firecrawl-0.1 on the hard set: four runs per task, 1 rep (LOG, 2026-11-10).

  python out_firecrawl-0.1/drive.py           # run the tasks not yet run
  python out_firecrawl-0.1/drive.py --dry     # list the jobs; runs nothing

Per task, in order:
  source  noregistry on the Firecrawl-backed tool (original question); its trace builds the card
  tool    noregistry-related on the Firecrawl-backed tool (arm 2)
  fold    warm-related-nowrite --iteration fold-0.1 on the Firecrawl-backed tool (arm 3)
  stock   noregistry-related on the stock firecrawl-mcp server (arm 1), in stock/
Each job records the account's credits before and after (stock runs log no per-call credits).
Stops before a job if this batch has spent more than BUDGET credits.
"""
import json, pathlib, subprocess, sys, time

import httpx

HERE = pathlib.Path(__file__).parent
EXP = HERE.parent
sys.path.insert(0, str(EXP))
from bc.common import _firecrawl_key

PY = str(EXP.parent / ".venv" / "Scripts" / "python.exe")
TASKS = ["bash-histsize", "gha-matrix-max-jobs", "git-gc-auto", "heroku-daily-restart", "mdn-fetch-credentials",
         "nginx-keepalive-requests", "render-free-spindown", "rust-vec-extract-if", "sonatype-guava"]
BUDGET = 400
LOG = HERE / "drive.log"


def credits() -> int:
    r = httpx.get("https://api.firecrawl.dev/v2/team/credit-usage", timeout=30,
                  headers={"Authorization": f"Bearer {_firecrawl_key()}"})
    return r.json()["data"]["remainingCredits"]


def log(msg: str) -> None:
    line = time.strftime("%m-%d %H:%M:%S ") + msg
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def jobs(t: str) -> list[tuple[str, list[str], pathlib.Path]]:
    a = ["--tasks", str(EXP / "tasks.yaml"), "--task", t]
    fw = a + ["--out", str(HERE), "--backend", "firecrawl"]
    return [("source", ["noregistry", *fw], HERE / "runs/noregistry" / t / "r1"),
            ("tool", ["noregistry-related", *fw], HERE / "runs/noregistry-related" / t / "r1"),
            ("fold", ["warm-related-nowrite", *fw, "--iteration", "fold-0.1"], HERE / "runs/warm-related-nowrite" / t / "r1"),
            ("stock", ["noregistry-related", *a, "--out", str(HERE / "stock"), "--backend", "firecrawl-mcp"],
             HERE / "stock/runs/noregistry-related" / t / "r1")]


def main():
    dry = "--dry" in sys.argv
    start = None if dry else credits()
    if start is not None:
        log(f"start: {start} credits remaining, budget {BUDGET}")
    for t in TASKS:
        for name, args, run_dir in jobs(t):
            if (run_dir / "result.json").exists():
                continue
            if dry:
                print(t, name, " ".join(args))
                continue
            before = credits()
            if start - before > BUDGET:
                log(f"stopping: {start - before} credits spent, over the budget of {BUDGET}")
                return
            p = subprocess.run([PY, str(EXP / "run.py"), *args], cwd=EXP, capture_output=True, encoding="utf-8",
                               errors="replace")
            out = (p.stdout.strip().splitlines() or [p.stderr.strip()[-300:]])[-1]
            log(f"{t:26} {name:6} {credits() - before:+d} cr | {out[:200]}")
            if name == "source":
                src = run_dir / "stream.jsonl"
                reg = HERE / "runs/cold" / t / "r1" / "registry.sqlite"
                b = subprocess.run([PY, str(EXP / "out_trace-0.1" / "build.py"), str(src), str(reg)], cwd=EXP,
                                   capture_output=True, encoding="utf-8", errors="replace")
                log(f"{t:26} card   {b.stdout.strip().splitlines()[-1] if b.stdout.strip() else b.stderr[-200:]}")
    if not dry:
        log(f"done: {start - credits()} credits spent")


if __name__ == "__main__":
    main()

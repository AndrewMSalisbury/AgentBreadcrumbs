"""card-0.1: route cards in front of stock firecrawl-mcp's scrape, against stock (LOG, 2026-11-11).

  python out_card-0.1/drive.py           # run the jobs not yet run
  python out_card-0.1/drive.py --dry     # list the jobs; runs nothing

Cards: firecrawl-0.1's, built from Firecrawl-backed noregistry traces (out_firecrawl-0.1/runs/cold),
copied to runs/cold/<task>/r1 and r2. Per rep and task, in order:
  card   warm-related-nowrite --backend firecrawl-card (bc/firecrawl_card.py)
  stock  noregistry-related --backend firecrawl-mcp, in stock/
The order alternates by rep (card first in r1, stock first in r2), so neither arm always gets the
other's warm tool-definition cache. Baselines r1 (cold) and r2 (warm) for both setups run first.
Each job records the account's credits before and after. Stops past BUDGET credits.
"""
import pathlib, shutil, subprocess, sys, time

import httpx

HERE = pathlib.Path(__file__).parent
EXP = HERE.parent
sys.path.insert(0, str(EXP))
from bc.common import _firecrawl_key

PY = str(EXP.parent / ".venv" / "Scripts" / "python.exe")
TASKS = ["bash-histsize", "gha-matrix-max-jobs", "git-gc-auto", "heroku-daily-restart", "mdn-fetch-credentials",
         "nginx-keepalive-requests", "render-free-spindown", "rust-vec-extract-if", "sonatype-guava"]
REPS = (1, 2)
BUDGET = 300
LOG = HERE / "drive.log"
SRC = EXP / "out_firecrawl-0.1" / "runs" / "cold"


def credits() -> int:
    r = httpx.get("https://api.firecrawl.dev/v2/team/credit-usage", timeout=30,
                  headers={"Authorization": f"Bearer {_firecrawl_key()}"})
    return r.json()["data"]["remainingCredits"]


def log(msg: str) -> None:
    line = time.strftime("%m-%d %H:%M:%S ") + msg
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def seed() -> None:
    for t in TASKS:
        src = SRC / t / "r1" / "registry.sqlite"
        for rep in REPS:
            dst = HERE / "runs" / "cold" / t / f"r{rep}" / "registry.sqlite"
            if src.exists() and not dst.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(src, dst)


def card_job(t: str | None, rep: int):
    a = ["--rep", str(rep), "--out", str(HERE), "--backend", "firecrawl-card"]
    if t is None:
        return "card", ["baseline", *a], HERE / "runs/baseline/baseline" / f"r{rep}"
    a += ["--tasks", str(EXP / "tasks.yaml"), "--task", t]
    return "card", ["warm-related-nowrite", *a], HERE / "runs/warm-related-nowrite" / t / f"r{rep}"


def stock_job(t: str | None, rep: int):
    a = ["--rep", str(rep), "--out", str(HERE / "stock"), "--backend", "firecrawl-mcp"]
    if t is None:
        return "stock", ["baseline", *a], HERE / "stock/runs/baseline/baseline" / f"r{rep}"
    a += ["--tasks", str(EXP / "tasks.yaml"), "--task", t]
    return "stock", ["noregistry-related", *a], HERE / "stock/runs/noregistry-related" / t / f"r{rep}"


def jobs():
    for rep in REPS:  # baselines: r1 cold, r2 right after it (warm)
        yield None, card_job(None, rep)
    for rep in REPS:
        yield None, stock_job(None, rep)
    for rep in REPS:
        for t in TASKS:
            pair = (card_job(t, rep), stock_job(t, rep))
            for j in pair if rep % 2 else pair[::-1]:
                yield t, j


def main():
    dry = "--dry" in sys.argv
    if not dry:
        seed()
    start = None if dry else credits()
    if start is not None:
        log(f"start: {start} credits remaining, budget {BUDGET}")
    for t, (name, args, run_dir) in jobs():
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
        log(f"{t or 'baseline':26} {name:6} {credits() - before:+d} cr | {out[:200]}")
    if not dry:
        log(f"done: {start - credits()} credits spent")


if __name__ == "__main__":
    main()

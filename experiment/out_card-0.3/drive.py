"""card-0.3: a section route also served when the agent scrapes the page the route reads (LOG, 2026-11-11).

  python out_card-0.3/drive.py           # run the jobs not yet run
  python out_card-0.3/drive.py --dry     # list the jobs; runs nothing

Arm card: warm-related-nowrite --backend firecrawl-card --iteration card-0.3 with firecrawl-0.1's
cards (card/). Of the 9 hard tasks only gha's related question scrapes a page a section route reads
without the card's own page (workflow-syntax, the matrix question's route page), so card-0.3 runs gha
only, r1-r2; on the other 8 it behaves as card-0.2. Stock is card-0.1/0.2's 3 reps; baselines are
card-0.1's. Stops past BUDGET credits.
"""
import pathlib, shutil, subprocess, sys, time

import httpx

HERE = pathlib.Path(__file__).parent
EXP = HERE.parent
sys.path.insert(0, str(EXP))
from bc.common import _firecrawl_key

PY = str(EXP.parent / ".venv" / "Scripts" / "python.exe")
TASKS = ["gha-matrix-max-jobs"]
BUDGET = 40
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
    """card/: firecrawl-0.1's cards."""
    for t in TASKS:
        src = SRC / t / "r1" / "registry.sqlite"
        for rep in (1, 2):
            dst = HERE / "card" / "runs" / "cold" / t / f"r{rep}" / "registry.sqlite"
            if not dst.exists() and src.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(src, dst)


def warm(arm: str, t: str, rep: int):
    args = ["warm-related-nowrite", "--rep", str(rep), "--out", str(HERE / arm), "--backend", "firecrawl-card",
            "--iteration", "card-0.3", "--tasks", str(EXP / "tasks.yaml"), "--task", t]
    return arm, args, HERE / arm / "runs/warm-related-nowrite" / t / f"r{rep}"


def jobs():
    for t in TASKS:
        for rep in (1, 2):
            yield t, warm("card", t, rep)


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
        log(f"{t:26} {name:10} {credits() - before:+d} cr | {out[:200]}")
    if not dry:
        log(f"done: {start - credits()} credits spent")


if __name__ == "__main__":
    main()

"""card-0.2 and a prompt-only arm, against card-0.1's runs and stock (LOG, 2026-11-11).

  python out_card-0.2/drive.py           # run the jobs not yet run
  python out_card-0.2/drive.py --dry     # list the jobs; runs nothing

Arms, all the related question:
  promptonly  warm-related-nowrite --backend firecrawl-card --iteration card-0.2 with an empty
              registry (promptonly/): the card arm's prompt line and wrapper, no cards. 9 tasks, r1-r2.
  card        the same with firecrawl-0.1's cards (card/): rust only, the one task where card-0.2
              differs from card-0.1 (its route is another URL with no section). r1-r2.
  stock       noregistry-related --backend firecrawl-mcp (stock/), rep 3, adding to card-0.1's r1-r2.
Per task the order is promptonly r1, stock r3, promptonly r2. Baselines are card-0.1's: same
servers and prompts. Stops past BUDGET credits.
"""
import pathlib, shutil, sqlite3, subprocess, sys, time

import httpx

HERE = pathlib.Path(__file__).parent
EXP = HERE.parent
sys.path.insert(0, str(EXP))
from bc.common import _firecrawl_key

PY = str(EXP.parent / ".venv" / "Scripts" / "python.exe")
TASKS = ["bash-histsize", "gha-matrix-max-jobs", "git-gc-auto", "heroku-daily-restart", "mdn-fetch-credentials",
         "nginx-keepalive-requests", "render-free-spindown", "rust-vec-extract-if", "sonatype-guava"]
BUDGET = 250
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
    """card/: firecrawl-0.1's cards; promptonly/: the same registries with every row deleted."""
    for t in TASKS:
        src = SRC / t / "r1" / "registry.sqlite"
        for rep in (1, 2):
            for arm in ("card", "promptonly"):
                dst = HERE / arm / "runs" / "cold" / t / f"r{rep}" / "registry.sqlite"
                if dst.exists():
                    continue
                dst.parent.mkdir(parents=True, exist_ok=True)
                if src.exists():
                    shutil.copy(src, dst)
                if arm == "promptonly":
                    with sqlite3.connect(dst) as db:
                        for (table,) in db.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall():
                            db.execute(f'DELETE FROM "{table}"')


def warm(arm: str, t: str, rep: int):
    args = ["warm-related-nowrite", "--rep", str(rep), "--out", str(HERE / arm), "--backend", "firecrawl-card",
            "--iteration", "card-0.2", "--tasks", str(EXP / "tasks.yaml"), "--task", t]
    return arm, args, HERE / arm / "runs/warm-related-nowrite" / t / f"r{rep}"


def stock(t: str, rep: int):
    args = ["noregistry-related", "--rep", str(rep), "--out", str(HERE / "stock"), "--backend", "firecrawl-mcp",
            "--tasks", str(EXP / "tasks.yaml"), "--task", t]
    return "stock", args, HERE / "stock/runs/noregistry-related" / t / f"r{rep}"


def jobs():
    for t in TASKS:
        yield t, warm("promptonly", t, 1)
        yield t, stock(t, 3)
        yield t, warm("promptonly", t, 2)
    for rep in (1, 2):
        yield "rust-vec-extract-if", warm("card", "rust-vec-extract-if", rep)


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

"""Rust third question, reps 2-3 of each arm: does the note naming ExtractIf.html cause long runs? (LOG 2026-11-11)

  python out_card-0.4/drive_rust.py [--dry]

card: card-0.4 (on rust the same as card-0.3: the route is another URL with no section, so the
reply names it) into out_card-0.4/card; stock into out_card-0.3/stock, after third-0.1's r1 of each.
A baseline runs first to warm the prompt cache.
"""
import pathlib, shutil, subprocess, sys, time

import httpx

HERE = pathlib.Path(__file__).parent
EXP = HERE.parent
sys.path.insert(0, str(EXP))
from bc.common import _firecrawl_key

PY = str(EXP.parent / ".venv" / "Scripts" / "python.exe")
SECTION = ["gha-matrix-max-jobs", "git-gc-auto", "mdn-fetch-credentials"]
OTHER = ["bash-histsize", "heroku-daily-restart", "nginx-keepalive-requests", "render-free-spindown",
         "rust-vec-extract-if", "sonatype-guava"]
BUDGET = 60
LOG = HERE / "drive_rust.log"
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
    for t in SECTION + OTHER:
        src = SRC / t / "r1" / "registry.sqlite"
        for rep in (1, 2, 3):
            dst = HERE / "card" / "runs" / "cold" / t / f"r{rep}" / "registry.sqlite"
            if not dst.exists() and src.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(src, dst)


def card(t: str | None, rep: int):
    cond = "warm-third-nowrite" if t else "baseline"
    args = [cond, "--rep", str(rep), "--out", str(HERE / "card"), "--backend", "firecrawl-card",
            "--iteration", "card-0.4", "--tasks", str(EXP / "tasks.yaml")] + (["--task", t] if t else [])
    return "card", args, HERE / "card/runs" / cond / (t or "baseline") / f"r{rep}"


def stock(t: str | None, rep: int):
    cond = "noregistry-third" if t else "baseline"
    args = [cond, "--rep", str(rep), "--out", str(HERE.parent / "out_card-0.3" / "stock"), "--backend", "firecrawl-mcp",
            "--tasks", str(EXP / "tasks.yaml")] + (["--task", t] if t else [])
    return "stock", args, HERE.parent / "out_card-0.3" / "stock/runs" / cond / (t or "baseline") / f"r{rep}"


def jobs():
    t = "rust-vec-extract-if"
    yield "baseline", card(None, 2)
    yield t, card(t, 2)
    yield t, stock(t, 2)
    yield t, stock(t, 3)
    yield t, card(t, 3)


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
        log(f"{t:26} {name:6} {credits() - before:+d} cr | {out[:200]}")
    if not dry:
        log(f"done: {start - credits()} credits spent")


if __name__ == "__main__":
    main()

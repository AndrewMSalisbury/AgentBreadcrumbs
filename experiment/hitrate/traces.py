"""curve-0.1, step 1: one stock run per real question on the local fetch, for trace cards (LOG 2026-11-11).

  python hitrate/traces.py --dry          # the tasks and runs
  python hitrate/traces.py [--site gha] [--out out_curve-0.1]   # runs what is missing, WORKERS at a time

Each of the site's Stack Overflow questions (hitrate/questions.jsonl; the title is the question,
ungraded) runs once under `noregistry`: web tools (fetch, render, WebSearch), no registry, no
lookup step, local fetch, so no Firecrawl credits. Task ids are opaque (t + 8 hex of a hash) since a
run's working directory carries its id and the agent can see it (reach-0.1). The traces then become
trace cards (out_trace-0.1/build.py) in hitrate/score.py.
"""
import concurrent.futures as cf, hashlib, json, pathlib, subprocess, sys

HERE = pathlib.Path(__file__).resolve().parent
EXP = HERE.parent
PY = str(EXP.parent / ".venv" / "Scripts" / "python.exe")
OUT = EXP / (sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else "out_curve-0.1")  # curve-0.2 (mdn): out_curve-0.2
WORKERS = 4


def opaque(answer_id: int) -> str:
    return "t" + hashlib.sha1(f"curve-{answer_id}".encode()).hexdigest()[:8]


def tasks(site: str) -> list[dict]:
    rows = [json.loads(l) for l in (HERE / "questions.jsonl").read_text(encoding="utf-8").splitlines()]
    return [{"id": opaque(r["answer_id"]), "set": "curve", "use_case": "docs", "question": r["title"], "expect": ["."],
             "answer_id": r["answer_id"]} for r in rows if r["site"] == site]


def run(t: dict) -> str:
    run_dir = OUT / "runs/noregistry" / t["id"] / "r1"
    if (run_dir / "result.json").exists():
        return f"{t['id']} done before"
    p = subprocess.run([PY, str(EXP / "run.py"), "noregistry", "--rep", "1", "--out", str(OUT), "--tasks",
                        str(OUT / "tasks.yaml"), "--task", t["id"]], cwd=EXP, capture_output=True, encoding="utf-8",
                       errors="replace")
    return (p.stdout.strip().splitlines() or [p.stderr.strip()[-200:]])[-1][:160]


def main():
    site = sys.argv[sys.argv.index("--site") + 1] if "--site" in sys.argv else "gha"
    ts = tasks(site)
    import yaml
    OUT.mkdir(exist_ok=True)
    (OUT / "tasks.yaml").write_text(yaml.safe_dump([{k: v for k, v in t.items() if k != "answer_id"} for t in ts],
                                                   sort_keys=False, allow_unicode=True), encoding="utf-8")
    (OUT / "ids.json").write_text(json.dumps({t["id"]: t["answer_id"] for t in ts}, indent=0), encoding="utf-8")
    if "--dry" in sys.argv:
        print(f"{len(ts)} tasks for {site}, e.g. {ts[0]['id']}: {ts[0]['question']}")
        return
    with cf.ThreadPoolExecutor(WORKERS) as ex:
        for line in ex.map(run, ts):
            print(line, flush=True)


if __name__ == "__main__":
    main()

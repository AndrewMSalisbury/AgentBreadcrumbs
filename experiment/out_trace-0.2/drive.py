"""trace-0.2: trace cards without start offsets, plus agent-written site records only.

  python out_trace-0.2/drive.py           # verify the answer keys, then run everything
  python out_trace-0.2/drive.py --dry     # count the jobs and estimate their cost; runs nothing
  python out_trace-0.2/drive.py --rebuild # only rebuild every folder's results.jsonl

Step 2 (out_miss-0.12) found trace cards match agent-written ones on related reuse with no write
cost, but lose where an agent writes a URL pattern (curl) and where the card's start offset,
which found the first question's answer, sends a later question to the wrong place (systemd,
vim, sqlite). This changes both and measures each on its own.

Tasks: step 2's 30 (head-0.1's two-call and three+ pages, the 9 hard multi-fetch tasks), reps 1-2.
Phase 1, task by task: same-day cold-nowrite and cold-nowrite-related, and cold under trace-0.2
  (miss-0.13's site-record note only; write refuses page cards), all here.
Build: from each cold-nowrite run, a v1 card (step 2's, into v1/) and a lean card (no start
  offset, into v2/); from each trace-0.2 cold run, a lean card merged into its own registry,
  next to any site record the agent wrote (the agent's registry is kept as registry.agent.sqlite).
Phase 2: warm-related-nowrite on all three registries.
Two runs at a time, finished runs are skipped so rerunning resumes, a run that hits the usage
limit is retried every 15 minutes (head-0.1's driver), and Windows is kept from idle sleep (a
closed lid still sleeps it).
"""
import ctypes, importlib.util, json, pathlib, shutil, statistics, subprocess, sys

HERE = pathlib.Path(__file__).parent
EXP = HERE.parent
spec = importlib.util.spec_from_file_location("drive", EXP / "out_head-0.1" / "drive.py")
d = importlib.util.module_from_spec(spec)
spec.loader.exec_module(d)
d.HERE = HERE  # drive.log goes here
sys.path.insert(0, str(EXP / "out_trace-0.1"))
from build import build

IT = "trace-0.2"
DIRS = {"base": HERE, "v1": HERE / "v1", "v2": HERE / "v2"}
TWO_CALLS = ["flask-config", "git-rebase", "k8s-probes", "mdn-set-cookie", "pandas-read-csv",
             "pg-connections", "pg-numeric", "py-argparse", "py-subprocess", "redis-set"]
THREE_PLUS = ["cargo-manifest", "curl-manpage", "npm-package-json", "pytest-reference", "apache-core",
              "haproxy-config", "linux-tcp7", "rsync-manpage", "sqlite-pragma", "systemd-exec", "vim-options"]
HARD_MULTI = ["bash-histsize", "gha-matrix-max-jobs", "git-gc-auto", "heroku-daily-restart", "mdn-fetch-credentials",
              "nginx-keepalive-requests", "render-free-spindown", "rust-vec-extract-if", "sonatype-guava"]
TASKS = {**{t: EXP / "tasks_head.yaml" for t in TWO_CALLS + THREE_PLUS}, **{t: EXP / "tasks.yaml" for t in HARD_MULTI}}
REPS = (1, 2)
POINTS_PER_DOLLAR = 7  # 5-hour meter, out_meter-0.1; a weekly point is about 8 of these


def run_dir(where, cond, task, rep):
    return DIRS[where] / "runs" / cond / task / f"r{rep}"


def result(where, cond, task, rep):
    try:
        return json.loads((run_dir(where, cond, task, rep) / "result.json").read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return None


def stream(name, jobs):
    """head-0.1's stream, with each job's folder and task file."""
    for where, cond, task, rep in jobs:
        r = result(where, cond, task, rep)
        while r is None or d.limited(r):
            subprocess.run([d.PY, "run.py", cond, "--task", task, "--rep", str(rep), "--tasks", str(TASKS[task]),
                            "--iteration", IT, "--out", str(DIRS[where])],
                           cwd=EXP, stdin=subprocess.DEVNULL, capture_output=True)
            r = result(where, cond, task, rep)
            if r is None:
                d.log(f"{name}: {where} {cond} {task} r{rep} left no result.json; retrying in 60 s")
                d.time.sleep(60)
            elif d.limited(r):
                d.log(f"{name}: usage limit at {where} {cond} {task} r{rep} ({r['answer'][:70]}); retrying in 15 min")
                d.time.sleep(d.WAIT)
            else:
                d.log(f"{name}: {where:4} {cond:22} {task:26} r{rep}  {'OK ' if r['correct'] else 'BAD'} "
                      f"{r['usage']['total']:>7}  ${r['cost_usd'] or 0:.3f}")


def phase(jobs):
    a, b = jobs[0::2], jobs[1::2]
    ts = [d.threading.Thread(target=stream, args=(n, j)) for n, j in (("A", a), ("B", b))]
    for t in ts:
        t.start()
    for t in ts:
        t.join()


def phase1():
    return [("base", c, t, r) for r in REPS for t in TASKS for c in ("cold-nowrite", "cold-nowrite-related", "cold")]


def cards():
    for r in REPS:
        for t in TASKS:
            nw = run_dir("base", "cold-nowrite", t, r) / "stream.jsonl"
            for where, lean in (("v1", False), ("v2", True)):
                reg = run_dir(where, "cold", t, r) / "registry.sqlite"
                if nw.exists() and not reg.exists():
                    d.log(f"{where} {t} r{r}: {build(nw, reg, lean=lean)}")
            cold = run_dir("base", "cold", t, r)
            if (cold / "result.json").exists() and not (cold / "registry.agent.sqlite").exists():
                shutil.copy(cold / "registry.sqlite", cold / "registry.agent.sqlite")
                d.log(f"trace-0.2 {t} r{r}: {build(cold / 'stream.jsonl', cold / 'registry.sqlite', lean=True, merge=True)}")


def phase2():
    return [(w, "warm-related-nowrite", t, r) for r in REPS for t in TASKS for w in DIRS
            if (run_dir(w, "cold", t, r) / "registry.sqlite").exists()]


def rebuild():
    for f in DIRS.values():
        if (f / "runs").exists():
            d.HERE = f
            d.rebuild()
    d.HERE = HERE


def dry():
    """Each job at the mean cost of the same (condition, task) in step 2's runs."""
    prior = {}
    for p in ("out_miss-0.12", "out_miss-0.14", "out_trace-0.1"):
        for l in (EXP / p / "results.jsonl").read_text(encoding="utf-8").splitlines():
            if l.strip() and (r := json.loads(l)).get("cost_usd") is not None:
                prior.setdefault((r["condition"], r["task"]), []).append(r["cost_usd"])
    p1 = phase1()
    p2 = [(w, "warm-related-nowrite", t, r) for r in REPS for t in TASKS for w in DIRS]
    total = 0.0
    for name, js in (("phase 1", p1), ("phase 2", p2)):
        s = sum(statistics.mean(prior[(c, t)]) for _, c, t, _ in js)
        print(f"{name:10}{len(js):>5} runs  ${s:6.2f}")
        total += s
    print(f"{'total':10}{len(p1) + len(p2):>5} runs  ${total:6.2f}  ~{total * POINTS_PER_DOLLAR / 8:.0f} weekly points")


def verify():
    ok = True
    for t, f in TASKS.items():
        p = subprocess.run([d.PY, "run.py", "verify", "--task", t, "--tasks", str(f)], cwd=EXP,
                           capture_output=True, encoding="utf-8", errors="replace")
        if p.returncode:
            print(p.stdout.strip())
            ok = False
    return ok


def main():
    if "--dry" in sys.argv:
        dry()
        return
    if "--rebuild" not in sys.argv:
        if not verify():
            sys.exit("answer keys failed verify (above); fix them, or rerun if a fetch only timed out")
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)  # ES_CONTINUOUS | ES_SYSTEM_REQUIRED
        jobs = phase1()
        d.log(f"start phase 1: {len(TASKS)} tasks, {IT}, reps {REPS}: {len(jobs)} runs")
        phase(jobs)
        cards()
        jobs = phase2()
        d.log(f"start phase 2: {len(jobs)} reuse runs")
        phase(jobs)
    rebuild()


if __name__ == "__main__":
    main()

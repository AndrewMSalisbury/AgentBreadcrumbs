"""Step 2, paired: the card bar and trace-built cards, on the pages where they matter.

  python out_miss-0.12/drive.py           # verify the answer keys, then run everything
  python out_miss-0.12/drive.py --dry     # list the jobs and estimate their cost; runs nothing
  python out_miss-0.12/drive.py --rebuild # only rebuild every folder's results.jsonl

Rewritten 2026-11-08 from the two-arm design (miss-0.13 against miss-0.14 cold, 414 runs). Under
miss-0.13 and miss-0.14 nothing mentions the bar until a fetch passes it, so the two run alike up
to the second web call, and bar 3 can be read off each miss-0.14 cold run (bar3.py) instead of
run as a second cold arm. Each run is then compared with its own counterfactual.

Tasks: head-0.1's two-call and three+ pages and the hard set's 9 multi-fetch tasks.
Phase 1, reps 1-2, task by task: same-day cold-nowrite and cold-nowrite-related (here), cold under
  miss-0.14 (out_miss-0.14), and noregistry-related at rep 1 (here), the related question's cost
  with no registry at all.
Build: a trace card from each cold-nowrite run (out_trace-0.1/build.py, into out_trace-0.1), and,
  for each miss-0.14 cold run whose page card bar 3 refuses but which also stored a site record,
  its registry without the page cards (out_miss-0.14_bar3).
Phase 2: warm-related-nowrite on every miss-0.14 cold run that stored a record, on each stripped
  registry and on every trace registry; plus the API site records miss-0.13 stored on the 5
  one-fetch API tasks (out_miss-0.13), with same-day cold-nowrite-related runs beside them.
Phase 3: rep 3 of all of the above on the tasks where the bar bites (a rep stored a page card
  that bar 3 refuses).
warm-same is left out: the same question is the caching ceiling and decides nothing here. Two
runs at a time, finished runs are skipped so rerunning resumes, and a run that hits the usage
limit is retried every 15 minutes (head-0.1's driver). Windows is kept from sleeping.
"""
import ctypes, importlib.util, json, pathlib, shutil, sqlite3, statistics, subprocess, sys

HERE = pathlib.Path(__file__).parent
EXP = HERE.parent
spec = importlib.util.spec_from_file_location("drive", EXP / "out_head-0.1" / "drive.py")
d = importlib.util.module_from_spec(spec)
spec.loader.exec_module(d)
d.HERE = HERE  # drive.log goes here
sys.path.insert(0, str(HERE))
from bar3 import classify

IT = "miss-0.14"
DIRS = {"base": HERE, "card": EXP / "out_miss-0.14", "bar3": EXP / "out_miss-0.14_bar3",
        "trace": EXP / "out_trace-0.1", "api": EXP / "out_miss-0.13"}
TWO_CALLS = ["flask-config", "git-rebase", "k8s-probes", "mdn-set-cookie", "pandas-read-csv",
             "pg-connections", "pg-numeric", "py-argparse", "py-subprocess", "redis-set"]
THREE_PLUS = ["cargo-manifest", "curl-manpage", "npm-package-json", "pytest-reference",
              # added 2026-11-04, screened at 3+ web calls in out_head-0.2 (rep 1)
              "apache-core", "haproxy-config", "linux-tcp7", "rsync-manpage", "sqlite-pragma", "systemd-exec",
              "vim-options"]
HARD_MULTI = ["bash-histsize", "gha-matrix-max-jobs", "git-gc-auto", "heroku-daily-restart", "mdn-fetch-credentials",
              "nginx-keepalive-requests", "render-free-spindown", "rust-vec-extract-if", "sonatype-guava"]
API = ["terraform-aws-provider", "galaxy-community-general", "artifacthub-cert-manager", "puppet-stdlib",
       "jetbrains-rainbow-brackets"]
TASKS = {**{t: EXP / "tasks_head.yaml" for t in TWO_CALLS + THREE_PLUS}, **{t: EXP / "tasks.yaml" for t in HARD_MULTI + API}}
STEP = TWO_CALLS + THREE_PLUS + HARD_MULTI
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
                            "--iteration", IT if where != "api" else "miss-0.13", "--out", str(DIRS[where])],
                           cwd=EXP, stdin=subprocess.DEVNULL, capture_output=True)
            r = result(where, cond, task, rep)
            if r is None:
                d.log(f"{name}: {where} {cond} {task} r{rep} left no result.json; retrying in 60 s")
                d.time.sleep(60)
            elif d.limited(r):
                d.log(f"{name}: usage limit at {where} {cond} {task} r{rep} ({r['answer'][:70]}); retrying in 15 min")
                d.time.sleep(d.WAIT)
            else:
                d.log(f"{name}: {where:5} {cond:22} {task:26} r{rep}  {'OK ' if r['correct'] else 'BAD'} "
                      f"{r['usage']['total']:>7}  ${r['cost_usd'] or 0:.3f}")


def phase(jobs):
    a, b = jobs[0::2], jobs[1::2]
    ts = [d.threading.Thread(target=stream, args=(n, j)) for n, j in (("A", a), ("B", b))]
    for t in ts:
        t.start()
    for t in ts:
        t.join()


def phase1(tasks, reps):
    jobs = []
    for r in reps:
        for t in tasks:
            jobs += [("base", "cold-nowrite", t, r), ("base", "cold-nowrite-related", t, r), ("card", "cold", t, r)]
            if r == 1 and t in STEP:
                jobs.append(("base", "noregistry-related", t, r))
    return jobs


def build(tasks, reps):
    """Trace registries from cold-nowrite runs; stripped registries where bar 3 refuses a card."""
    sys.path.insert(0, str(DIRS["trace"]))
    from build import build as trace
    for r in reps:
        for t in tasks:
            reg = run_dir("trace", "cold", t, r) / "registry.sqlite"
            src = run_dir("base", "cold-nowrite", t, r) / "stream.jsonl"
            if src.exists() and not reg.exists():
                d.log(f"trace {t} r{r}: {trace(src, reg)}")
            c = classify(run_dir("card", "cold", t, r))
            if c and c["bar3"] == "refused" and c["sites"]:
                dst = run_dir("bar3", "cold", t, r)
                if not (dst / "registry.sqlite").exists():
                    dst.mkdir(parents=True, exist_ok=True)
                    shutil.copy(run_dir("card", "cold", t, r) / "registry.sqlite", dst / "registry.sqlite")
                    with sqlite3.connect(dst / "registry.sqlite") as db:
                        db.execute("DELETE FROM pages")
                    d.log(f"bar3 {t} r{r}: site record kept, page cards removed")


def phase2(tasks, reps):
    jobs = []
    for r in reps:
        for t in tasks:
            cold = result("card", "cold", t, r)
            if cold and cold["write_results"]["stored"]:
                jobs.append(("card", "warm-related-nowrite", t, r))
            if (run_dir("bar3", "cold", t, r) / "registry.sqlite").exists():
                jobs.append(("bar3", "warm-related-nowrite", t, r))
            if (run_dir("trace", "cold", t, r) / "registry.sqlite").exists():
                jobs.append(("trace", "warm-related-nowrite", t, r))
    return jobs


def api_jobs():
    return [("api", c, t, r) for r in REPS for t in API for c in ("cold-nowrite-related", "warm-related-nowrite")
            if c != "warm-related-nowrite" or (run_dir("api", "cold", t, r) / "registry.sqlite").exists()]


def bites():
    return [t for t in STEP if any((c := classify(run_dir("card", "cold", t, r))) and c["bar3"] == "refused"
                                   for r in REPS)]


def rebuild():
    for f in DIRS.values():
        if (f / "runs").exists():
            d.HERE = f
            d.rebuild()
    d.HERE = HERE


def dry():
    """Each job at the mean cost of the same (condition, task) in earlier runs, else of the condition."""
    prior = {}
    for p in ("out_head-0.1", "out_head-0.2", "out_miss-0.5", "out_miss-0.8", "out_miss-0.13"):
        for l in (EXP / p / "results.jsonl").read_text(encoding="utf-8").splitlines():
            if l.strip() and (r := json.loads(l)).get("cost_usd") is not None:
                prior.setdefault((r["condition"], r["task"]), []).append(r["cost_usd"])
    by_cond = {}
    for (c, _), v in prior.items():
        by_cond.setdefault(c, []).extend(v)
    cost = lambda c, t: statistics.mean(prior.get((c, t)) or prior.get(("cold-nowrite-related" if "related" in c
                                        else "cold-nowrite", t)) or by_cond[c])
    p1 = phase1(STEP, REPS)
    p2 = [(w, "warm-related-nowrite", t, r) for r in REPS for t in STEP for w in ("card", "trace")] + api_jobs()
    p3 = phase1(STEP[:8], (3,)) + [(w, "warm-related-nowrite", t, 3) for t in STEP[:8] for w in ("card", "trace")]
    total, n = 0.0, 0
    for name, js in (("phase 1", p1), ("phase 2 (at most)", p2), ("phase 3 (~8 tasks)", p3)):
        s = sum(cost(c, t) for _, c, t, _ in js)
        print(f"{name:20}{len(js):>5} runs  ${s:6.2f}")
        total, n = total + s, n + len(js)
    print(f"{'total':20}{n:>5} runs  ${total:6.2f}  ~{total * POINTS_PER_DOLLAR:.0f} five-hour points, "
          f"~{total * POINTS_PER_DOLLAR / 8:.0f} weekly points")


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
        jobs = phase1(STEP, REPS)
        d.log(f"start phase 1: {len(STEP)} tasks, {IT}, reps {REPS}: {len(jobs)} runs")
        phase(jobs)
        build(STEP, REPS)
        jobs = phase2(STEP, REPS) + api_jobs()
        d.log(f"start phase 2: {len(jobs)} reuse runs")
        phase(jobs)
        b = bites()
        d.log(f"start phase 3: rep 3 on {len(b)} tasks where bar 3 refuses a card: {', '.join(b)}")
        phase(phase1(b, (3,)))
        build(b, (3,))
        phase(phase2(b, (3,)))
    rebuild()


if __name__ == "__main__":
    main()

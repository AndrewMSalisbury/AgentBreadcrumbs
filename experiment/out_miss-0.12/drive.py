"""Step 2: the card bar on the pages where it matters, miss-0.13 (bar of 3 web calls) against
miss-0.14 (miss-0.9's bar), with same-day baselines. Reps 1-2. Both have miss-0.13's write side
(no note on a miss; the site-record note comes with a fetch that shows an access route). Written
for miss-0.11 and miss-0.12, which differ from them only in that write side.

  python out_miss-0.12/drive.py           # verify the answer keys, then run everything
  python out_miss-0.12/drive.py --dry     # list the jobs and estimate their cost; runs nothing
  python out_miss-0.12/drive.py --rebuild # only rebuild both folders' results.jsonl

Tasks: head-0.1's two-call and three+ pages and the hard set's 9 multi-fetch tasks (as in
miss-0.8). Phase 1 runs, task by task, cold-nowrite and cold-nowrite-related (into
out_miss-0.12; they don't depend on the iteration) beside cold under each iteration (into its
own folder), so both iterations and their baselines share the same hours. Phase 2 runs
warm-same-nowrite and warm-related-nowrite on each cold run that stored a record; one that
stored nothing left an empty registry, so its reuse runs would be the baselines. Two runs at a
time, finished runs are skipped so rerunning resumes, and a run that hits the usage limit is
retried every 15 minutes (head-0.1's driver). Windows is kept from sleeping while it runs.
"""
import ctypes, importlib.util, json, pathlib, statistics, subprocess, sys

import yaml

HERE = pathlib.Path(__file__).parent
EXP = HERE.parent
spec = importlib.util.spec_from_file_location("drive", EXP / "out_head-0.1" / "drive.py")
d = importlib.util.module_from_spec(spec)
spec.loader.exec_module(d)
d.HERE = HERE  # drive.log goes here

ITERATIONS = ("miss-0.13", "miss-0.14")
BASELINES = ("cold-nowrite", "cold-nowrite-related")
WARM = ("warm-same-nowrite", "warm-related-nowrite")
PAIR = dict(zip(WARM, BASELINES))  # --dry: a warm arm with no prior runs is costed as its baseline
TWO_CALLS = ["flask-config", "git-rebase", "k8s-probes", "mdn-set-cookie", "pandas-read-csv",
             "pg-connections", "pg-numeric", "py-argparse", "py-subprocess", "redis-set"]
THREE_PLUS = ["cargo-manifest", "curl-manpage", "npm-package-json", "pytest-reference",
              # added 2026-11-04, screened at 3+ web calls in out_head-0.2 (rep 1)
              "apache-core", "haproxy-config", "linux-tcp7", "rsync-manpage", "sqlite-pragma", "systemd-exec",
              "vim-options"]
HARD_MULTI = ["bash-histsize", "gha-matrix-max-jobs", "git-gc-auto", "heroku-daily-restart", "mdn-fetch-credentials",
              "nginx-keepalive-requests", "render-free-spindown", "rust-vec-extract-if", "sonatype-guava"]
TASKS = {**{t: EXP / "tasks_head.yaml" for t in TWO_CALLS + THREE_PLUS}, **{t: EXP / "tasks.yaml" for t in HARD_MULTI}}
# Earlier runs, for --dry: miss-0.8 had miss-0.13's bar, head-0.1 (miss-0.7) and miss-0.5 had miss-0.14's.
PRIOR = {"miss-0.13": [EXP / "out_miss-0.8"], "miss-0.14": [EXP / "out_head-0.1", EXP / "out_miss-0.5"],
         None: [EXP / "out_head-0.1", EXP / "out_miss-0.5", EXP / "out_head-0.2"]}
POINTS_PER_DOLLAR = 7  # 5-hour meter, out_meter-0.1; a weekly point is about 8 of these


def folder(it, cond):
    return HERE if cond in BASELINES else EXP / f"out_{it}"


def result(it, cond, task, rep):
    try:
        return json.loads((folder(it, cond) / "runs" / cond / task / f"r{rep}" / "result.json").read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return None


def stream(name, jobs):
    """head-0.1's stream, with each job's iteration, folder and task file."""
    for it, cond, task, rep in jobs:
        r = result(it, cond, task, rep)
        while r is None or d.limited(r):
            subprocess.run([d.PY, "run.py", cond, "--task", task, "--rep", str(rep), "--tasks", str(TASKS[task]),
                            "--iteration", it, "--out", str(folder(it, cond))], cwd=EXP,
                           stdin=subprocess.DEVNULL, capture_output=True)
            r = result(it, cond, task, rep)
            if r is None:
                d.log(f"{name}: {it} {cond} {task} r{rep} left no result.json; retrying in 60 s")
                d.time.sleep(60)
            elif d.limited(r):
                d.log(f"{name}: usage limit at {it} {cond} {task} r{rep} ({r['answer'][:70]}); retrying in 15 min")
                d.time.sleep(d.WAIT)
            else:
                d.log(f"{name}: {it:9} {cond:22} {task:24} r{rep}  {'OK ' if r['correct'] else 'BAD'} "
                      f"{r['usage']['total']:>7}  ${r['cost_usd'] or 0:.3f}")


def phase(jobs):
    a, b = jobs[0::2], jobs[1::2]
    ts = [d.threading.Thread(target=stream, args=(n, j)) for n, j in (("A", a), ("B", b))]
    for t in ts:
        t.start()
    for t in ts:
        t.join()


def phase1():
    jobs = []
    for r in d.REPS:
        for t in TASKS:
            jobs += [(ITERATIONS[-1], c, t, r) for c in BASELINES] + [(it, "cold", t, r) for it in ITERATIONS]
    return jobs


def phase2():
    return [(it, c, t, r) for it in ITERATIONS for r in d.REPS for t in TASKS
            if (cold := result(it, "cold", t, r)) and cold["write_results"]["stored"] for c in WARM]


def rebuild():
    for f in [HERE] + [EXP / f"out_{it}" for it in ITERATIONS]:
        d.HERE = f
        d.rebuild()
    d.HERE = HERE


def dry():
    """Each job at the mean cost of the same (condition, task) in earlier runs at the same bar."""
    def rows(dirs):
        out = {}
        for p in dirs:
            for l in (p / "results.jsonl").read_text(encoding="utf-8").splitlines():
                if l.strip() and (r := json.loads(l))["task"] in TASKS and r.get("cost_usd") is not None:
                    out.setdefault((r["condition"], r["task"]), []).append(r)
        return out
    prior = {k: rows(v) for k, v in PRIOR.items()}
    # Pages added on 2026-11-04 have only screened baselines: their cold runs are costed as
    # cold-nowrite (three+ pages wrote at about baseline cost) and assumed to store a card.
    cost = lambda it, c, t: statistics.mean(r["cost_usd"] for r in prior[it if c not in BASELINES else None].get(
        (c, t)) or prior[None][("cold-nowrite", t)])
    total, n = 0.0, 0
    print(f"{'':10}{'runs':>6}{'est. $':>9}")
    p1 = phase1()
    for it in (None,) + ITERATIONS:
        js = [j for j in p1 if (j[1] in BASELINES) == (it is None) and (it is None or j[0] == it)]
        s = sum(cost(it, c, t) for _, c, t, _ in js)
        print(f"{it or 'baselines':10}{len(js):>6}{s:>9.2f}  phase 1")
        total, n = total + s, n + len(js)
    for it in ITERATIONS:  # warm runs at the prior stored rate per task
        colds = {t: prior[it].get(("cold", t)) or [{"write_results": {"stored": [1]}}] for t in TASKS}
        k = sum(2 * len(d.REPS) * statistics.mean(bool(r["write_results"]["stored"]) for r in colds[t]) for t in TASKS)
        s = sum(len(d.REPS) * statistics.mean(bool(r["write_results"]["stored"]) for r in colds[t])
                * sum(statistics.mean(r["cost_usd"] for r in prior[it].get((c, t)) or prior[None][(PAIR[c], t)])
                      for c in WARM) for t in TASKS)
        print(f"{it:10}{k:>6.0f}{s:>9.2f}  phase 2 (expected)")
        total, n = total + s, n + k
    print(f"{'total':10}{n:>6.0f}{total:>9.2f}  ~{total * POINTS_PER_DOLLAR:.0f} five-hour points, "
          f"~{total * POINTS_PER_DOLLAR / 8:.0f} weekly points")



def verify():
    ok = True
    for f in sorted(set(TASKS.values())):
        ids = [t for t in TASKS if TASKS[t] == f]
        for t in ids:
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
        d.log(f"start phase 1: {len(TASKS)} tasks, {', '.join(ITERATIONS)}, reps {d.REPS}: {len(jobs)} runs")
        phase(jobs)
        jobs = phase2()
        d.log(f"start phase 2: {len(jobs)} reuse runs on cold runs that stored a record")
        phase(jobs)
    rebuild()


if __name__ == "__main__":
    main()

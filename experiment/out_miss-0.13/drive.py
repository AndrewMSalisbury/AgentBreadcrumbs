"""miss-0.13 on the pages where the write side only costs: head-0.1's one-call pages and the
hard set's one-fetch API tasks (as miss-0.11), reps 1-2.

  python out_miss-0.13/drive.py           # run everything
  python out_miss-0.13/drive.py --rebuild # only rebuild results.jsonl

Per task and rep: cold under miss-0.13, cold-nowrite (same-day baseline) and noregistry (web
tools only, no lookup step), side by side so the three share the same hours. Two runs at a
time, finished runs are skipped so rerunning resumes, and a run that hits the usage limit is
retried every 15 minutes (head-0.1's driver). Windows is kept from sleeping while it runs.
"""
import ctypes, importlib.util, pathlib, subprocess, sys

HERE = pathlib.Path(__file__).parent
EXP = HERE.parent
spec = importlib.util.spec_from_file_location("drive", EXP / "out_head-0.1" / "drive.py")
d = importlib.util.module_from_spec(spec)
spec.loader.exec_module(d)
d.HERE = HERE  # drive.log and results.jsonl go here

ONE_CALL = ["docker-run", "dockerfile", "gha-events", "go-net-http", "lambda-quotas", "node-child-process",
            "node-fs", "react-useeffect", "tsconfig", "vite-server"]
API = ["terraform-aws-provider", "galaxy-community-general", "artifacthub-cert-manager", "puppet-stdlib",
       "jetbrains-rainbow-brackets"]
TASKS = {**{t: EXP / "tasks_head.yaml" for t in ONE_CALL}, **{t: EXP / "tasks.yaml" for t in API}}
CONDS = ("cold", "cold-nowrite", "noregistry")


def stream(name, jobs):
    for cond, task, rep in jobs:
        r = d.result(cond, task, rep)
        while r is None or d.limited(r):
            subprocess.run([d.PY, "run.py", cond, "--task", task, "--rep", str(rep), "--tasks", str(TASKS[task]),
                            "--iteration", "miss-0.13", "--out", str(HERE)], cwd=EXP,
                           stdin=subprocess.DEVNULL, capture_output=True)
            r = d.result(cond, task, rep)
            if r is None:
                d.log(f"{name}: {cond} {task} r{rep} left no result.json; retrying in 60 s")
                d.time.sleep(60)
            elif d.limited(r):
                d.log(f"{name}: usage limit at {cond} {task} r{rep} ({r['answer'][:70]}); retrying in 15 min")
                d.time.sleep(d.WAIT)
            else:
                d.log(f"{name}: {cond:14} {task:26} r{rep}  {'OK ' if r['correct'] else 'BAD'} "
                      f"{r['usage']['total']:>7}  ${r['cost_usd'] or 0:.3f}")


def main():
    if "--rebuild" in sys.argv:
        d.rebuild()
        return
    ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)  # ES_CONTINUOUS | ES_SYSTEM_REQUIRED
    jobs = [(c, t, rep) for rep in d.REPS for t in TASKS for c in CONDS]
    ts = [d.threading.Thread(target=stream, args=(n, j)) for n, j in (("A", jobs[0::2]), ("B", jobs[1::2]))]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    d.rebuild()
    d.log("done")


if __name__ == "__main__":
    main()

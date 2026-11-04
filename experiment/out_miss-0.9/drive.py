"""miss-0.9+ (page-card instructions deferred to the fetch that passes the bar): cold runs, reps 1-2.

  python out_miss-0.9/drive.py              # miss-0.9 (miss-0.7's bar) into out_miss-0.9/
  python out_miss-0.9/drive.py miss-0.10    # miss-0.10 (bar of 3 web calls) into out_miss-0.10/
  python out_miss-0.9/drive.py miss-0.11 one api   # only head-0.1's one-call pages, then the
                                                   # hard set's one-fetch API tasks

Sets: cheap (head-0.1's one- and two-call pages, the default), one, api. Baselines are
head-0.1's cold-nowrite runs, as in miss-0.8, and miss-0.5's for the API tasks. Uses head-0.1's driver with its
iteration, folder and task file swapped. Windows is kept from sleeping while it runs (sleep
killed two meter-0.1 batches).
"""
import ctypes, importlib.util, pathlib, sys

HERE = pathlib.Path(__file__).parent
spec = importlib.util.spec_from_file_location("drive", HERE.parent / "out_head-0.1" / "drive.py")
d = importlib.util.module_from_spec(spec)
spec.loader.exec_module(d)
d.ITERATION = sys.argv[1] if len(sys.argv) > 1 else "miss-0.9"
d.HERE = HERE.parent / f"out_{d.ITERATION}"
d.HERE.mkdir(exist_ok=True)
ONE_CALL = ["docker-run", "dockerfile", "gha-events", "go-net-http", "lambda-quotas", "node-child-process", "node-fs",
            "react-useeffect", "tsconfig", "vite-server"]
TWO_CALLS = ["flask-config", "git-rebase", "k8s-probes", "mdn-set-cookie", "pandas-read-csv",
             "pg-connections", "pg-numeric", "py-argparse", "py-subprocess", "redis-set"]

API = ["terraform-aws-provider", "galaxy-community-general", "artifacthub-cert-manager", "puppet-stdlib",
       "jetbrains-rainbow-brackets"]
SETS = {"cheap": (d.EXP / "tasks_head.yaml", ONE_CALL + TWO_CALLS), "one": (d.EXP / "tasks_head.yaml", ONE_CALL),
        "api": (d.EXP / "tasks.yaml", API)}

ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)  # ES_CONTINUOUS | ES_SYSTEM_REQUIRED
for name in sys.argv[2:] or ["cheap"]:
    cond = "cold-nowrite" if name.endswith("-nowrite") else "cold"  # e.g. one-nowrite: a same-day baseline
    d.TASKS, ids = SETS[name.removesuffix("-nowrite")]
    d.log(f"start {d.ITERATION} {name}: {len(ids)} tasks from {d.TASKS.name}, reps {d.REPS}")
    d.phase([(cond, t, r) for r in d.REPS for t in ids])
d.rebuild()

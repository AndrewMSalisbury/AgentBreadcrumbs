"""miss-0.8 (3-web-call card bar): cold, then read-only reuse where a card was stored, reps 1-2.

  python out_miss-0.8/drive.py              # head-0.1's two-call pages
  python out_miss-0.8/drive.py expensive    # head-0.1's three+ pages and the 9 hard multi-fetch tasks

Baselines (cold-nowrite, cold-nowrite-related) are the earlier runs: head-0.1's for the head
pages, miss-0.5's for the hard tasks; they don't depend on the iteration. A cold run that
still stores a card gets warm-same-nowrite and warm-related-nowrite on its registry; one that
stores nothing leaves an empty registry, and its reuse runs would be the baselines. Uses
head-0.1's driver with its iteration, folder and task file swapped.
"""
import importlib.util, pathlib, sys

HERE = pathlib.Path(__file__).parent
spec = importlib.util.spec_from_file_location("drive", HERE.parent / "out_head-0.1" / "drive.py")
d = importlib.util.module_from_spec(spec)
spec.loader.exec_module(d)
d.HERE, d.ITERATION = HERE, "miss-0.8"
TWO_CALLS = ["flask-config", "git-rebase", "k8s-probes", "mdn-set-cookie", "pandas-read-csv",
             "pg-connections", "pg-numeric", "py-argparse", "py-subprocess", "redis-set"]
THREE_PLUS = ["cargo-manifest", "curl-manpage", "npm-package-json", "pytest-reference"]
HARD_MULTI = ["bash-histsize", "gha-matrix-max-jobs", "git-gc-auto", "heroku-daily-restart", "mdn-fetch-credentials",
              "nginx-keepalive-requests", "render-free-spindown", "rust-vec-extract-if", "sonatype-guava"]
SETS = {"two": [(d.EXP / "tasks_head.yaml", TWO_CALLS)],
        "expensive": [(d.EXP / "tasks_head.yaml", THREE_PLUS), (d.EXP / "tasks.yaml", HARD_MULTI)]}

for tasks_file, ids in SETS[sys.argv[1] if len(sys.argv) > 1 else "two"]:
    d.TASKS = tasks_file
    d.log(f"start: {len(ids)} tasks from {tasks_file.name}, reps {d.REPS}")
    d.phase([("cold", t, r) for r in d.REPS for t in ids])
    stored = [(t, r) for r in d.REPS for t in ids if d.result("cold", t, r)["write_results"]["stored"]]
    d.log(f"cold runs storing a record: {stored}")
    d.phase([(c, t, r) for t, r in stored for c in ("warm-same-nowrite", "warm-related-nowrite")])
d.rebuild()

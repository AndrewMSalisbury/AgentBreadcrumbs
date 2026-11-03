"""miss-0.8 on head-0.1's two-call pages: cold under a 3-web-call card bar, reps 1-2.

  python out_miss-0.8/drive.py

Baselines (cold-nowrite, cold-nowrite-related) are head-0.1's runs; they don't depend on
the iteration. A cold run that still stores a card gets warm-same-nowrite and
warm-related-nowrite on its registry; one that stores nothing leaves an empty registry,
and its reuse runs would be the baselines. Uses head-0.1's driver with its iteration and folder swapped.
"""
import importlib.util, pathlib

HERE = pathlib.Path(__file__).parent
spec = importlib.util.spec_from_file_location("drive", HERE.parent / "out_head-0.1" / "drive.py")
d = importlib.util.module_from_spec(spec)
spec.loader.exec_module(d)
d.HERE, d.ITERATION = HERE, "miss-0.8"
TWO_CALLS = ["flask-config", "git-rebase", "k8s-probes", "mdn-set-cookie", "pandas-read-csv",
             "pg-connections", "pg-numeric", "py-argparse", "py-subprocess", "redis-set"]


d.log(f"start: {len(TWO_CALLS)} tasks, reps {d.REPS}")
d.phase([("cold", t, r) for r in d.REPS for t in TWO_CALLS])
stored = [(t, r) for r in d.REPS for t in TWO_CALLS if d.result("cold", t, r)["write_results"]["stored"]]
d.log(f"cold runs storing a record: {stored}")
d.phase([(c, t, r) for t, r in stored for c in ("warm-same-nowrite", "warm-related-nowrite")])
d.rebuild()

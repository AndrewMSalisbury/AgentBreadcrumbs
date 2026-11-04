"""meter-0.1 report: plan-meter points per dollar of each token type, from meter.jsonl.

Uses the three clean batches (one start and one settled end reading, no failed runs, no
5-hour reset in between) and solves points = a*cache_write$ + b*cache_read$ + c*output$.
"""
import json, pathlib
from collections import defaultdict
import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
K = ["input", "cache_write", "cache_read", "output"]
CLEAN = {"batch-out-1793740172": None, "batch-write-1793759898": None,
         # started at 53% before the 02:00 reset; its 9 completed runs all fell in the new window, which
         # opened at 02:30 when the machine woke (the 6 failed runs died in sleep), so it is read from 0%
         "batch-read-1793752868": 0.0}

rows = [json.loads(l) for l in open(HERE / "meter.jsonl", encoding="utf-8")]
B = defaultdict(list)
for r in rows:
    B[r["batch"]].append(r)

runs = [r for r in rows if r["event"] == "run" and "usage" in r]
X = np.array([[r["usage"][k] for k in K] for r in runs], float) / 1e6
price = np.linalg.lstsq(X, np.array([r["cost_usd"] for r in runs]), rcond=None)[0]
print("fitted $/Mtok:", dict(zip(K, price.round(3))))

A, y = [], []
print(f"\n{'batch':<24}{'runs':>5}{'$':>7}{'cw $':>7}{'cr $':>7}{'out $':>7}{'5h pts':>8}{'pts/$':>7}{'weekly':>9}")
for b, start in CLEAN.items():
    rs = B[b]
    st, en = rs[0], rs[-1]
    good = [r for r in rs if r["event"] == "run" and "usage" in r]
    d = {k: sum(r["usage"][k] for r in good) * p / 1e6 for k, p in zip(K, price)}
    usd = sum(d.values())
    pts = en["five_hour"] - (st["five_hour"] if start is None else start)
    A.append([d["cache_write"] + d["input"], d["cache_read"], d["output"]])
    y.append(pts)
    print(f"{b:<24}{len(good):>5}{usd:>7.2f}{d['cache_write']:>7.2f}{d['cache_read']:>7.2f}{d['output']:>7.2f}"
          f"{pts:>8.0f}{pts / usd:>7.1f}{st['weekly']:>5.0f}->{en['weekly']:.0f}")

w = np.linalg.solve(np.array(A), np.array(y))
print("\n5-hour points per dollar: cache write/input %.1f, cache read %.1f, output %.1f" % tuple(w))
print("relative to cache writes: cache read x%.2f, output x%.2f" % (w[1] / w[0], w[2] / w[0]))
first, last = rows[0], rows[-1]
print(f"weekly {first['weekly']:.0f} -> {last['weekly']:.0f} over the session")

"""meter-0.1: how a Pro plan's usage meter weights output, cache writes and cache reads.

Three synthetic batches, each dominated by one token type, run on sonnet like the experiments.
After every run it reads the plan meter (the same endpoint /usage shows) and appends a row to
meter.jsonl, so the meter's integer steps can be lined up against cumulative tokens and dollars.

  python drive.py probe              one run of each kind, to check token shapes
  python drive.py batch out|write|read [--max-usd 1.5] [--par 3]

A batch stops when spend passes --max-usd or the weekly meter reaches --weekly-stop. The meter
lags spend and returns 429 if polled often, so a batch reads it only at the start, every sixth
round for the weekly stop, and once settled at the end; the per-run rows carry the tokens. Nothing else should use the account while a batch runs.
"""
import argparse, concurrent.futures as cf, json, pathlib, random, subprocess, time, urllib.error, urllib.request, uuid

HERE = pathlib.Path(__file__).resolve().parent
LOG = HERE / "meter.jsonl"
RUN_DIR = HERE / "rundir"  # empty cwd so no CLAUDE.md leaks in
CREDS = pathlib.Path.home() / ".claude" / ".credentials.json"

VOCAB = ("river stone window garden letter morning paper silver bridge market winter candle orchard "
         "harbor lantern meadow engine pocket ladder thunder blanket compass mirror valley pencil "
         "station basket feather kettle island marble shadow ribbon saddle tunnel violet wagon "
         "anchor beacon cellar donkey fabric glacier hammer jacket kitten lemon magnet needle "
         "oyster parrot quarry rocket sponge timber umbrella velvet walnut yellow zipper").split()


def padding(seed, words=19000):  # ~25k tokens of filler
    r = random.Random(seed)
    lines = [" ".join(r.choice(VOCAB) for _ in range(12)) + "." for _ in range(words // 12)]
    return "Reference notes (ignore them; they are filler).\n" + "\n".join(lines)


PADS = HERE / "pads"  # system prompts go in files: 25k tokens is past Windows' command-line limit


def pad_file(name, text):
    PADS.mkdir(exist_ok=True)
    f = PADS / name
    f.write_text(text, encoding="utf-8")
    return str(f)


FIXED_PAD = pad_file("fixed.txt", padding(1))


def meter():
    for wait in (0, 30, 60, 120, 240, 480):  # the endpoint returns 429 if polled often
        time.sleep(wait)
        try:
            return _meter()
        except urllib.error.HTTPError as e:
            if e.code != 429:
                raise
    return _meter()


def settled():  # the meter lags spend by a minute or more: read until two readings 90 s apart agree
    m = meter()
    while True:
        time.sleep(90)
        n = meter()
        if n["five_hour"] == m["five_hour"]:
            return n
        m = n


def _meter():
    token = json.loads(CREDS.read_text())["claudeAiOauth"]["accessToken"]
    req = urllib.request.Request("https://api.anthropic.com/api/oauth/usage", headers={
        "Authorization": f"Bearer {token}", "anthropic-beta": "oauth-2025-04-20"})
    d = json.load(urllib.request.urlopen(req, timeout=30))
    return {"five_hour": d["five_hour"]["utilization"], "five_hour_resets": d["five_hour"]["resets_at"],
            "weekly": d["seven_day"]["utilization"], "weekly_resets": d["seven_day"]["resets_at"]}


def cmd_for(kind, i):
    base = ["--model", "sonnet", "--output-format", "json", "--setting-sources", "",
            "--strict-mcp-config", "--no-session-persistence", "--permission-mode", "dontAsk"]
    if kind == "out":
        topic = random.Random(i).choice(VOCAB) + " and " + random.Random(i + 7).choice(VOCAB)
        return ["-p", f"Write a story of about 3000 words about a {topic}. Plain prose, no headings.",
                "--system-prompt", "You are a fiction writer.", "--tools", "", "--allowedTools", ""] + base
    if kind == "write":  # a unique prefix, so the whole system prompt is a cache write
        sid = uuid.uuid4()
        return ["-p", "Reply with the single word OK.", "--system-prompt-file",
                pad_file(f"{sid}.txt", f"Session {sid}.\n" + padding(sid.int)), "--tools", "", "--allowedTools", ""] + base
    if kind == "read":  # one fixed prefix re-read on every turn
        return ["-p", "Use the Bash tool to run `echo 1`, then `echo 2`, and so on up to `echo 25`, one command "
                "per tool call, waiting for each result. Say nothing between calls. Then reply DONE.",
                "--system-prompt-file", FIXED_PAD, "--tools", "Bash", "--allowedTools", "Bash(echo:*)"] + base
    raise ValueError(kind)


def run(kind, i):
    RUN_DIR.mkdir(exist_ok=True)
    t0 = time.time()
    try:
        p = subprocess.run(["claude"] + cmd_for(kind, i), cwd=RUN_DIR, stdin=subprocess.DEVNULL, capture_output=True,
                           encoding="utf-8", errors="replace", timeout=900)
    except subprocess.TimeoutExpired as e:  # also raised when the machine sleeps mid-run
        return {"kind": kind, "i": i, "error": f"timeout {e}"[-300:]}
    try:
        res = json.loads(p.stdout)
    except json.JSONDecodeError:
        return {"kind": kind, "i": i, "error": (p.stdout + p.stderr)[-500:]}
    u = {"input": 0, "cache_write": 0, "cache_read": 0, "output": 0}
    for m in res.get("modelUsage", {}).values():
        u["input"] += m.get("inputTokens", 0)
        u["cache_write"] += m.get("cacheCreationInputTokens", 0)
        u["cache_read"] += m.get("cacheReadInputTokens", 0)
        u["output"] += m.get("outputTokens", 0)
    return {"kind": kind, "i": i, "usage": u, "cost_usd": res.get("total_cost_usd"), "turns": res.get("num_turns"),
            "is_error": res.get("is_error"), "result": str(res.get("result"))[:80], "wall_s": round(time.time() - t0, 1),
            "models": list(res.get("modelUsage", {}))}


def log(row):
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")
    print(json.dumps(row), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["probe", "batch", "meter"])
    ap.add_argument("kind", nargs="?")
    ap.add_argument("--max-usd", type=float, default=1.5)
    ap.add_argument("--weekly-stop", type=float, default=88)
    ap.add_argument("--par", type=int, default=3)
    a = ap.parse_args()
    if a.mode == "meter":
        return print(meter())
    kinds = ["out", "write", "read"] if a.mode == "probe" else [a.kind]
    batch = f"{a.mode}-{a.kind or 'all'}-{int(time.time())}"
    m0 = settled()
    log({"batch": batch, "event": "start", **m0, "t": time.time()})
    spent, i = 0.0, 0
    with cf.ThreadPoolExecutor(a.par) as ex:
        while True:
            jobs = [ex.submit(run, k, i + j) for j, k in enumerate(kinds * (1 if a.mode == "probe" else a.par))]
            i += len(jobs)
            for f in jobs:
                r = f.result()
                spent += r.get("cost_usd") or 0
                log({"batch": batch, "event": "run", **r})
            if a.mode == "probe" or spent >= a.max_usd:
                break
            if i % (6 * len(jobs)) == 0 and meter()["weekly"] >= a.weekly_stop:
                break
    log({"batch": batch, "event": "end", **settled(), "spent_usd": round(spent, 4), "t": time.time()})


if __name__ == "__main__":
    main()

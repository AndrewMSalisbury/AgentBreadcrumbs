"""reach-0.1: where agents actually go on real questions, and what each step costs (option 1, PLAN 2026-11-11).

  python hitrate/reach.py --dry        # the sample and the runs
  python hitrate/reach.py              # runs stock firecrawl-mcp on the sample, then reports
  python hitrate/reach.py --report     # report only

hitrate-0.1 found agents search first on real questions and mostly read Stack Overflow, blogs and
GitHub discussions, not the docs pages cards are keyed by. Before keying cards by what agents reach,
this measures it: N questions per site from hitrate/questions.jsonl (random, SEED; none of
validate.py's picks), one stock run each (noregistry --backend firecrawl-mcp; the question is the
Stack Overflow title, ungraded), then every tool call by kind and domain with the size of its result
and its credits, plus the 11 card-arm runs of hitrate-0.1 (out_hitrate-0.1), where the wrapper
served once and otherwise passed calls to stock.

reach-0.2 (the default; `--v1` for reach-0.1's report): reach-0.1 and hitrate-0.1 named each task
so<answer id>, and the run directory, and with it the agent's working directory, carries the task
id. 16 of those 35 runs used the id (a scrape of stackoverflow.com/questions/<id>, or the number in
a search), and the "so" prefix likely sent others to Stack Overflow. reach-0.2 reruns all 35
questions on stock with opaque ids (q + 8 hex of a hash) and reports on those runs alone.
"""
import collections, hashlib, json, pathlib, random, re, subprocess, sys
from urllib.parse import urlsplit

HERE = pathlib.Path(__file__).parent
EXP = HERE.parent
sys.path.insert(0, str(EXP))
from bc.common import _firecrawl_key

N, SEED = 6, 11
V1 = "--v1" in sys.argv
OUT = EXP / ("out_reach-0.1" if V1 else "out_reach-0.2")
PY = str(EXP.parent / ".venv" / "Scripts" / "python.exe")
BUDGET = 120


def opaque(answer_id: int) -> str:
    return "q" + hashlib.sha1(f"reach-{answer_id}".encode()).hexdigest()[:8]


def sample() -> list[dict]:
    rows = [json.loads(l) for l in (HERE / "questions.jsonl").read_text(encoding="utf-8").splitlines()]
    used = set()
    v = EXP / "out_hitrate-0.1" / "validate.json"
    if v.exists():
        used = {r["id"] for r in json.loads(v.read_text(encoding="utf-8"))}
    out, rng = [], random.Random(SEED)
    for site in ("gha", "mdn", "git", "nginx"):
        pool = [r for r in rows if r["site"] == site and f"so{r['answer_id']}" not in used]
        out += rng.sample(pool, N)
    if not V1:  # hitrate-0.1's 11 live questions too
        out += [r for r in rows if f"so{r['answer_id']}" in used]
    return out


def credits() -> int:
    import httpx
    r = httpx.get("https://api.firecrawl.dev/v2/team/credit-usage", timeout=30,
                  headers={"Authorization": f"Bearer {_firecrawl_key()}"})
    return r.json()["data"]["remainingCredits"]


def price(name: str, args: dict) -> int:
    if name.endswith("firecrawl_scrape"):
        q = any(f == "query" or (isinstance(f, dict) and f.get("type") == "query") for f in args.get("formats") or [])
        return 1 + 4 * q
    if name.endswith("firecrawl_search"):
        return 2
    return 0


def kind_of(host: str) -> str:
    if host.endswith("stackoverflow.com") or host.endswith("stackexchange.com") or host.endswith("superuser.com") \
            or host.endswith("serverfault.com"):
        return "stack exchange"
    if host in ("github.com",) or host.endswith(".githubusercontent.com"):
        return "github.com"
    if host in ("docs.github.com", "developer.mozilla.org", "git-scm.com", "nginx.org"):
        return "the site's docs"
    if host.startswith("docs.") or "/docs" in host:
        return "other docs"
    return "other (blogs, etc.)"


def calls(stream: pathlib.Path) -> list[dict]:
    """Each tool call with its result's size, in order."""
    pending, out = {}, []
    for line in stream.read_text(encoding="utf-8").splitlines():
        ev = json.loads(line)
        msg = ev.get("message") if isinstance(ev.get("message"), dict) else {}
        for b in msg.get("content", []) if isinstance(msg.get("content"), list) else []:
            if ev.get("type") == "assistant" and b.get("type") == "tool_use":
                pending[b["id"]] = {"name": b["name"].rsplit("__", 1)[-1], "input": b["input"]}
            if ev.get("type") == "user" and b.get("type") == "tool_result" and b.get("tool_use_id") in pending:
                c = pending.pop(b["tool_use_id"])
                t = b["content"] if isinstance(b["content"], str) else " ".join(x.get("text", "") for x in b["content"])
                c["chars"] = len(t)
                out.append(c)
    return out


def report():
    dirs = sorted((OUT / "runs/noregistry").glob("*/r1"))
    if V1:
        dirs += sorted((EXP / "out_hitrate-0.1/runs/warm-same-nowrite").glob("*/r1"))
    by_kind = collections.defaultdict(lambda: [0, 0, 0])  # calls, chars, credits
    first = collections.Counter()
    hosts = collections.Counter()
    so_ids = collections.Counter()
    search_first, n, cost = 0, 0, 0.0
    for d in dirs:
        cs = calls(d / "stream.jsonl")
        if not (d / "result.json").exists():
            continue
        n += 1
        cost += json.loads((d / "result.json").read_text(encoding="utf-8"))["cost_usd"]
        search_first += bool(cs) and "search" in cs[0]["name"].lower()
        f = next((c for c in cs if c["name"].endswith("scrape")), None)
        first[kind_of(urlsplit(f["input"]["url"]).netloc.lower().removeprefix("www.")) if f else "no scrape"] += 1
        for c in cs:
            url = c["input"].get("url")
            k = "search: " + c["name"] if not url else kind_of(urlsplit(url).netloc.lower().removeprefix("www."))
            if url:
                hosts[urlsplit(url).netloc.lower().removeprefix("www.")] += 1
                if m := re.search(r"stackoverflow\.com/(?:questions|q|a)/(\d+)", url):
                    so_ids[m.group(1)] += 1
            v = by_kind[k]
            v[0] += 1
            v[1] += c.get("chars", 0)
            v[2] += price(c["name"], c["input"])
    print(f"{n} runs ({OUT.name}), ${cost:.2f} in all; first call a search on {search_first}")
    print("first scrape lands on:", dict(first.most_common()))
    print(f"\n{'step':28}{'calls':>7}{'result chars':>14}{'credits':>9}")
    for k, (c, ch, cr) in sorted(by_kind.items(), key=lambda x: -x[1][1]):
        print(f"{k:28}{c:>7}{ch:>14,}{cr:>9}")
    print("\nhosts scraped:", ", ".join(f"{h} {c}" for h, c in hosts.most_common(15)))
    print("Stack Overflow threads scraped more than once across runs:", {k: v for k, v in so_ids.items() if v > 1})


def main():
    if "--report" in sys.argv:
        return report()
    qs = sample()
    tasks = [{"id": f"so{r['answer_id']}" if V1 else opaque(r["answer_id"]), "set": r["site"], "use_case": "docs", "question": r["title"], "expect": ["."]}
             for r in qs]
    import yaml
    OUT.mkdir(exist_ok=True)
    (OUT / "tasks.yaml").write_text(yaml.safe_dump(tasks, sort_keys=False, allow_unicode=True), encoding="utf-8")
    jobs = [("baseline", ["baseline", "--rep", "1"])] + [(t["id"], ["noregistry", "--rep", "1", "--task", t["id"]]) for t in tasks]
    if "--dry" in sys.argv:
        for t in tasks:
            print(f"  {t['set']:6} {t['question'][:90]}")
        return
    start = credits()
    for name, args in jobs:
        run_dir = OUT / "runs" / args[0] / name / "r1"
        if (run_dir / "result.json").exists():
            continue
        if start - credits() > BUDGET:
            print("budget reached")
            break
        subprocess.run([PY, str(EXP / "run.py"), *args, "--out", str(OUT), "--backend", "firecrawl-mcp",
                        "--tasks", str(OUT / "tasks.yaml")], cwd=EXP, capture_output=True)
        print(name, "done", flush=True)
    print(f"credits spent: {start - credits()}")
    report()


if __name__ == "__main__":
    main()

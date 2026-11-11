"""The page an agent starts on, per question: the agent's model asked for the URL it would scrape first.

  python hitrate/start.py validate     # against the first scrapes of the 18 known stock runs' questions
  python hitrate/start.py              # every hitrate/questions.jsonl row -> hitrate/start.json

A card is keyed by the page an agent first scrapes, so a question's start page decides whether a
card can be hit at all. Running a stock agent per question would cost ~5 credits each; instead the
same model (sonnet, as in run.py) is asked, with no tools, for the single URL it would scrape first,
and the guess is checked against what stock agents actually scraped first on the 9 related and 9
third questions (all reps).
"""
import concurrent.futures as cf, json, pathlib, re, subprocess, sys

HERE = pathlib.Path(__file__).parent
EXP = HERE.parent
sys.path.insert(0, str(EXP))
from bc.common import page_id

SYSTEM = ("You answer questions about public web pages using a web scraping tool. Before scraping anything, "
          "reply with only the one URL you would scrape first to answer the question (if you would search "
          "first, the URL you expect the search to lead you to). Reply with the URL and nothing else.")


def guess(question: str) -> str:
    p = subprocess.run(["claude", "-p", question, "--model", "sonnet", "--system-prompt", SYSTEM, "--tools", "",
                        "--output-format", "json"], capture_output=True, encoding="utf-8", errors="replace", timeout=180)
    try:
        text = json.loads(p.stdout)["result"]
    except Exception:
        return ""
    m = re.search(r"https?://\S+", text)
    return m.group(0).rstrip(").,>`'\"") if m else ""


def first_scrapes(stream: pathlib.Path) -> str | None:
    for line in stream.read_text(encoding="utf-8").splitlines():
        ev = json.loads(line)
        for b in ev.get("message", {}).get("content", []) if ev.get("type") == "assistant" else []:
            if b.get("type") == "tool_use" and b["name"].endswith("firecrawl_scrape"):
                return b["input"].get("url")
    return None


def validate():
    import yaml
    tasks = {t["id"]: t for t in yaml.safe_load((EXP / "tasks.yaml").read_text(encoding="utf-8"))}
    known = []
    for kind, globs in (("related", ["out_card-0.1/stock/runs/noregistry-related/*/r*", "out_card-0.2/stock/runs/noregistry-related/*/r*"]),
                        ("third", ["out_card-0.3/stock/runs/noregistry-third/*/r*"])):
        for g in globs:
            for d in sorted(EXP.glob(g)):
                u = first_scrapes(d / "stream.jsonl")
                if u:
                    known.append((d.parent.name, kind, u))
    qs = sorted({(t, k) for t, k, _ in known})
    with cf.ThreadPoolExecutor(6) as ex:
        g = dict(zip(qs, ex.map(lambda q: guess(tasks[q[0]][q[1]]["question"]), qs)))
    hits = 0
    for t, k in qs:
        actual = [u for tt, kk, u in known if (tt, kk) == (t, k)]
        same = sum(page_id(u) == page_id(g[(t, k)]) for u in actual)
        hits += same / len(actual)
        print(f"{same}/{len(actual)}  {t:26} {k:7} guess {g[(t, k)][-60:]}  actual {actual[0][-60:]}")
    print(f"guess matches the actual first scrape on {hits / len(qs):.0%} of runs (per question, averaged)")


def main():
    rows = [json.loads(l) for l in (HERE / "questions.jsonl").read_text(encoding="utf-8").splitlines()]
    out_path = HERE / "start.json"
    out = json.loads(out_path.read_text(encoding="utf-8")) if out_path.exists() else {}
    todo = [r for r in rows if str(r["answer_id"]) not in out]
    with cf.ThreadPoolExecutor(6) as ex:
        for r, u in zip(todo, ex.map(lambda r: guess(r["title"]), todo)):
            out[str(r["answer_id"])] = u
    out_path.write_text(json.dumps(out, indent=0), encoding="utf-8")
    print(f"{len(out)} start pages, {sum(not v for v in out.values())} empty")


if __name__ == "__main__":
    validate() if sys.argv[1:] == ["validate"] else main()

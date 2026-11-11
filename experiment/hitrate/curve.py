"""Offline hit-rate curve: how often a new question lands on a card, against how many questions came before.

  python hitrate/curve.py

Inputs: questions.jsonl (Stack Overflow questions whose answers link to the docs: the answer's page
and anchor), pages.json (canonical URLs, heading trees), start.json (the page the agent's model says
it would scrape first). Per site, the questions are put in random order (PERMS times); the first k
are seeds, each leaving a card the way a trace card is built: keyed by the seed's start page,
routing to its answer page and the section holding its answer's anchor. The first card per key is
kept (later seeds don't overwrite it). Each later question is then scored against the cards:

  miss          no card keyed by its start page (nor, with route matching, routing to it)
  right-same    a section served that holds its answer, on the page it started on (slicing only)
  right-other   a section served that holds its answer, on another page (routing, as mdn)
  wrong         a section served that doesn't hold its answer (card-0.4 skips it on a `query`)
  named         a route to another page with no section: the URL is named, nothing served
  pass          a route that is the start page with no section: the call goes to stock

A section is the narrowest heading holding the answer's anchor ("deep"), or its top-level section
("top", level 1-2 under the page title), as two bounds on how wide agents' sections are. A section
over half the page counts as none. An answer with no anchor, or one not found on the page, has no
section. Start pages are matched as the wrapper does (page_id of the URL as given, "literal") and
after following redirects ("canonical").
"""
import json, pathlib, random, statistics, sys

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE.parent))
from bc.common import page_id

PERMS = 300
KS = (5, 10, 25, 50, 75)
OUTCOMES = ("miss", "right-same", "right-other", "wrong", "named", "pass")
EXTRA = ("route-right", "route-wrong")  # a card on the start page routes to the answer page (not the start) / only to other pages

pages = json.loads((HERE / "pages.json").read_text(encoding="utf-8"))
canon, trees = pages["canonical"], pages["pages"]
start = json.loads((HERE / "start.json").read_text(encoding="utf-8"))
rows = [json.loads(l) for l in (HERE / "questions.jsonl").read_text(encoding="utf-8").splitlines()]


START_CANON = HERE / "start_canon.json"
_sc = json.loads(START_CANON.read_text(encoding="utf-8")) if START_CANON.exists() else {}


def resolve_starts() -> None:
    """Follow each guessed start URL's redirects over plain HTTP (no credits), cached in start_canon.json."""
    import httpx
    todo = sorted({u for u in start.values() if u and u not in _sc and u.split("#")[0] not in canon})
    with httpx.Client(headers={"User-Agent": "Mozilla/5.0 (research fetch)"}, timeout=30) as c:
        for u in todo:
            try:
                _sc[u] = str(c.get(u, follow_redirects=True).url).split("#")[0]
            except Exception:
                _sc[u] = u
    START_CANON.write_text(json.dumps(_sc, indent=0), encoding="utf-8")


def canonical_start(url: str) -> str:
    """The start URL after redirects."""
    base = url.split("#")[0]
    return page_id(canon.get(base) or _sc.get(url) or url)


def span(tree: dict, i: int) -> tuple[int, int]:
    heads = tree["heads"]
    line, level = heads[i][0], heads[i][1]
    end = next((h[0] for h in heads[i + 1:] if h[1] <= level), tree["lines"])
    return line, end


def section(tree: dict, anchor: str | None, top: bool) -> tuple[int, int] | None:
    """Line span of the section holding the anchor, or None."""
    if not anchor or not tree.get("heads"):
        return None
    a = anchor.lower()
    heads = tree["heads"]
    idx = next((i for i, h in enumerate(heads) if h[3].lower() == a), None)
    if idx is None and a in tree.get("anchors", {}):
        line = tree["anchors"][a]
        idx = max((i for i, h in enumerate(heads) if h[0] <= line), default=None)
    if idx is None:
        return None
    if top:
        min_level = min(h[1] for h in heads)
        while idx > 0 and heads[idx][1] > min_level + 1:
            idx = max((i for i in range(idx) if heads[i][1] < heads[idx][1]), default=0)
    a0, a1 = span(tree, idx)
    if (a1 - a0) > tree["lines"] / 2:
        return None
    return a0, a1


def answer_line(tree: dict, anchor: str | None) -> int | None:
    if not anchor or not tree.get("heads"):
        return None
    a = anchor.lower()
    h = next((h for h in tree["heads"] if h[3].lower() == a), None)
    return h[0] if h else tree.get("anchors", {}).get(a)


def prepare(top: bool, canonical: bool) -> list[dict]:
    out = []
    for r in rows:
        s = start.get(str(r["answer_id"]))
        if not s:
            continue
        apid = page_id(canon.get(r["doc_url"], r["doc_url"]))
        tree = trees.get(apid, {})
        out.append({"site": r["site"], "start": canonical_start(s) if canonical else page_id(s), "answer": apid,
                    "section": section(tree, r["anchor"], top), "line": answer_line(tree, r["anchor"])})
    return out


def holds(c: dict, q: dict) -> bool:
    return (c["section"] is not None and c["answer"] == q["answer"] and q["line"] is not None
            and c["section"][0] <= q["line"] < c["section"][1])


def outcome(q: dict, cards: dict, route_match: bool) -> str:
    """cards: start page -> list of seed routes (one in the first-card model, all in the pooled one)."""
    cs = cards.get(q["start"])
    if not cs and route_match:
        cs = [c for v in cards.values() for c in v if c["section"] and c["answer"] == q["start"]]
    if not cs:
        return "miss"
    if any(holds(c, q) for c in cs):
        return "right-same" if q["answer"] == q["start"] else "right-other"
    if any(c["section"] for c in cs):
        return "wrong"
    return "pass" if all(c["answer"] == q["start"] for c in cs) else "named"


def curve(qs: list[dict], route_match: bool, pooled: bool = False, seed: int = 0) -> dict[int, dict[str, float]]:
    rng = random.Random(seed)
    res = {k: {o: [] for o in OUTCOMES + EXTRA} for k in KS}
    for _ in range(PERMS):
        order = qs[:]
        rng.shuffle(order)
        for k in KS:
            if k >= len(order):
                continue
            cards = {}
            for s in order[:k]:
                v = cards.setdefault(s["start"], [])
                if pooled or not v:
                    v.append(s)
            held = order[k:]
            counts = {o: 0 for o in OUTCOMES + EXTRA}
            for q in held:
                counts[outcome(q, cards, route_match)] += 1
                cs = cards.get(q["start"]) or []
                counts["route-right"] += q["answer"] != q["start"] and any(c["answer"] == q["answer"] for c in cs)
                counts["route-wrong"] += bool(cs) and all(c["answer"] not in (q["answer"],) for c in cs) \
                    and any(c["answer"] != q["start"] for c in cs)
            for o in OUTCOMES + EXTRA:
                res[k][o].append(counts[o] / len(held))
    return {k: {o: statistics.mean(v) for o, v in d.items() if v} for k, d in res.items()}


def main():
    resolve_starts()
    sites = sorted({r["site"] for r in rows})
    for top, canonical, pooled in ((False, False, False), (False, True, False), (True, True, False),
                                   (False, True, True), (True, True, True)):
        if True:
            qs = prepare(top, canonical)
            print(f"\n=== sections {'top' if top else 'deep'}, start pages {'canonical' if canonical else 'literal'}, "
                  f"{'pooled: every seed section kept' if pooled else 'first card per page'} (route matching on)")
            print(f"{'site':6} {'n':>4} {'k':>3}  " + "  ".join(f"{o:>11}" for o in OUTCOMES + EXTRA))
            for site in sites:
                sq = [q for q in qs if q["site"] == site]
                c = curve(sq, route_match=True, pooled=pooled)
                for k in KS:
                    if c[k]:
                        print(f"{site:6} {len(sq):>4} {k:>3}  " + "  ".join(f"{c[k][o]:>11.0%}" for o in OUTCOMES + EXTRA))
    qs = prepare(False, False)
    print("\nper site: share of questions whose start page is the answer page; with an answer section (deep / top)")
    for site in sites:
        sq = [q for q in qs if q["site"] == site]
        same = sum(q["start"] == q["answer"] for q in sq) / len(sq)
        deep = sum(q["section"] is not None for q in sq) / len(sq)
        tq = [q for q in prepare(True, False) if q["site"] == site]
        topn = sum(q["section"] is not None for q in tq) / len(tq)
        print(f"  {site:6} n={len(sq):3}  start==answer {same:.0%}  section deep {deep:.0%}  top {topn:.0%}")


if __name__ == "__main__":
    main()

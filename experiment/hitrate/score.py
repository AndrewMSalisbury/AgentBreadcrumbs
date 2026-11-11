"""curve-0.1, step 2: hit-rate curve from real traces, pooled cards against one card per page.

  python hitrate/score.py [--out out_curve-0.1]

Each run (hitrate/traces.py) gives a trace card (out_trace-0.1/build.py, lean, as trace-0.2): keyed
by the run's first successful page on the host that held its answer, routing to the call that held
it (URL, and section when the run asked for one or cited an anchor). Per run the scorer also keeps
the run's first fetched page (where a card would be met) and its answer location (route page and
section). In PERMS random orders, the first k runs leave cards; each later run is scored:

  miss         no card for the page it fetched first (nor a section route reading that page)
  right        a served section holds its answer: its own route is on that page and its section
               lies inside the served one; or, when its run read the page whole, the card-0.4
               matcher (bc/section_match.py) ranks the served section the page's best for its
               question
  wrong        a section is served and none holds its answer
  route-right  no section, but a card routes from its first page to the page that held its answer
  route-wrong  no section, and the card routes to another page
  pass         a card with no section on the page it already fetched: nothing changes

pooled: a page's card keeps every seed's route (the registry grows within a page); first: the first
seed's route only (the registry as it is). Pages are fetched with the local fetch (no credits) to
place sections.
"""
import collections, json, pathlib, random, re, statistics, sys

HERE = pathlib.Path(__file__).parent
EXP = HERE.parent
sys.path.insert(0, str(EXP))
sys.path.insert(0, str(EXP / "out_trace-0.1"))
import build
from bc.common import page_id, fetch_clean
from bc.section_match import section_span, serves

OUT = EXP / (sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else "out_curve-0.1")
PERMS, KS = 300, (5, 10, 25, 50, 75)
OUTCOMES = ("miss", "right", "wrong", "route-right", "route-wrong", "pass")
TEXT = OUT / "pages_text.json"
_text = json.loads(TEXT.read_text(encoding="utf-8")) if TEXT.exists() else {}


def page_text(url: str) -> str:
    pid = page_id(url)
    if pid not in _text:
        try:
            _text[pid] = fetch_clean(url.split("#")[0])[0]
        except Exception:
            _text[pid] = ""
    return _text[pid]


def runs() -> list[dict]:
    out = []
    qs = {t["id"]: t["question"] for t in __import__("yaml").safe_load((OUT / "tasks.yaml").read_text(encoding="utf-8"))}
    for d in sorted((OUT / "runs/noregistry").glob("*/r1")):
        s = d / "stream.jsonl"
        if not (d / "result.json").exists():
            continue
        order, _, _ = build.calls(s)
        rec = build.card(s, lean=True)
        first = next((c["url"] for c in order), None)
        r = {"id": d.parent.name, "question": qs.get(d.parent.name, ""), "first": page_id(first) if first else None,
             "fetches": len(order)}
        if rec:
            route = rec["route"]
            r.update(key=page_id(rec["url"]), route_page=page_id(route["url"]), route_url=route["url"],
                     section=route.get("section"))
        out.append(r)
    return out


def span_of(url: str, section: str | None):
    return section_span(page_text(url), section) if section else None


def outcome(q: dict, cards: dict) -> str:
    if not q["first"]:
        return "miss"
    cs = cards.get(q["first"]) or [c for v in cards.values() for c in v
                                    if c.get("section") and c["route_page"] == q["first"]]
    if not cs:
        return "miss"
    sec = [c for c in cs if c.get("section")]
    if sec:
        for c in sec:
            if q.get("route_page") != c["route_page"]:
                continue
            cs_span = span_of(c["route_url"], c["section"])
            if not cs_span:
                continue
            if q.get("section"):
                qs_span = span_of(q["route_url"], q["section"])
                if qs_span and cs_span[0] <= qs_span[0] < cs_span[1]:
                    return "right"
            elif serves(page_text(c["route_url"]), c["section"], q["question"])[0]:
                return "right"
        return "wrong"
    if any(c["route_page"] == q.get("route_page") and c["route_page"] != q["first"] for c in cs):
        return "route-right"
    return "pass" if all(c["route_page"] == q["first"] for c in cs) else "route-wrong"


def curve(rs: list[dict], pooled: bool) -> dict:
    rng = random.Random(0)
    res = {k: collections.defaultdict(list) for k in KS}
    memo = {}
    for _ in range(PERMS):
        order = rs[:]
        rng.shuffle(order)
        for k in KS:
            if k >= len(order):
                continue
            cards = {}
            for s in order[:k]:
                if "key" in s and (pooled or s["key"] not in cards):
                    cards.setdefault(s["key"], []).append(s)
            held = order[k:]
            cnt = collections.Counter()
            for q in held:
                sig = (q["id"], tuple(sorted((key, tuple(c["id"] for c in v)) for key, v in cards.items()
                                             if key == q["first"] or any(c["route_page"] == q["first"] for c in v))))
                if sig not in memo:
                    memo[sig] = outcome(q, cards)
                cnt[memo[sig]] += 1
            for o in OUTCOMES:
                res[k][o].append(cnt[o] / len(held))
    return {k: {o: statistics.mean(v) for o, v in d.items()} for k, d in res.items() if d}


def main():
    rs = runs()
    with_card = [r for r in rs if "key" in r]
    print(f"{len(rs)} runs; {len(with_card)} leave a card ({sum(bool(r.get('section')) for r in with_card)} with a section);"
          f" {sum(not r['first'] for r in rs)} fetched nothing")
    print(f"first fetch == card key: {sum(r.get('key') == r['first'] for r in with_card)}; answer on the first page:"
          f" {sum(r.get('route_page') == r['first'] for r in with_card)}")
    pages = collections.Counter(r["first"] for r in rs if r["first"])
    print("most common first pages:", ", ".join(f"{p.split('/')[-1]} {c}" for p, c in pages.most_common(8)))
    for pooled in (True, False):
        c = curve(rs, pooled)
        print(f"\n{'pooled: every seed route kept' if pooled else 'first card per page (the registry as it is)'}")
        print(f"{'k':>4}  " + "  ".join(f"{o:>11}" for o in OUTCOMES))
        for k, v in c.items():
            print(f"{k:>4}  " + "  ".join(f"{v[o]:>11.0%}" for o in OUTCOMES))
    TEXT.write_text(json.dumps(_text), encoding="utf-8")


if __name__ == "__main__":
    main()

"""trace-0.1: route cards built from a no-write run's trace, with no agent writing anything.

  python out_trace-0.1/build.py <stream.jsonl> <registry.sqlite>

The card is what a registry that served the fetch tool could store on its own: the page the
run started from (its first successful fetch or render on the host it looked up), the call
that held the answer (the last successful call to the URL the ANSWER line cites, else the last
successful call) with its arguments and size, and the attempts that failed before it. answers
is the page's first heading. No site records and no URL patterns: generalizing from one route
to a pattern is the judgment an agent adds, and what this arm leaves out. Stored through the
registry's own write_page, so the card is validated and fingerprinted like an agent's.
"""
import json, os, pathlib, re, sys

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE.parent))
os.environ.setdefault("BC_CARDS", "route")
from bc import registry_server as rs
from bc.common import host_of, normalize_url, tokens

WEB = ("mcp__web__fetch", "mcp__web__render")
HEAD = re.compile(r"^\[HTTP (\d{3}) ")


def calls(stream: pathlib.Path) -> tuple[list[dict], str | None, str]:
    """Web calls in the order made, each with its input and result text; the first lookup target; the answer."""
    order, results, target, answer = [], {}, None, ""
    for line in stream.read_text(encoding="utf-8").splitlines():
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        if ev.get("type") == "assistant":
            for b in ev["message"].get("content", []):
                if b.get("type") == "tool_use":
                    if b["name"] in WEB:
                        order.append({"id": b["id"], "kind": b["name"].rsplit("__", 1)[1], **b["input"]})
                    elif b["name"].endswith("__lookup") and target is None:
                        target = b["input"].get("target")
        elif ev.get("type") == "user":
            content = ev["message"].get("content")
            for b in content if isinstance(content, list) else []:
                if b.get("type") == "tool_result":
                    c = b.get("content")
                    results[b["tool_use_id"]] = c if isinstance(c, str) else "".join(
                        x.get("text", "") for x in c or [] if isinstance(x, dict))
        elif ev.get("type") == "result":
            answer = ev.get("result") or ""
    for c in order:
        c["reply"] = results.get(c["id"], "")
        m = HEAD.match(c["reply"])
        c["ok"] = bool(m and m[1].startswith("2")) and "not found. Headings" not in c["reply"][:400] \
            and "(no text content" not in c["reply"][:400] and c["reply"].count("\n") > 1
    return order, target, answer


def base(url: str) -> str:
    return normalize_url(url.split("#")[0])


def title(h: str) -> str:
    """A heading as plain text: links reduced to their text, pilcrows dropped."""
    return re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", h).replace("¶", "").strip()[:300]


def failed(c: dict) -> str:
    u = c["url"].split("#")[0].split("://")[-1]
    m = HEAD.match(c["reply"])
    if m and not m[1].startswith("2"):
        return f"{u}: HTTP {m[1]}"
    if "not found. Headings" in c["reply"][:400]:
        return f"section={c.get('section')!r} not found on {u}"
    if "(no text content" in c["reply"][:400]:
        return f"{u}: empty without JavaScript"
    if c["reply"].startswith("[fetch failed") or c["reply"].startswith("[render failed"):
        return f"{u}: {c['kind']} failed"
    return ""


def card(stream: pathlib.Path, writer: str = "trace", observed: str | None = None, lean: bool = False) -> dict | None:
    """lean (trace-0.2): no start offset, since it found this run's answer and sent later agents
    with other questions to the wrong part of the page (step 2: systemd, vim, sqlite). A section
    is kept: it names a part of the page, which other questions can share."""
    order, target, answer = calls(stream)
    ok = [c for c in order if c["ok"]]
    if not ok:
        return None
    cited = re.findall(r"ANSWER:.*?\(source:\s*(\S+?)\)?\s*$", answer, re.M)
    hits = [c for c in ok if cited and base(c["url"]) == base(cited[-1])]
    route = (hits or ok)[-1]
    site = host_of(target) if target else host_of(route["url"])
    # Filed where a later agent looks up: a page on the looked-up host, even one that failed
    # (an empty JavaScript page is exactly what the route gets around), else the lookup target.
    page = next((c for c in ok if host_of(c["url"]) == site), None) or \
        next((c for c in order if host_of(c["url"]) == site), None) or \
        ({"url": target if "://" in target else "https://" + target} if target else route)
    replies = [c["reply"] for c in order if base(c["url"]) == base(page["url"])] + [route["reply"]]
    heads = [m[1] for t in replies if (m := re.search(r"^# (.+)$", t, re.M))] + \
            [m[1] for t in replies if (m := re.search(r"Headings: ([^(;]+?) \(#", t))]
    heads = [h for h in heads if re.search(r"[A-Za-z]{3}", h)]
    r = {"url": route["url"].split("#")[0], "tokens": tokens(route["reply"])}
    for k in ("section", "select") if lean else ("section", "start", "select"):
        if route.get(k) not in (None, "", 0, []):
            r[k] = route[k]
    if "#" in route["url"] and "section" not in r:
        r["section"] = route["url"].split("#", 1)[1]
    fails = [f for f in dict.fromkeys(failed(c) for c in order[:order.index(route)]) if f]
    size = max((int(n) for t in replies for n in re.findall(r"tokens \d+-\d+ of (\d+)\]", t[:300])), default=0)
    if lean and size and "section" not in r and base(r["url"]) == base(page["url"]):
        r["tokens"] = size  # the whole page, not the part that answered this run
    notes = "; ".join(fails + ([f"page is {size} tokens"] if size else []))
    if notes:
        r["notes"] = notes[:199]
    rec = {"schema": "0.2", "url": page["url"].split("#")[0], "tier": "L1",
           "answers": title(heads[0] if heads else page["url"].split("#")[0]), "route": r,
           "observed_at": observed or __import__("datetime").date.today().isoformat(),
           "provenance": {"writer": writer, "observed_at": observed or __import__("datetime").date.today().isoformat()}}
    if route["kind"] == "render":
        rec["access"] = {"js_required": True}
    return rec


def build(stream: pathlib.Path, registry: pathlib.Path, lean: bool = False, merge: bool = False) -> str:
    """Write the trace card into a fresh registry, or with merge into the one there (trace-0.2: the
    cold run's own registry, holding any site record it wrote); returns write_page's reply."""
    registry.parent.mkdir(parents=True, exist_ok=True)
    if registry.exists() and not merge:
        registry.unlink()
    rec = card(stream, lean=lean)
    rs.DB_PATH = str(registry)
    rs.connect().close()  # an empty registry even when there is no card
    if rec is None:
        return "no card: no successful fetch or render"
    (registry.parent / "card.json").write_text(json.dumps(rec, indent=2), encoding="utf-8")
    return rs.write_page(rec)


if __name__ == "__main__":
    print(build(pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), lean="--lean" in sys.argv, merge="--merge" in sys.argv))

"""MCP server `web`: fetch and render, identical for both experiment arms.

With BC_ENFORCE=1 (enforced-*) each call is logged to BC_CALL_LOG and every
result ends with a note saying whether write would store a page card from this run.
With BC_MISS=x (miss-0.2) calls are logged too, and only the first fetch or
render that makes a page card storable, in a run whose lookup sent the miss note,
says so. Each logged call records the tokens its reply returned (BC_MIN_PULL reads them).
BC_SEARCHES=1 (miss-0.7) counts searches toward that bar, as the registry does.
BC_DEFER=1 (miss-0.9): if the lookup sent only the site-record note, that fetch carries
the page-card instructions (bc.common.CARD_NOTE).
BC_SITE_SIGNAL=1 (miss-0.13): the lookup sent nothing, so the first fetch or render whose
result shows an access route (bc.common.access_signal) carries the site-record note.
BC_FOLD=1 (fold-0.1): no lookup tool; fetch and render read the registry (BC_REGISTRY) themselves.
A plain call for a page with a route card returns the route's content (its url, select and
section; start found an earlier question's answer, so it is only named) under a line saying so,
and as_is=true gets the page itself; a call with its own arguments gets what it asked for, with the
card's route named once per page above it. The first call to a site that has cards, but none for this
page, lists them after the reply. Each hit is logged as a "fold" line to BC_CALL_LOG.
"""
import sys, pathlib, re, os, datetime, json
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from mcp.server.mcpserver import MCPServer
from bc.common import ENC, page_id, host_of, tokens, fetch_clean, render_clean, log_call, call_counts, card_block, stored_site_records, \
    DEFER, CARD_NOTE, SIGNAL, SIGNAL_NOTE, access_signal

# Claude Code moves any tool result over ~50 KB into a file the agent cannot read,
# so each reply stays under both limits and says where to continue.
MAX_TOKENS = 10000
MAX_CHARS = 36000
ENFORCE = os.environ.get("BC_ENFORCE") == "1"
MISSX = os.environ.get("BC_MISS") == "x"
SEARCHES = os.environ.get("BC_SEARCHES") == "1"
FOLD = os.environ.get("BC_FOLD") == "1"
LOGGED = ENFORCE or MISSX
HEADING = re.compile(r"^(#{1,6})\s+(.+)$")
mcp = MCPServer("web")


def _headings(lines: list[str]) -> list[tuple[int, int, str, str]]:
    """(line index, level, title, anchor) for each Markdown heading."""
    out = []
    for i, line in enumerate(lines):
        if m := HEADING.match(line):
            raw = m[2]
            anchors = re.findall(r"\]\([^)\s]*#([^)\s]+)\)", raw)
            title = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", raw).replace("¶", "").replace("`", "").strip()
            anchor = anchors[-1] if anchors else re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
            out.append((i, len(m[1]), title, anchor))
    return out


def _outline(heads) -> str:
    return "; ".join(f"{t} (#{a})" for _, _, t, a in heads[:60])


def _section(text: str, want: str) -> tuple[str | None, str]:
    """Text under the heading matching `want` (anchor or heading text), plus the outline."""
    lines = text.splitlines()
    heads = _headings(lines)
    w = want.lstrip("#").strip().lower()
    hit = next((h for h in heads if w in (h[3].lower(), h[2].lower())), None) \
        or next((h for h in heads if w in h[2].lower() or w in h[3].lower()), None)
    if not hit:
        return None, _outline(heads)
    i, level = hit[0], hit[1]
    end = next((h[0] for h in heads if h[0] > i and h[1] <= level), len(lines))
    return "\n".join(lines[i:end]), _outline(heads)


def _reply(text: str, head: str, start: int = 0) -> str:
    ids = ENC.encode(text, disallowed_special=())
    total = len(ids)
    chunk = ENC.decode(ids[start:start + MAX_TOKENS])[:MAX_CHARS]
    end = start + len(ENC.encode(chunk, disallowed_special=()))
    if start == 0 and end >= total:
        return f"[{head}, {total} tokens]\n{chunk}"
    note = f"[{head}, tokens {start}-{end} of {total}]"
    if end < total:
        heads = _headings(text.splitlines())
        note += f"\n[continue with start={end}, or pass section=<heading or #anchor>. Headings: {_outline(heads)}]"
    return f"{note}\n{chunk}"


def _respond(text: str, head: str, section: str | None, start: int) -> str:
    if section:
        part, outline = _section(text, section)
        if part is None:
            return f"[{head}] section {section!r} not found. Headings: {outline}"
        return _reply(part, f"{head} section {section!r}", start)
    return _reply(text, head, start)


_nudged = False


def _site_note(kind: str, reply: str) -> str:
    """miss-0.13: the site-record note, once, on a result that shows an access route."""
    lines = _call_lines()
    if "note\tsignal" not in lines or "note\tsite" in lines:
        return reply
    why = access_signal(kind, reply, [l.split("\t", 1)[1] for l in lines if l.startswith("lookup\t")])
    if not why:
        return reply
    log_call("note", "site")
    return reply + SIGNAL_NOTE.format(why=why, writer=os.environ.get("BC_WRITER", "unknown"),
                                      today=datetime.date.today().isoformat())


def _card_note(url: str, reply: str, kind: str = "fetch") -> str:
    global _nudged
    if MISSX:
        if SIGNAL:
            reply = _site_note(kind, reply)
        if _nudged or "note\tmiss" not in _call_lines():
            return reply
        counts = call_counts()
        if card_block([url], stored_site_records(os.environ.get("BC_REGISTRY")), counts, searches=SEARCHES):
            return reply
        _nudged = True
        log_call("nudge", url)  # read by the miss-0.3+ Stop hook
        taken = f"{counts['fetch']} fetch{'es' if counts['fetch'] != 1 else ''}" + (
            f" and {counts['search']} search{'es' if counts['search'] != 1 else ''}" if SEARCHES and counts["search"] else "")
        if DEFER and "note\tdefer" in _call_lines():
            return reply + CARD_NOTE.format(taken=taken, writer=os.environ.get("BC_WRITER", "unknown"),
                                            today=datetime.date.today().isoformat())
        return reply + (f"\n[breadcrumbs: this run has now taken {taken}, so write would store "
                        "a page card from it: write one for the page that holds the answer before answering.]")
    if not ENFORCE:
        return reply
    why = card_block([url], stored_site_records(os.environ.get("BC_REGISTRY")), call_counts())
    return reply + (f"\n[breadcrumbs: write would not store a page card from this run: {why}]"
                    if why else "\n[breadcrumbs: write would store a page card from this run]")


def _call_lines() -> list[str]:
    try:
        return open(os.environ["BC_CALL_LOG"], encoding="utf-8").read().splitlines()
    except (KeyError, FileNotFoundError):
        return []


FETCH_DOC = """Fetch a URL without running JavaScript. HTML is returned as cleaned Markdown;
    JSON, Markdown and plain text are returned as-is. For JSON, `select` keeps only
    the given dotted paths (e.g. ["crate.name", "versions.0.num"]). `section` (heading
    text or #anchor; a #fragment in the URL works too) returns only that section.
    Output is at most 10,000 tokens per call; longer results say which `start` to
    pass for the next part and list the page's headings."""
FOLD_DOC = """ When an earlier agent found a cheaper route to
    a page (a raw source, an API, a section), a plain fetch of the page returns that route's
    content instead and says so; pass as_is=true for the page itself."""


def fetch(url: str, select: list[str] | None = None, section: str | None = None, start: int = 0) -> str:
    if not section and "#" in url:
        url, section = url.split("#", 1)
    reply = _fetch(url, select, section, start)
    if LOGGED:
        log_call("fetch", f"{url}\t{tokens(reply)}")
    return _card_note(url, reply)


def fetch_folded(url: str, select: list[str] | None = None, section: str | None = None, start: int = 0,
                 as_is: bool = False) -> str:
    if not section and "#" in url:
        url, section = url.split("#", 1)
    if not (as_is or select or section or start) and (hit := _folded(url, "fetch")):
        return hit
    return _others(url, _named(url, _fetch(url, select, section, start)))


fetch.__doc__, fetch_folded.__doc__ = FETCH_DOC, FETCH_DOC + FOLD_DOC
fetch = mcp.tool(name="fetch", structured_output=False)(fetch_folded if FOLD else fetch)


_seen_sites: set[str] = set()
_named_pages: set[str] = set()


def _cards(site: str) -> list[dict]:
    import sqlite3
    try:
        with sqlite3.connect(os.environ["BC_REGISTRY"]) as db:
            return [json.loads(r) for (r,) in db.execute("SELECT record FROM pages WHERE site = ?", (site,))]
    except (KeyError, sqlite3.Error):
        return []


def _bad(reply: str) -> bool:
    head = reply[:400]
    return head.startswith(("[fetch failed", "[render failed")) or "not found. Headings" in head \
        or "(no text content" in head or not re.match(r"\[(HTTP 2|rendered )", head)


def _card(url: str) -> dict | None:
    return next((c for c in _cards(host_of(url)) if c.get("id") == page_id(url) and c.get("route")), None)


def _route_line(url: str, r: dict) -> str:
    args = "".join(f", {k}={r[k]!r}" for k in ("select", "section") if r.get(k))
    extra = "".join(f"; {k}: {r[k]}" for k in ("start", "notes") if r.get(k))
    return f"[breadcrumbs: an earlier agent's route for {url}: fetch({r['url']!r}{args}){extra}."


def _named(url: str, reply: str) -> str:
    """fold-0.1: a call with its own arguments on a carded page; the route is named once per page."""
    if not FOLD or page_id(url) in _named_pages or not (card := _card(url)):
        return reply
    _named_pages.add(page_id(url))
    _seen_sites.add(host_of(url))
    log_call("fold-named", url)
    return f"{_route_line(url, card['route'])}]\n{reply}"


def _folded(url: str, kind: str) -> str | None:
    """fold-0.1: the route's content for a page with a route card, or None to fetch as asked."""
    if not (card := _card(url)):
        return None
    r = card["route"]
    if page_id(r["url"]) == page_id(url) and not (r.get("section") or r.get("select")):
        return None  # the route is the page as fetched; _named still names it
    _seen_sites.add(host_of(url))
    reply = _fetch(r["url"], r.get("select"), r.get("section"), 0) if kind == "fetch" or r["url"] != url \
        else _render(r["url"], r.get("section"), 0)
    if _bad(reply):
        return None
    _named_pages.add(page_id(url))
    log_call("fold", f"{url}\t{r['url']}\t{tokens(reply)}")
    return f"{_route_line(url, r)} This is the route's content; {kind} with as_is=true for the page itself.]\n{reply}"


def _others(url: str, reply: str) -> str:
    """fold-0.1: once per site, the carded pages there, if this page has no card."""
    site = host_of(url)
    if not FOLD or site in _seen_sites:
        return reply
    _seen_sites.add(site)
    cards = [c for c in _cards(site) if c.get("id") != page_id(url) and c.get("route")]
    if not cards:
        return reply
    log_call("fold-others", site)
    lines = "; ".join(f"{c['url']} ({c.get('answers', '')[:80]}) -> {c['route']['url']}" for c in cards[:10])
    return reply + f"\n[breadcrumbs: earlier agents found routes for other pages on {site}: {lines}]"


def _fetch(url, select, section, start) -> str:
    try:
        text, m = fetch_clean(url, select)
    except Exception as e:
        return f"[fetch failed: {type(e).__name__}: {e}]"
    head = f"HTTP {m['status']} {m['content_type']} {m['final_url']}"
    if not text.strip():
        return f"[{head}] (no text content; the page may need JavaScript: try render)"
    return _respond(text, head, section, start)


RENDER_DOC = """Load a URL in headless Chrome (runs JavaScript, ~10-20 s), then return the
    cleaned Markdown. Use for pages that fetch returns empty. `section` and `start`
    work as in fetch; output is at most 10,000 tokens per call."""


def render(url: str, section: str | None = None, start: int = 0) -> str:
    if not section and "#" in url:
        url, section = url.split("#", 1)
    reply = _render(url, section, start)
    if LOGGED:
        log_call("render", f"{url}\t{tokens(reply)}")
    return _card_note(url, reply, "render")


def render_folded(url: str, section: str | None = None, start: int = 0, as_is: bool = False) -> str:
    if not section and "#" in url:
        url, section = url.split("#", 1)
    if not (as_is or section or start) and (hit := _folded(url, "render")):
        return hit
    return _others(url, _named(url, _render(url, section, start)))


render.__doc__, render_folded.__doc__ = RENDER_DOC, RENDER_DOC + " as_is works as in fetch."
render = mcp.tool(name="render", structured_output=False)(render_folded if FOLD else render)


def _render(url, section, start) -> str:
    try:
        text, _ = render_clean(url)
    except Exception as e:
        return f"[render failed: {type(e).__name__}: {e}]"
    if not text.strip():
        return f"[rendered {url}] (no text content)"
    return _respond(text, f"rendered {url}", section, start)


if __name__ == "__main__":
    mcp.run()

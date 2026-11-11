"""MCP server `firecrawl`: the stock firecrawl-mcp server with route cards in front of its scrape
(run.py --backend firecrawl-card; card-0.1, LOG 2026-11-11).

  python bc/firecrawl_card.py

Starts the stock server (bc/firecrawl_mcp.py, same pinned version) and passes its tool list,
instructions and every call through unchanged, so the agent sees exactly the stock schema and
its ~42k tokens of definitions. One exception: the first firecrawl_scrape of a page that has a
route card in BC_REGISTRY, whatever formats it asks for, when the route narrows the page:

  - a raw source (a JSON/text URL or a `select`): fetched over plain HTTP, 0 credits
  - a `section`: the route's page as Firecrawl Markdown (1 credit), sliced to that section
  - another URL, no section: the agent's own call goes to stock, and the reply names the route's
    URL (card-0.2). With BC_CARD_REDIRECT=1 (card-0.1) the call is sent to that URL instead,
    which on rust sent a pop_if question to the extract_if question's page

card-0.3 (BC_CARD_ROUTE_MATCH=1) also serves a section route when the agent scrapes the page the
route reads rather than the page it was found from (gha's related question ends on workflow-syntax,
the matrix question's route page). The section was found for another question, so the note says
so and names that question's topics; a second scrape gets stock's reply.

card-0.4 (BC_CARD_PROMPT_CHECK=1, with route matching on) uses the agent's question when it has one:
a scrape with a `query` prompt is served the stored section only if bc/section_match.py ranks it
(nearly) the page's best match for that prompt; otherwise the call goes to stock as asked, the
1-credit section scrape logged as "card-skip". On gha third-0.1's agent asked a `query` about job
outputs and was served the matrix section.

A route that is the page itself with no section (or only a `start` offset) adds nothing over the
agent's call, so that call goes to stock as is. A second scrape of the same page always goes to
stock, which is how an agent gets Firecrawl's own reply (a `query` answer, say). The first scrape
on a site with cards for other pages lists them after the reply, as fold-0.1 does.

Replies keep stock's output schema (structured content plus the same JSON as text); the
breadcrumbs note goes in its `warning` field, the one free-text field, since the schema allows no
new keys. Each call is logged to BC_CALL_LOG: "card" for a served route (with its credits),
"forward" for a call passed to stock (name and arguments, so report.py can price it), and
"firecrawl" lines for the section scrapes (bc.common.firecrawl_scrape).
"""
import asyncio, json, os, pathlib, re, sqlite3, sys

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from mcp import types
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.server.lowlevel.server import Server
from mcp.server.stdio import stdio_server

from bc.common import page_id, host_of, tokens, fetch_clean, firecrawl_scrape, log_call
from bc.web_server import _section
from bc.section_match import serves

HERE = pathlib.Path(__file__).parent
RAW = re.compile(r"\.(json|txt|md|markdown|ya?ml|xml|toml|csv|rst)(\?|$)", re.I)
REDIRECT = os.environ.get("BC_CARD_REDIRECT") == "1"
ROUTE_MATCH = os.environ.get("BC_CARD_ROUTE_MATCH") == "1"
PROMPT_CHECK = os.environ.get("BC_CARD_PROMPT_CHECK") == "1"


def _prompt(args: dict) -> str | None:
    """The question in a scrape's `query` format, if it asks one."""
    for f in args.get("formats") or []:
        if f == "query" or (isinstance(f, dict) and f.get("type") == "query"):
            q = (args.get("queryOptions") or {}).get("prompt") or (f.get("prompt") if isinstance(f, dict) else None)
            return q or None
    return None
_served: set[str] = set()  # page ids whose card was used once
_seen_sites: set[str] = set()


def _cards(site: str) -> list[dict]:
    try:
        with sqlite3.connect(os.environ["BC_REGISTRY"]) as db:
            return [json.loads(r) for (r,) in db.execute("SELECT record FROM pages WHERE site = ?", (site,))]
    except (KeyError, sqlite3.Error):
        return []


def _card(url: str) -> tuple[dict | None, bool]:
    """The card for this page, and whether it matched by the page its route reads (card-0.3)."""
    cards, pid = [c for c in _cards(host_of(url)) if c.get("route")], page_id(url)
    if c := next((c for c in cards if c.get("id") == pid), None):
        return c, False
    if ROUTE_MATCH:
        if c := next((c for c in cards if c["route"].get("section") and page_id(c["route"]["url"]) == pid), None):
            return c, True
    return None, False


def _raw(r: dict) -> bool:
    u = r["url"]
    return bool(r.get("select")) or "raw.githubusercontent.com" in u or bool(RAW.search(u.split("#")[0]))


def _result_text(res) -> str:
    return "\n".join(c.text for c in getattr(res, "content", []) if getattr(c, "type", "") == "text")


def _result(data: dict) -> types.CallToolResult:
    """A scrape result shaped like stock's: the structured data, and the same as JSON text."""
    return types.CallToolResult(content=[types.TextContent(type="text", text=json.dumps(data, ensure_ascii=False))],
                                structured_content=data)


def _noted(res, note: str, after: bool = False) -> types.CallToolResult:
    """Stock's result with a breadcrumbs note in its `warning` field, placed first so the agent
    reads it before the page, or last for the list of other pages' cards."""
    data = dict(getattr(res, "structured_content", None) or {})
    if not data:
        text = _result_text(res)
        return types.CallToolResult(content=[types.TextContent(
            type="text", text=f"{text}\n{note}" if after else f"{note}\n{text}")])
    warn = " ".join(w for w in (data.pop("warning", None), note) if w)
    return _result({**data, "warning": warn} if after else {"warning": warn, **data})


def _route_line(url: str, r: dict) -> str:
    if r.get("section"):
        how = f"section {r['section']!r} of {r['url']}"
    elif _raw(r):
        how = f"{r['url']} over plain HTTP" + (f", select {r['select']}" if r.get("select") else "")
    else:
        how = r["url"]
    return f"[breadcrumbs: an earlier agent's route for {url}: {how}."


def _serve(url: str, r: dict, other: dict | None = None, prompt: str | None = None) -> dict | None:
    """The route's content as stock-shaped scrape data, or None to fall back to stock. With
    `prompt` (card-0.4), a section is served only if it matches that question."""
    if _raw(r):
        try:
            text, m = fetch_clean(r["url"], r.get("select"))
        except Exception:
            return None
        if m["status"] != 200 or not text.strip():
            return None
        part, credits = text, 0
        if r.get("section"):
            s = _section(text, r["section"])[0]
            part = s or part
    else:
        try:
            text, m = firecrawl_scrape(r["url"])
        except Exception:
            return None
        part = _section(text, r["section"])[0]
        credits = m.get("credits") or 1
        if not part:
            log_call("card-miss", f"{url}\t{r['url']}\t{r['section']}")
            return None
        if prompt:
            ok, why = serves(text, r["section"], prompt)
            if not ok:
                log_call("card-skip", f"{url}\t{r['url']}\t{credits}\t{why}")
                return None
    log_call("card-route" if other else "card", f"{url}\t{r['url']}\t{credits}\t{tokens(part)}")
    if other:
        topics = (other.get("answers") or "")[:120]
        note = (f"[breadcrumbs: an earlier agent found section {r['section']!r} of this page for another question"
                f" (via {other['url']}{'; ' + topics if topics else ''}). It may not hold your answer. Served in"
                f" place of the formats asked for; scrape {url} again for Firecrawl's own reply.]")
    else:
        note = (f"{_route_line(url, r)} This is the route's content, served in place of the formats asked for; "
                f"scrape {url} again for Firecrawl's own reply.]")
    return {"warning": note, "markdown": part, "metadata": {"sourceURL": r["url"], "statusCode": 200}}


def _others(url: str) -> str | None:
    """Once per site, the carded pages there, if this page has no card."""
    site = host_of(url)
    if site in _seen_sites:
        return None
    _seen_sites.add(site)
    cards = [c for c in _cards(site) if c.get("id") != page_id(url) and c.get("route")]
    if not cards:
        return None
    log_call("card-others", site)
    lines = "; ".join(f"{c['url']} ({c.get('answers', '')[:80]}) -> {c['route']['url']}" for c in cards[:10])
    return f"[breadcrumbs: earlier agents found routes for other pages on {site}: {lines}]"


async def main():
    upstream = StdioServerParameters(command=sys.executable, args=[str(HERE / "firecrawl_mcp.py")],
                                     env=dict(os.environ))
    async with stdio_client(upstream) as (ur, uw), ClientSession(ur, uw) as stock:
        init = await stock.initialize()
        tools = await stock.list_tools()

        async def list_tools(ctx, params):
            return tools

        async def call_tool(ctx, params: types.CallToolRequestParams):
            name, args = params.name, dict(params.arguments or {})
            url = args.get("url") if name == "firecrawl_scrape" else None
            card, by_route = _card(url) if url and page_id(url) not in _served else (None, False)
            if card:
                r, pid = card["route"], page_id(url)
                _served.add(pid)
                _seen_sites.add(host_of(url))
                if r.get("section") or _raw(r):
                    prompt = _prompt(args) if PROMPT_CHECK else None
                    if (hit := await asyncio.to_thread(_serve, url, r, card if by_route else None, prompt)) is not None:
                        return _result(hit)
                elif page_id(r["url"]) != pid and REDIRECT:
                    args["url"] = r["url"]
                    log_call("card-redirect", f"{url}\t{r['url']}")
                    log_call("forward", f"{name}\t{json.dumps(args)}")
                    res = await stock.call_tool(name, args)
                    return _noted(res, f"{_route_line(url, r)} This scrape went to that URL instead; "
                                       f"scrape {url} again for the page itself.]")
                elif page_id(r["url"]) != pid:
                    log_call("card-named", f"{url}\t{r['url']}")
                    log_call("forward", f"{name}\t{json.dumps(args)}")
                    res = await stock.call_tool(name, args)
                    if getattr(res, "is_error", False):
                        return res
                    return _noted(res, f"{_route_line(url, r)} It answered another question there; "
                                       f"this reply is the page you asked for.]")
            log_call("forward", f"{name}\t{json.dumps(args)}")
            res = await stock.call_tool(name, args)
            if url and not getattr(res, "is_error", False) and (note := _others(url)):
                return _noted(res, note, after=True)
            return res

        info = init.server_info
        server = Server(info.name, version=info.version, instructions=init.instructions,
                        on_list_tools=list_tools, on_call_tool=call_tool)
        async with stdio_server() as (r, w):
            await server.run(r, w, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())

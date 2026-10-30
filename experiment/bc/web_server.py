"""MCP server `web`: fetch and render, identical for both experiment arms.

With BC_ENFORCE=1 (--write enforced) each call is logged to BC_CALL_LOG and every
result ends with a note saying whether write would store a page card from this run.
"""
import sys, pathlib, re, os
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from mcp.server.mcpserver import MCPServer
from bc.common import ENC, fetch_clean, render_clean, log_call, call_counts, card_block, stored_site_records

# Claude Code moves any tool result over ~50 KB into a file the agent cannot read,
# so each reply stays under both limits and says where to continue.
MAX_TOKENS = 10000
MAX_CHARS = 36000
ENFORCE = os.environ.get("BC_ENFORCE") == "1"
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


def _card_note(url: str, reply: str) -> str:
    if not ENFORCE:
        return reply
    why = card_block([url], stored_site_records(os.environ.get("BC_REGISTRY")), call_counts())
    return reply + (f"\n[breadcrumbs: write would not store a page card from this run: {why}]"
                    if why else "\n[breadcrumbs: write would store a page card from this run]")


@mcp.tool(structured_output=False)
def fetch(url: str, select: list[str] | None = None, section: str | None = None, start: int = 0) -> str:
    """Fetch a URL without running JavaScript. HTML is returned as cleaned Markdown;
    JSON, Markdown and plain text are returned as-is. For JSON, `select` keeps only
    the given dotted paths (e.g. ["crate.name", "versions.0.num"]). `section` (heading
    text or #anchor; a #fragment in the URL works too) returns only that section.
    Output is at most 10,000 tokens per call; longer results say which `start` to
    pass for the next part and list the page's headings."""
    if not section and "#" in url:
        url, section = url.split("#", 1)
    if ENFORCE:
        log_call("fetch", url)
    return _card_note(url, _fetch(url, select, section, start))


def _fetch(url, select, section, start) -> str:
    try:
        text, m = fetch_clean(url, select)
    except Exception as e:
        return f"[fetch failed: {type(e).__name__}: {e}]"
    head = f"HTTP {m['status']} {m['content_type']} {m['final_url']}"
    if not text.strip():
        return f"[{head}] (no text content; the page may need JavaScript: try render)"
    return _respond(text, head, section, start)


@mcp.tool(structured_output=False)
def render(url: str, section: str | None = None, start: int = 0) -> str:
    """Load a URL in headless Chrome (runs JavaScript, ~10-20 s), then return the
    cleaned Markdown. Use for pages that fetch returns empty. `section` and `start`
    work as in fetch; output is at most 10,000 tokens per call."""
    if not section and "#" in url:
        url, section = url.split("#", 1)
    if ENFORCE:
        log_call("render", url)
    return _card_note(url, _render(url, section, start))


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

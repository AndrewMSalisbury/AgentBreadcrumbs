"""Shared helpers: URL normalization, fetching, cleaning and token counting.

Both experiment arms get pages through these functions, so any saving comes
from breadcrumbs, not from better cleanup.
"""
import json, os, re, subprocess, tempfile
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

import httpx, tiktoken, trafilatura
from bs4 import BeautifulSoup
from markdownify import markdownify

ENC = tiktoken.get_encoding("o200k_base")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/141.0 Safari/537.36")
CHROME = os.environ.get("BC_CHROME", r"C:\Program Files\Google\Chrome\Application\chrome.exe")
TRACKING = re.compile(r"^(utm_.*|ref|ref_src|fbclid|gclid|mc_cid|mc_eid)$", re.I)


def tokens(s: str) -> int:
    return len(ENC.encode(s, disallowed_special=()))


def normalize_url(url: str) -> str:
    """Standard §6.2: lowercase host, no tracking params, no fragment, .md maps to its page."""
    if "://" not in url:
        url = "https://" + url
    p = urlsplit(url.strip())
    host = (p.hostname or "").lower()
    if p.port and p.port not in (80, 443):
        host += f":{p.port}"
    path = p.path or "/"
    if path.endswith(".md") and not path.endswith("/README.md"):
        path = path[:-3]
    if len(path) > 1:
        path = path.rstrip("/")
    query = urlencode([(k, v) for k, v in parse_qsl(p.query) if not TRACKING.match(k)])
    return urlunsplit(("https", host, path, query, ""))


def _fold_www(host: str) -> str:
    """Registry keys treat www.example.com and example.com as one site."""
    return host[4:] if host.startswith("www.") else host


def host_of(url_or_domain: str) -> str:
    s = url_or_domain.strip().lower()
    return _fold_www(urlsplit(s if "://" in s else "https://" + s).hostname or s)


def page_id(url: str) -> str:
    p = urlsplit(normalize_url(url))
    return ("page:" + _fold_www(p.netloc) + (p.path if p.path != "/" else "")
            + (f"?{p.query}" if p.query else ""))


def clean_html(html: str, url: str | None = None) -> str:
    """The page's main element as Markdown; trafilatura when there is none (it drops
    some tables, e.g. the os/pathlib table in the Python docs); plain text last."""
    soup = BeautifulSoup(html, "html.parser")
    main = soup.select_one("main, [role=main], article")
    if main:
        for t in main(["script", "style", "noscript", "svg", "nav", "button", "form"]):
            t.decompose()
        md = markdownify(str(main), heading_style="ATX")
        md = re.sub(r'(\]\([^)\s]*)\s+"[^"]*"\)', r"\1)", md)  # drop link titles
        md = re.sub(r"\n{3,}", "\n\n", md).strip()
        if md:
            return md
    md = trafilatura.extract(html, output_format="markdown", include_links=True,
                             include_tables=True, url=url) or ""
    if md.strip():
        return md
    for t in soup(["script", "style", "noscript", "svg"]):
        t.decompose()
    return re.sub(r"\s+", " ", soup.get_text(" ")).strip()


def select_json(data, paths: list[str]):
    """Keep only dotted paths, e.g. ['crate.name', 'versions.0.num']."""
    out = {}
    for path in paths:
        cur = data
        try:
            for part in path.split("."):
                cur = cur[int(part)] if isinstance(cur, list) else cur[part]
            out[path] = cur
        except (KeyError, IndexError, ValueError, TypeError):
            out[path] = None
    return out


def http_get(url: str) -> httpx.Response:
    with httpx.Client(follow_redirects=True, timeout=30, headers={"User-Agent": UA}) as c:
        return c.get(url)


def fetch_clean(url: str, select: list[str] | None = None) -> tuple[str, dict]:
    """Fetch a URL and return (text, meta). HTML is cleaned to Markdown; JSON and
    plain text/Markdown pass through (JSON optionally reduced to `select` paths)."""
    r = http_get(url)
    ctype = r.headers.get("content-type", "").split(";")[0].strip()
    meta = {"status": r.status_code, "final_url": str(r.url), "content_type": ctype,
            "raw_tokens": tokens(r.text)}
    if "json" in ctype or (r.text[:1] in "[{" and select):
        try:
            data = r.json()
            text = json.dumps(select_json(data, select) if select else data, ensure_ascii=False)
        except ValueError:
            text = r.text
    elif "html" in ctype:
        text = clean_html(r.text, str(r.url))
    else:
        text = r.text
    return text, meta


def render_clean(url: str, wait_ms: int = 10000) -> tuple[str, dict]:
    """Render with headless Chrome, then clean like fetch_clean."""
    with tempfile.TemporaryDirectory() as profile:
        p = subprocess.run(
            [CHROME, "--headless=new", "--disable-gpu", "--no-first-run",
             f"--user-data-dir={profile}", f"--user-agent={UA}",
             f"--virtual-time-budget={wait_ms}", "--dump-dom", url],
            capture_output=True, timeout=90, encoding="utf-8", errors="replace")
    html = p.stdout
    return clean_html(html, url), {"rendered_tokens": tokens(html)}


def cap(text: str, max_tokens: int) -> tuple[str, bool]:
    ids = ENC.encode(text, disallowed_special=())
    if len(ids) <= max_tokens:
        return text, False
    return ENC.decode(ids[:max_tokens]), True


# Harness-enforced write policy (enforced-*, miss-0.2+). The web server and a WebSearch
# hook append one line per call to BC_CALL_LOG; the registry reads it at write time.
CALL_LOG = os.environ.get("BC_CALL_LOG")
# miss-0.5: page cards need the run's fetches to have returned this many tokens in all.
MIN_PULL = int(os.environ.get("BC_MIN_PULL") or 0)
# miss-0.8: page cards need this many web calls (fetches, renders and, if counted, searches).
MIN_CALLS = int(os.environ.get("BC_MIN_CALLS") or 0)
# miss-0.9: a lookup that misses sends only SITE_NOTE; the fetch that passes the card bar
# carries CARD_NOTE, so runs that never pass it don't pay for the page-card instructions.
DEFER = os.environ.get("BC_DEFER") == "1"
SITE_NOTE = """

[breadcrumbs: the registry has nothing for this. If you learn how to get content from any page on the site (an API or raw-source URL pattern with {{name}} in it, Markdown versions, JavaScript needed), write a site record before answering. A fetch result will say if a page card is wanted too. Use schema "0.2" and provenance {{"writer": "{writer}", "observed_at": "{today}"}}.]"""
# miss-0.11: miss-0.9's note drew site records that only said a plain fetch works.
SITE_STRICT = os.environ.get("BC_SITE_STRICT") == "1"
SITE_NOTE_STRICT = """

[breadcrumbs: the registry has nothing for this. Write a site record before answering only if you found something a later agent would not get from a plain fetch of the page: an API or raw-source URL pattern with {{name}} in it, Markdown versions of pages, or that pages need JavaScript. Not that a plain fetch or the section parameter works: that is true of most sites. A fetch result will say if a page card is wanted too. Use schema "0.2" and provenance {{"writer": "{writer}", "observed_at": "{today}"}}.]"""
CARD_NOTE = """
[breadcrumbs: this run has now taken {taken}, so write would store a page card from it: write one before answering, for the page that held the answer. A card records the cheapest way to get the page's content, not your answer:
  - route.url: the smallest source you found with the page's content: a raw source file, an API endpoint, a Markdown version, or the page itself if nothing smaller exists.
  - route.select, route.section, route.start: fetch arguments that worked on route.url, if you used any; route.tokens: roughly how large the result was.
  - route.notes: what did not work and why (e.g. section= fails because entries are not headings).
  - answers: the topics the whole page covers, not your question. No values anywhere in the card.
Use schema "0.2" and provenance {{"writer": "{writer}", "observed_at": "{today}"}}.]"""
PATTERN_URL = re.compile(r"https?://[^\s\"'<>()]*\{[^}]+\}[^\s\"'<>()]*")


def log_call(kind: str, detail: str, path: str | None = CALL_LOG) -> None:
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"{kind}\t{detail}\n")


def call_counts(path: str | None = CALL_LOG) -> dict:
    counts = {"fetch": 0, "search": 0, "tokens": 0}
    try:
        lines = open(path, encoding="utf-8").read().splitlines() if path else []
    except FileNotFoundError:
        lines = []
    for line in lines:
        kind, *rest = line.split("\t")
        counts["search" if kind == "search" else "fetch"] += kind in ("fetch", "render", "search")
        if kind in ("fetch", "render") and len(rest) > 1 and rest[1].isdigit():
            counts["tokens"] += int(rest[1])
    return counts


def _bare(url: str) -> str:
    """Scheme, www. and trailing slash dropped, so URLs and patterns compare as text."""
    s = re.sub(r"^https?://(www\.)?", "", url.strip().lower())
    return s.split("#")[0].rstrip("/")


def url_patterns(site_record: dict) -> list[str]:
    """URL patterns with {placeholders} anywhere in a site record's access notes."""
    return [m.rstrip(".,;:") for s in site_record.get("access", {}).values() if isinstance(s, str)
            for m in PATTERN_URL.findall(s)]


def pattern_covers(pattern: str, url: str) -> bool:
    """{name} fills one path segment; a placeholder that says it is a path
    (e.g. {group path with slashes}) may span several."""
    rx, pos, pat = "", 0, _bare(pattern)
    for m in re.finditer(r"\{([^}]*)\}", pat):
        rx += re.escape(pat[pos:m.start()]) + ("[^?#]+?" if re.search("path|slash", m[1]) else "[^/?#]+")
        pos = m.end()
    return bool(re.fullmatch(rx + re.escape(pat[pos:]), _bare(url).split("?")[0]))


def card_block(urls: list[str], site_records: list[dict], counts: dict, searches: bool = True) -> str | None:
    """Why a page card from this run would not be stored, or None if it would.
    searches=False (miss-0.2): only fetches and renders make a run eligible."""
    if counts["fetch"] <= 1 and not (searches and counts["search"]):
        if not searches:
            return (f"this run took {counts['fetch']} fetch{'es' if counts['fetch'] != 1 else ''} or render, "
                    "so a later agent gets the page as cheaply without a card")
        return (f"this run took {counts['fetch']} fetch{'es' if counts['fetch'] != 1 else ''} and no search, "
                "so a later agent gets the page as cheaply without a card")
    calls = counts["fetch"] + (counts["search"] if searches else 0)
    if calls < MIN_CALLS:
        return (f"this run took {calls} web call{'s' if calls != 1 else ''}, fewer than {MIN_CALLS}, "
                "so a card would save a later agent less than writing it costs")
    if counts["tokens"] < MIN_PULL:
        return (f"this run's fetches returned {counts['tokens']} tokens in all, "
                "so a later agent gets the page as cheaply without a card")
    for rec in site_records:
        for p in url_patterns(rec):
            if any(u and pattern_covers(p, u) for u in urls):
                return f"the site record for {rec['site']} already has the URL pattern {p}"
    return None


def stored_site_records(db_path: str | None) -> list[dict]:
    import sqlite3
    if not db_path or not os.path.exists(db_path):
        return []
    with sqlite3.connect(db_path) as db:
        try:
            return [json.loads(r) for (r,) in db.execute("SELECT record FROM sites")]
        except sqlite3.OperationalError:  # registry not created yet
            return []

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


def host_of(url_or_domain: str) -> str:
    s = url_or_domain.strip().lower()
    return urlsplit(s if "://" in s else "https://" + s).hostname or s


def page_id(url: str) -> str:
    p = urlsplit(normalize_url(url))
    return "page:" + p.netloc + (p.path if p.path != "/" else "") + (f"?{p.query}" if p.query else "")


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

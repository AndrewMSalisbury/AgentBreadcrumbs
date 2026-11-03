"""How concentrated AI-agent requests are on a docs site's pages, from its own access logs.

Run by a site owner. A shared breadcrumb registry pays when agents keep landing on the same
pages, so this measures, for agent traffic and for human traffic beside it:
  - the share of requests on the site's top 1%, 10% and 25% of pages (ranked within that traffic)
  - the share of pages fetched by 2+ and 5+ distinct clients, and the requests on them
  - the share of requests for a page a different client of the same kind fetched earlier:
    the requests a registry could have served from someone else's breadcrumb
Clients are an IP address and user agent together. Pages are the request path with the query,
fragment, trailing slash and .md/.html/index.html suffixes removed, so /x, /x/ and /x.md count
as one page. Only GET requests with status below 400 count, and static assets, robots.txt and
sitemaps are left out (llms.txt is kept and reported on its own line).

Traffic classes, from the user agent (first match wins):
  crawler      training and search crawlers (GPTBot, ClaudeBot, Googlebot, ...): left out
  agent        assistants fetching for a user (Claude-User, ChatGPT-User, Perplexity-User, ...)
  http-client  generic HTTP libraries and command-line tools (curl, python-requests, axios,
               node-fetch, ...): where coding agents that shell out show up, mixed with scripts
  human        everything else with a browser user agent
  other        the rest: left out

Prints aggregate counts only: no paths, page names, IP addresses or user agents. Named agents
are counted by product name (e.g. ChatGPT-User), which is not specific to any visitor.

Reads nginx/Apache common or combined logs, Cloudflare Logpush JSON lines, and CloudFront or
other W3C logs with a #Fields header. Files may be gzipped. The format is detected per file.

  python agent_concentration.py LOG [LOG ...]
"""
import argparse, collections, datetime, gzip, json, pathlib, re, sys
from urllib.parse import unquote, urlsplit

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("logs", nargs="+", type=pathlib.Path)
args = ap.parse_args()

# Order matters: crawlers before agents, so "ClaudeBot" isn't caught by a looser pattern.
CRAWLER = re.compile(r"GPTBot|OAI-SearchBot|ClaudeBot|Claude-SearchBot|anthropic-ai|PerplexityBot|"
                     r"Google-Extended|Googlebot|bingbot|Applebot|Bytespider|CCBot|Amazonbot|meta-externalagent|"
                     r"FacebookBot|YandexBot|Baiduspider|DuckDuckBot|AhrefsBot|SemrushBot|MJ12bot|DotBot|"
                     r"PetalBot|cohere-ai|Diffbot|YouBot|Timpibot|ImagesiftBot|Omgili|bot\b|crawler|spider", re.I)
AGENTS = [("Claude-User", r"Claude-User"), ("ChatGPT-User", r"ChatGPT-User"),
          ("Perplexity-User", r"Perplexity-User"), ("MistralAI-User", r"MistralAI-User"),
          ("Gemini", r"Google-Agent|Gemini-Deep-Research|GoogleAgent"), ("DuckAssistBot", r"DuckAssistBot"),
          ("Cursor", r"Cursor"), ("Devin", r"Devin"), ("Copilot", r"Copilot|GitHub-Copilot"),
          ("other AI agent", r"\bAI ?Agent\b|-User/\d")]
AGENTS = [(n, re.compile(p, re.I)) for n, p in AGENTS]
HTTP_CLIENT = re.compile(r"^(curl|Wget|python-requests|python-httpx|Python-urllib|aiohttp|axios|node-fetch|"
                         r"undici|got|Go-http-client|okhttp|Java/|Apache-HttpClient|libwww-perl|httpie|"
                         r"Ruby|Faraday|reqwest|Deno|Bun|node)\b", re.I)
BROWSER = re.compile(r"Mozilla/5\.0 .*(Chrome|Firefox|Safari|Edg)/", re.I)
ASSET = re.compile(r"\.(css|js|mjs|map|png|jpe?g|gif|svg|webp|avif|ico|woff2?|ttf|otf|eot|mp4|webm|pdf|zip|"
                   r"json|xml|txt|wasm)$|^/(robots\.txt|sitemap[^/]*|favicon[^/]*|_next/|static/|assets/)", re.I)
SUFFIX = re.compile(r"(/index)?\.(md|mdx|html?)$", re.I)

COMBINED = re.compile(r'^(\S+) \S+ \S+ \[([^\]]+)\] "(\S+) (\S+)[^"]*" (\d{3}) \S+(?: "[^"]*" "([^"]*)")?')
JSON_KEYS = {"ip": ("ClientIP", "client_ip", "remote_addr", "ip"),
             "path": ("ClientRequestURI", "ClientRequestPath", "request_uri", "path", "uri"),
             "method": ("ClientRequestMethod", "method", "request_method"),
             "status": ("EdgeResponseStatus", "OriginResponseStatus", "status"),
             "ua": ("ClientRequestUserAgent", "user_agent", "http_user_agent", "ua"),
             "time": ("EdgeStartTimestamp", "timestamp", "time", "@timestamp")}


def classify(ua: str) -> str:
    if not ua or ua == "-":
        return "other"
    if CRAWLER.search(ua):
        return "crawler"
    for name, pat in AGENTS:
        if pat.search(ua):
            return "agent:" + name
    if HTTP_CLIENT.search(ua):
        return "http-client"
    return "human" if BROWSER.search(ua) else "other"


def page_of(target: str) -> str | None:
    path = unquote(urlsplit(target).path or "/")
    if ASSET.search(path) and not path.lower().endswith("llms.txt"):
        return None
    path = SUFFIX.sub("", path).rstrip("/") or "/"
    return path


def when(v) -> float:
    """Seconds since the epoch, from the timestamp shapes these log formats use; 0 if unknown."""
    if isinstance(v, (int, float)) or (isinstance(v, str) and v.isdigit()):
        n = float(v)
        return n / 1e9 if n > 1e15 else n / 1e3 if n > 1e12 else n
    for fmt in ("%d/%b/%Y:%H:%M:%S %z", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%d %H:%M:%S"):
        try:
            t = datetime.datetime.strptime(str(v).replace("Z", "+0000"), fmt)
            return (t if t.tzinfo else t.replace(tzinfo=datetime.timezone.utc)).timestamp()
        except ValueError:
            pass
    return 0.0


def records(path: pathlib.Path):
    """(time, ip, method, target, status, ua) for each request line the file's format can parse."""
    opener = gzip.open if path.suffix == ".gz" else open
    fields = None
    with opener(path, "rt", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith("#Fields:"):
                fields = line.split()[1:]
                continue
            if not line or line.startswith("#"):
                continue
            if line.startswith("{"):
                try:
                    o = json.loads(line)
                except ValueError:
                    continue
                g = lambda k: next((o[a] for a in JSON_KEYS[k] if a in o), None)
                yield when(g("time") or 0), g("ip"), g("method") or "GET", g("path"), int(g("status") or 0), g("ua") or ""
            elif fields:
                v = dict(zip(fields, line.split("\t") if "\t" in line else line.split()))
                yield (when(f"{v.get('date', '')} {v.get('time', '')}"), v.get("c-ip"), v.get("cs-method", "GET"),
                       v.get("cs-uri-stem"), int(v.get("sc-status") or 0), unquote(v.get("cs(User-Agent)", "")))
            elif m := COMBINED.match(line):
                ip, t, method, target, status, ua = m.groups()
                yield when(t), ip, method, target, int(status), ua or ""


# Pages and clients are interned to ints, so nothing readable is kept past parsing.
page_ids, client_ids = {}, {}
rows = []  # (time, class, page id, client id)
parsed = 0
agent_names = collections.Counter()
llms = collections.Counter()
for log in args.logs:
    before = parsed
    for t, ip, method, target, status, ua in records(log):
        parsed += 1
        if method != "GET" or not target or not (100 <= status < 400):
            continue
        cls = classify(ua)
        if cls in ("crawler", "other"):
            continue
        page = page_of(target)
        if page is None:
            continue
        if cls.startswith("agent:"):
            agent_names[cls[6:]] += 1
            cls = "agent"
        if page.lower().endswith("llms.txt") or page.lower().endswith("llms-full.txt"):
            llms[cls] += 1
        rows.append((t, cls, page_ids.setdefault(page, len(page_ids)),
                     client_ids.setdefault((ip, ua), len(client_ids))))
    if parsed == before:
        print(f"warning: no requests parsed from one input file ({log.suffix or 'no extension'})", file=sys.stderr)
rows.sort(key=lambda r: r[0])
page_ids = client_ids = None

times = [r[0] for r in rows if r[0]]
span = (max(times) - min(times)) / 86400 if times else 0
print(f"agent_concentration.py: {parsed} log lines parsed, {len(rows)} page requests kept, "
      f"span {span:.1f} days")
pct = lambda a, b: f"{100 * a / b:.1f}%" if b else "-"


def report(cls: str) -> None:
    rs = [r for r in rows if r[1] == cls]
    if not rs:
        print(f"\n{cls}: no requests")
        return
    by_page = collections.Counter(r[2] for r in rs)
    clients = collections.defaultdict(set)
    for r in rs:
        clients[r[2]].add(r[3])
    ranked = [n for _, n in by_page.most_common()]
    total, pages = len(rs), len(ranked)
    top = lambda share: sum(ranked[:max(1, round(pages * share))])
    # A request whose page another client of this class fetched before it. Two remembered
    # clients per page are enough to tell: if there are two, one of them isn't this one.
    seen_by = collections.defaultdict(set)
    from_other = 0
    for _, _, p, c in rs:
        from_other += bool(seen_by[p] - {c})
        if len(seen_by[p]) < 2:
            seen_by[p].add(c)
    multi = [p for p in by_page if len(clients[p]) >= 2]
    multi5 = [p for p in by_page if len(clients[p]) >= 5]
    print(f"\n{cls}: {total} requests, {pages} pages, {len({r[3] for r in rs})} clients")
    print(f"  requests on top 1% / 10% / 25% of pages: {pct(top(.01), total)} / {pct(top(.10), total)} / "
          f"{pct(top(.25), total)}")
    print(f"  requests on top 10 / 100 pages: {pct(sum(ranked[:10]), total)} / {pct(sum(ranked[:100]), total)}")
    print(f"  pages fetched by 2+ clients: {pct(len(multi), pages)}, holding {pct(sum(by_page[p] for p in multi), total)} "
          f"of requests; 5+ clients: {pct(len(multi5), pages)}, holding {pct(sum(by_page[p] for p in multi5), total)}")
    print(f"  requests for a page another {cls} client fetched earlier: {pct(from_other, total)}")
    if llms[cls]:
        print(f"  llms.txt requests: {pct(llms[cls], total)}")


for cls in ("agent", "http-client", "human"):
    report(cls)
if agent_names:
    print("\nagent requests by product: " + ", ".join(f"{n} {k}" for n, k in agent_names.most_common()))
# Where agent demand sits in human traffic: the share of agent requests on the humans' top 10% of pages.
human = collections.Counter(r[2] for r in rows if r[1] == "human")
agent = [r[2] for r in rows if r[1] == "agent"]
if human and agent:
    top_human = {p for p, _ in human.most_common(max(1, round(len(human) * .10)))}
    print(f"agent requests on the human top 10% of pages: {pct(sum(p in top_human for p in agent), len(agent))}; "
          f"on pages no human fetched: {pct(sum(p not in human for p in agent), len(agent))}")

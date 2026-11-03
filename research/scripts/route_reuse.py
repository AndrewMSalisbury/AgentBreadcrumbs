"""Count web lookups that could reuse a route an earlier lookup found, in local Claude Code transcripts.

A breadcrumb saves when a lookup has something to skip (2+ web calls) and an earlier lookup
reached the same page or site and could have left a record: a page card needs 2+ web calls and
2,000+ result tokens (miss-0.7's bar), a site record can come from any lookup. Failures are not
required. Lookups are as in lookups_local.py: a run of web calls that ends at the next user
message or after GAP non-web tool calls in a row.

The first section prints aggregate counts only: no text, URLs, queries, domains, pages or project
names. The second section is for matching across machines, and the person running it reviews it
before sending: one line per domain, readable, and one per page, as a salted hash every machine
computes the same way. Query strings, fragments, local hosts and IP addresses are never printed.

  python route_reuse.py [ROOT ...]   (default: every ~/.claude*/projects, plus $CLAUDE_CONFIG_DIR/projects)
"""
import collections, hashlib, ipaddress, json, os, pathlib, statistics, sys
from datetime import datetime
from urllib.parse import urlparse

GAP = 3
MIN_CALLS, MIN_PULL = 2, 2000
FETCH_SUFFIX = ("__navigate", "__get_page_text", "__read_page", "__fetch", "__render")

src = pathlib.Path(__file__).read_bytes().replace(b"\r", b"")
print(f"route_reuse.py sha256 {hashlib.sha256(src).hexdigest()[:16]}")

roots = [pathlib.Path(a) for a in sys.argv[1:]]
if not roots:
    roots = sorted(pathlib.Path.home().glob(".claude*/projects"))
    if os.environ.get("CLAUDE_CONFIG_DIR"):
        roots.append(pathlib.Path(os.environ["CLAUDE_CONFIG_DIR"]) / "projects")
    roots = list(dict.fromkeys(r.resolve() for r in roots))
print(f"config folders {len(roots)}")


def kind(name):
    if name == "WebSearch":
        return "search"
    if name == "WebFetch" or name.endswith(FETCH_SUFFIX):
        return "fetch"
    return None


def page_of(url):
    try:
        p = urlparse(url)
        host = (p.hostname or "").lower()
    except ValueError:
        return None
    if not host:
        return None
    host = host[4:] if host.startswith("www.") else host
    return host, host + (p.path.rstrip("/") or "")


def chars(c):
    return len(c) if isinstance(c, str) else sum(len(x.get("text", "")) for x in c or [] if isinstance(x, dict))


def when(ts):
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return None


lookups, seen_files, dupes, subagent_files, times = [], set(), 0, 0, []
all_result_tok = 0
for root in roots:
    for f in sorted(root.rglob("*.jsonl")) if root.is_dir() else []:
        key = f.relative_to(root).as_posix()
        if key in seen_files:  # the same session copied under two config folders
            dupes += 1
            continue
        seen_files.add(key)
        sid = len(seen_files)
        subagent_files += "subagents" in f.parts
        calls, results, order, last_page = {}, set(), [], None
        for line in f.open(encoding="utf-8", errors="replace"):
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            if not isinstance(ev, dict):
                continue
            msg = ev.get("message") or {}
            content = msg.get("content") if isinstance(msg, dict) else None
            ts = ev.get("timestamp") or ""
            t = when(ts)
            if t:
                times.append(t)
            if ev.get("type") == "assistant":
                for b in content if isinstance(content, list) else []:
                    if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("id") not in calls:
                        name = b.get("name", "")
                        k = kind(name)
                        url = (b.get("input") or {}).get("url", "") if k == "fetch" else ""
                        pg = page_of(url) if isinstance(url, str) and url else None
                        if k == "fetch" and not url:
                            pg = last_page  # a browser read is on the page the last navigate loaded
                        elif pg and name.endswith("__navigate"):
                            last_page = pg
                        calls[b["id"]] = {"k": k, "pg": pg, "tok": 0, "t": ts}
                        order.append(b["id"])
            elif ev.get("type") == "user":
                if isinstance(content, str) or (isinstance(content, list) and any(
                        isinstance(b, dict) and b.get("type") == "text" for b in content)):
                    order.append(None)  # a real user message ends the lookup
                for b in content if isinstance(content, list) else []:
                    if isinstance(b, dict) and b.get("type") == "tool_result" and b.get("tool_use_id") not in results:
                        results.add(b.get("tool_use_id"))
                        n = chars(b.get("content")) // 4
                        all_result_tok += n
                        c = calls.get(b.get("tool_use_id"))
                        if c and c["k"]:
                            c["tok"] += n

        cur, since = [], 0

        def close():
            if cur:
                lookups.append({"s": sid, "t": cur[0]["t"], "n": len(cur),
                                "nf": sum(c["k"] == "fetch" for c in cur), "tok": sum(c["tok"] for c in cur),
                                "pages": {c["pg"][1] for c in cur if c["pg"]},
                                "doms": {c["pg"][0] for c in cur if c["pg"]}})

        for cid in order:
            if cid is None:
                close(); cur, since = [], 0
                continue
            c = calls[cid]
            if c["k"]:
                cur.append(c); since = 0
            else:
                since += 1
                if cur and since >= GAP:
                    close(); cur, since = [], 0
        close()

# ---- aggregate, in time order across all transcripts ----
L = sorted(lookups, key=lambda l: l["t"])
for l in L:
    l["card"] = l["n"] >= MIN_CALLS and l["tok"] >= MIN_PULL
    l["multi"] = l["n"] >= MIN_CALLS

page_by, dom_by = collections.defaultdict(list), collections.defaultdict(list)
for l in L:
    pe = [e for p in l["pages"] for e in page_by[p]]
    de = [e for d in l["doms"] for e in dom_by[d]]
    l["page_any"] = bool(pe)
    l["dom_any"] = bool(de)
    l["page_card_x"] = any(card and s != l["s"] for s, card in pe)
    l["page_card_s"] = any(card and s == l["s"] for s, card in pe)
    l["dom_x"] = any(s != l["s"] for s, _ in de)
    for p in l["pages"]:
        page_by[p].append((l["s"], l["card"]))
    for d in l["doms"]:
        dom_by[d].append((l["s"], l["card"]))

n = len(L)
web_tok = sum(l["tok"] for l in L)
pct = lambda a, b: f"{100 * a / b:.0f}%" if b else "-"
med = lambda xs: f"{statistics.median(xs):,.0f}" if xs else "-"


def row(label, sel):
    xs = [l for l in L if sel(l)]
    tok = sum(l["tok"] for l in xs)
    print(f"  {label}: {len(xs)} ({pct(len(xs), n)} of lookups, {pct(tok, web_tok)} of web-result tokens)")


span = (max(times) - min(times)).days if times else 0
print(f"transcripts {len(seen_files)} ({subagent_files} subagent), duplicates skipped {dupes}, span {span} days")
print(f"transcripts with a lookup {len({l['s'] for l in L})}")
print(f"lookups {n} (GAP={GAP}), web calls {sum(l['n'] for l in L)}: "
      f"{sum(l['nf'] for l in L)} fetches, {sum(l['n'] - l['nf'] for l in L)} searches")
h = collections.Counter(min(l["n"], 6) for l in L)
print("web calls per lookup 1/2/3/4/5/6+: " + " / ".join(str(h[k]) for k in range(1, 7)))
print(f"web-result tokens (chars/4): total {web_tok:,} = {pct(web_tok, all_result_tok)} of all tool-result tokens; "
      f"per lookup median {med([l['tok'] for l in L])}, "
      f"1-call median {med([l['tok'] for l in L if l['n'] == 1])}, "
      f"2+-call median {med([l['tok'] for l in L if l['multi']])}")
print("lookup classes:")
row("2+ web calls", lambda l: l["multi"])
row(f"card-eligible (2+ web calls and {MIN_PULL:,}+ result tokens)", lambda l: l["card"])
row("with a fetch whose page is known", lambda l: bool(l["pages"]))
print("repeats (an earlier lookup, any size):")
row("same page, any session", lambda l: l["page_any"])
row("same domain, any session", lambda l: l["dom_any"])
print("savable (this lookup has 2+ web calls, and an earlier lookup could have left a record):")
row("same page, earlier card-eligible lookup in another session", lambda l: l["multi"] and l["page_card_x"])
row("same page, earlier card-eligible lookup in the same session only",
    lambda l: l["multi"] and l["page_card_s"] and not l["page_card_x"])
row("same domain, earlier lookup in another session", lambda l: l["multi"] and l["dom_x"])
ps = collections.Counter(len({s for s, _ in v}) for v in page_by.values())
ds = collections.Counter(len({s for s, _ in v}) for v in dom_by.values())
print(f"distinct pages {len(page_by)}, in 2+ sessions {sum(c for k, c in ps.items() if k > 1)}; "
      f"distinct domains {len(dom_by)}, in 2+ sessions {sum(c for k, c in ds.items() if k > 1)}")

# ---- matching section: per domain and per hashed page, for pooling across machines ----
SALT = b"agentbreadcrumbs-route-reuse-1"  # the same on every machine, so page hashes match


def local(d):
    try:
        ipaddress.ip_address(d.strip("[]"))
        return True
    except ValueError:
        return d == "localhost" or "." not in d or d.endswith((".local", ".localhost", ".internal", ".lan", ".home"))


stats = collections.defaultdict(lambda: [0, 0, 0, set()])  # key -> lookups, 2+ calls, card-eligible, sessions
for l in L:
    for k in [("D", d) for d in l["doms"]] + [("P", p) for p in l["pages"]]:
        st = stats[k]
        st[0] += 1; st[1] += l["multi"]; st[2] += l["card"]; st[3].add(l["s"])
doms = sorted(d for t, d in stats if t == "D")
print()
print("--- matching section: review before sending. To withhold a site, delete its D line and the P lines under it. ---")
print(f"local or IP hosts left out: {sum(local(d) for d in doms)}")
fmt = lambda st: f"lookups={st[0]} multi={st[1]} card={st[2]} sessions={len(st[3])}"
for d in doms:
    if local(d):
        continue
    print(f"D {d} {fmt(stats[('D', d)])}")
    for p in sorted(p for t, p in stats if t == "P" and p.split("/", 1)[0] == d):
        print(f"  P {hashlib.sha256(SALT + p.encode()).hexdigest()[:12]} {fmt(stats[('P', p)])}")

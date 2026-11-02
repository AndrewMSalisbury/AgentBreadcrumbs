"""Count web fetches that fail or come back near-empty in local Claude Code transcripts,
and what agents do after them.

Measures demand for site access knowledge: how often an agent hits a page it can't read
(blocked, gone, JavaScript-only or empty, too large), how many web calls the lookup
spends after that, and whether the same site fails again in another session (a breadcrumb
only pays if it does). Lookups are defined as in lookups_local.py. Each tool call is
counted once by its id, since a transcript can repeat a message over several lines.

Prints aggregate counts only: no text, URLs, queries, domains or project names. Domains
are used in memory to count repeats and are never printed.

  python access_failures.py ROOT [ROOT ...] [--gap N]
"""
import argparse, collections, json, pathlib, re, statistics
from urllib.parse import urlparse

ap = argparse.ArgumentParser()
ap.add_argument("roots", nargs="+", type=pathlib.Path)
ap.add_argument("--gap", type=int, default=3)
args = ap.parse_args()

FETCH_SUFFIX = ("__navigate", "__get_page_text", "__read_page", "__fetch", "__render")
EMPTY_CHARS = 200  # a browser page read shorter than this is treated as empty

# Order matters: the first class whose pattern matches wins.
CLASSES = [
    ("blocked", re.compile(r"HTTP (401|403|429|451)\b|access denied|captcha|are you a robot|"
                           r"verify you are human|enable cookies|cloudflare", re.I)),
    ("gone", re.compile(r"HTTP (404|410)\b|page not found|no longer available|does not exist", re.I)),
    ("too_large", re.compile(r"maxContentLength|content too large|exceeds? (the )?maximum", re.I)),
    ("server_error", re.compile(r"HTTP 5\d\d\b|timed? ?out|ECONN|ENOTFOUND|socket hang up|"
                                r"unable to fetch|failed to fetch", re.I)),
    ("redirect", re.compile(r"REDIRECT DETECTED")),
    ("js_or_empty", re.compile(r"requires? javascript|enable javascript|javascript (is )?(disabled|required)|"
                               r"content (provided )?is (incomplete|empty|minimal)|only (contains|shows|includes) "
                               r"(the )?(navigation|header|footer|title|menu)|no (main |substantive )?content|"
                               r"page (appears to be|is) (empty|blank)|cannot (determine|find|provide|extract)"
                               r".{0,60}(page|content)|only (been )?(provided|given|shows?|contains?) (with )?"
                               r"(a |the )?(page )?title", re.I)),
]


def kind(name):
    if name == "WebSearch":
        return "search"
    if name == "WebFetch" or name.endswith(FETCH_SUFFIX):
        return "fetch"
    return None


def text_of(c):
    return c if isinstance(c, str) else " ".join(x.get("text", "") for x in c or [] if isinstance(x, dict))


def classify(name, res, is_error):
    head = res[:400].replace("*", "")  # failure messages and summarizer complaints open the result
    for label, pat in CLASSES:
        if pat.search(head):
            return label
    if name.endswith(("__get_page_text", "__read_page")) and len(res) < EMPTY_CHARS:
        return "js_or_empty"
    if is_error:
        return "other_error"
    return None


def domain(url):
    try:
        host = urlparse(url).hostname or ""
    except ValueError:
        return ""
    return host[4:] if host.startswith("www.") else host


sessions = []
for root in args.roots:
    for f in sorted(root.rglob("*.jsonl")):
        calls = {}      # tool_use id -> [kind, name, domain, failure class or None]
        order = []      # (tool_use id or None for a user message / non-web call) in transcript order
        for line in f.open(encoding="utf-8", errors="replace"):
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            msg = ev.get("message") or {}
            content = msg.get("content")
            if ev.get("type") == "assistant":
                for b in content if isinstance(content, list) else []:
                    if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("id") not in calls:
                        name = b.get("name", "")
                        url = (b.get("input") or {}).get("url", "")
                        calls[b["id"]] = [kind(name), name, domain(url) if url else "", None]
                        order.append(("call", b["id"]))
            elif ev.get("type") == "user":
                if isinstance(content, str) or (isinstance(content, list) and any(
                        isinstance(b, dict) and b.get("type") == "text" for b in content)):
                    order.append(("user", None))
                for b in content if isinstance(content, list) else []:
                    if isinstance(b, dict) and b.get("type") == "tool_result":
                        c = calls.get(b.get("tool_use_id"))
                        if c and c[0] == "fetch" and c[3] is None:
                            c[3] = classify(c[1], text_of(b.get("content")), b.get("is_error")) or ""

        # Split web calls into lookups, as lookups_local.py does.
        lookups, cur, since = [], [], 0
        for ev, cid in order:
            if ev == "user":
                if cur:
                    lookups.append(cur); cur = []
                continue
            c = calls[cid]
            if c[0]:
                cur.append(c); since = 0
            else:
                since += 1
                if cur and since >= args.gap:
                    lookups.append(cur); cur = []
        if cur:
            lookups.append(cur)
        sessions.append(lookups)

# ---- aggregate ----
looks = [l for s in sessions for l in s]
fetches = [c for l in looks for c in l if c[0] == "fetch"]
fails = [c for c in fetches if c[3]]
by_class = collections.Counter(c[3] for c in fails)
ACCESS = {"blocked", "js_or_empty", "too_large"}  # what a site access record could fix

print(f"transcripts {len(sessions)}, with any web call {sum(1 for s in sessions if s)}")
print(f"lookups {len(looks)} (GAP={args.gap}), web calls {sum(map(len, looks))}: "
      f"{len(fetches)} fetches, {sum(map(len, looks)) - len(fetches)} searches")
print(f"failed fetches {len(fails)} ({100 * len(fails) / max(len(fetches), 1):.0f}% of fetches)")
for label, _ in CLASSES + [("other_error", None)]:
    print(f"  {label:13} {by_class[label]}")

hit = [l for l in looks if any(c[0] == "fetch" and c[3] for c in l)]
acc = [l for l in looks if any(c[0] == "fetch" and c[3] in ACCESS for c in l)]
clean = [l for l in looks if not any(c[0] == "fetch" and c[3] for c in l)]
med = lambda xs: statistics.median(xs) if xs else 0
print(f"lookups with a failed fetch {len(hit)} ({100 * len(hit) / max(len(looks), 1):.0f}%), "
      f"with an access failure (blocked/js_or_empty/too_large) {len(acc)} ({100 * len(acc) / max(len(looks), 1):.0f}%)")


def after_first_fail(l, classes):
    i = next(i for i, c in enumerate(l) if c[0] == "fetch" and c[3] in classes)
    return l[i + 1:]


rest = [after_first_fail(l, ACCESS) for l in acc]
print(f"web calls per lookup: clean median {med([len(l) for l in clean])}, "
      f"with access failure median {med([len(l) for l in acc])}")
print(f"web calls after the first access failure: total {sum(map(len, rest))}, median {med([len(r) for r in rest])}")
print(f"after an access failure the lookup: switched to a browser tool {sum(any(c[1].startswith('mcp__') for c in r) for r in rest)}, "
      f"fetched again and succeeded {sum(any(c[0] == 'fetch' and not c[3] for c in r) for r in rest)}, "
      f"ended with no successful fetch {sum(not any(c[0] == 'fetch' and not c[3] for c in r) for r in rest)}")

# Repeats: does the same site fail with an access failure in more than one session?
dom_sessions = collections.defaultdict(set)
for i, s in enumerate(sessions):
    for l in s:
        for c in l:
            if c[0] == "fetch" and c[3] in ACCESS and c[2]:
                dom_sessions[c[2]].add(i)
n_dom = len(dom_sessions)
rep = [d for d, ss in dom_sessions.items() if len(ss) > 1]
print(f"domains with an access failure {n_dom}; failing in 2+ sessions {len(rep)}; "
      f"failures a breadcrumb from an earlier session could cover "
      f"{sum(len(dom_sessions[d]) - 1 for d in rep)}")

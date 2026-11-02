"""Aggregate web-lookup counts and token shares in local Claude Code transcripts.

Same definitions as the developer's script (web call = WebSearch, WebFetch, or a browser
tool that loads or reads a page; a lookup ends at the next real user message or after GAP
non-web tool calls), plus token totals. Prints aggregate counts only: no text, URLs,
queries, domains or project names.

  python lookups_local.py ROOT [GAP]
"""
import collections, json, pathlib, statistics, sys

root, gap = pathlib.Path(sys.argv[1]), int(sys.argv[2]) if len(sys.argv) > 2 else 3
WEB_SUFFIX = ("WebSearch", "WebFetch", "__navigate", "__get_page_text", "__read_page", "__fetch", "__render")


def is_web(name: str) -> bool:
    return name in ("WebSearch", "WebFetch") or name.endswith(WEB_SUFFIX[2:])


sessions = []
for f in sorted(root.rglob("*.jsonl")):
    tok = tool_res_web = tool_res_all = 0
    seen_msg = set()
    calls, lookups, cur, since_web, names = 0, [], 0, 0, {}
    for line in f.open(encoding="utf-8", errors="replace"):
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        msg = ev.get("message") or {}
        if ev.get("type") == "assistant":
            mid = msg.get("id")
            u = msg.get("usage") or {}
            if mid not in seen_msg:  # one API response can be split over several lines
                seen_msg.add(mid)
                tok += sum(u.get(k, 0) or 0 for k in ("input_tokens", "cache_creation_input_tokens",
                                                       "cache_read_input_tokens", "output_tokens"))
            for b in msg.get("content") or []:
                if isinstance(b, dict) and b.get("type") == "tool_use":
                    names[b.get("id")] = b.get("name", "")
                    if is_web(b.get("name", "")):
                        calls += 1
                        cur += 1
                        since_web = 0
                    else:
                        since_web += 1
                        if cur and since_web >= gap:
                            lookups.append(cur); cur = 0
        elif ev.get("type") == "user":
            content = msg.get("content")
            if isinstance(content, str) or (isinstance(content, list) and any(
                    isinstance(b, dict) and b.get("type") == "text" for b in content)):
                if cur:  # a real user message ends the lookup
                    lookups.append(cur); cur = 0
            for b in content if isinstance(content, list) else []:
                if isinstance(b, dict) and b.get("type") == "tool_result":
                    c = b.get("content")
                    n = len(c) if isinstance(c, str) else sum(len(x.get("text", "")) for x in c or [] if isinstance(x, dict))
                    tool_res_all += n // 4
                    if is_web(names.get(b.get("tool_use_id"), "")):
                        tool_res_web += n // 4
    if cur:
        lookups.append(cur)
    sessions.append({"tokens": tok, "web_calls": calls, "lookups": lookups,
                     "web_result_tokens": tool_res_web, "all_result_tokens": tool_res_all})

n = len(sessions)
withweb = [s for s in sessions if s["web_calls"]]
looks = [l for s in sessions for l in s["lookups"]]
h = collections.Counter(min(l, 6) for l in looks)
tot = sum(s["tokens"] for s in sessions)
print(f"transcripts {n}, with any web call {len(withweb)} ({100 * len(withweb) / n:.0f}%)")
print(f"web calls {sum(s['web_calls'] for s in sessions)}, lookups {len(looks)} (GAP={gap})")
print("calls per lookup 1/2/3/4/5/6+: " + " / ".join(str(h[k]) for k in range(1, 7))
      + f"; single-call share {100 * h[1] / max(len(looks), 1):.0f}%")
print(f"session tokens (all, cached reads included): total {tot:,}, median {statistics.median(s['tokens'] for s in sessions):,.0f}")
print(f"web tool-result tokens (chars/4): {sum(s['web_result_tokens'] for s in sessions):,} "
      f"= {100 * sum(s['web_result_tokens'] for s in sessions) / max(sum(s['all_result_tokens'] for s in sessions), 1):.1f}% of all tool-result tokens")

import json, pathlib, tiktoken
enc = tiktoken.get_encoding("o200k_base"); t = lambda s: len(enc.encode(s))
card = {"url":"https://docs.stripe.com/rate-limits","tier":"L2",
 "answers":"Stripe API rate and concurrency limits, 429 handling, increase requests",
 "sections":{"#rate-limits":"limits table","#handle-limiting":"backoff advice"},
 "facts":[{"claim":"Global limit, live mode","value":"100 requests/second","section":"#rate-limits","quote":"Live mode ... 100 requests per second"},
          {"claim":"Global limit, sandbox","value":"25 requests/second","section":"#rate-limits","quote":"Sandbox ... 25 requests per second"}],
 "content_hash":"sha256:3f9a1c0e","provenance":{"writer":"claude-opus-5-5","observed_at":"2026-10-21","confirmations":0}}
yaml = """url: https://docs.stripe.com/rate-limits
tier: L2
answers: Stripe API rate and concurrency limits, 429 handling, increase requests
sections:
  "#rate-limits": limits table
  "#handle-limiting": backoff advice
facts:
  - claim: Global limit, live mode
    value: 100 requests/second
    section: "#rate-limits"
    quote: Live mode ... 100 requests per second
  - claim: Global limit, sandbox
    value: 25 requests/second
    section: "#rate-limits"
    quote: Sandbox ... 25 requests per second
content_hash: sha256:3f9a1c0e
provenance: {writer: claude-opus-5-5, observed_at: 2026-10-21, confirmations: 0}
"""
md = """## docs.stripe.com/rate-limits (L2, 2026-10-21, sha256:3f9a1c0e, claude-opus-5-5, 0 confirmations)
Answers: Stripe API rate and concurrency limits, 429 handling, increase requests
- #rate-limits: limits table
- #handle-limiting: backoff advice
Facts:
- Global limit, live mode: 100 requests/second (#rate-limits, "Live mode ... 100 requests per second")
- Global limit, sandbox: 25 requests/second (#rate-limits, "Sandbox ... 25 requests per second")
"""
out = pathlib.Path(__file__).parent.parent / "measurements" / "formats"; out.mkdir(exist_ok=True)
for name, fn, s in [("JSON pretty", "card_pretty.json", json.dumps(card, indent=2)), ("JSON minified", "card_min.json", json.dumps(card, separators=(",",":"))), ("YAML", "card.yaml", yaml), ("Markdown", "card.md", md)]:
    (out / fn).write_text(s, encoding="utf-8")
    print(f"{name:14}{t(s):>5}")

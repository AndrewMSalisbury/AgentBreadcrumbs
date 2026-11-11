"""Does a stored section answer the agent's question? (card-0.4, LOG 2026-11-11)

A card's section was found for an earlier question. When the agent's scrape carries a `query`
prompt, the wrapper has the new question, so before serving the section it ranks every chunk of
the page (the text between two headings) against the prompt with BM25 and serves the section only
if the best chunk lies inside it. No model call; the page is the 1-credit scrape the wrapper makes
anyway to cut the section.
"""
import math, re

from bc.web_server import _headings

WORD = re.compile(r"[a-z0-9][a-z0-9_.\-]*[a-z0-9]|[a-z0-9]")
STOP = set("""a an and are as at be by can do does for from has have how i if in into is it its of on or
that the their there this to was what when where which who why will with you your according docs
documentation page quote exact text sentence relevant answer value default set maximum minimum many much
number""".split())


def terms(text: str) -> list[str]:
    return [w for w in WORD.findall(text.lower().replace("\\_", "_")) if w not in STOP]


def chunks(text: str, size: int = 15, step: int = 5) -> list[tuple[int, int, str]]:
    """(first line, end line, text) for windows of `size` non-blank lines. Windows rather than
    heading chunks: a long stored section (git-gc's CONFIGURATION, MDN's Instance properties) is
    otherwise outscored by any short intro that repeats the prompt's words."""
    lines = text.splitlines()
    idx = [i for i, l in enumerate(lines) if l.strip()]
    out = []
    for s in range(0, max(1, len(idx) - size + step), step):
        w = idx[s:s + size]
        if w:
            out.append((w[0], w[-1] + 1, "\n".join(lines[i] for i in w)))
    return out


def section_span(text: str, want: str) -> tuple[int, int] | None:
    """The line range bc.web_server._section would return for `want`."""
    lines = text.splitlines()
    heads = _headings(lines)
    w = want.lstrip("#").strip().lower()
    hit = next((h for h in heads if w in (h[3].lower(), h[2].lower())), None) \
        or next((h for h in heads if w in h[2].lower() or w in h[3].lower()), None)
    if not hit:
        return None
    end = next((h[0] for h in heads if h[0] > hit[0] and h[1] <= hit[1]), len(lines))
    return hit[0], end


def rank(text: str, prompt: str, k1: float = 1.2, b: float = 0.75) -> list[tuple[float, int, int]]:
    """(BM25 score, first line, end line) per chunk, best first."""
    cs = chunks(text)
    docs = [terms(c[2]) for c in cs]
    q = set(terms(prompt))
    n, avg = len(docs), (sum(map(len, docs)) / len(docs) if docs else 1) or 1
    df = {t: sum(t in set(d) for d in docs) for t in q}
    out = []
    for (a, e, _), d in zip(cs, docs):
        s = 0.0
        for t in q:
            f = d.count(t)
            if f:
                idf = math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5))
                s += idf * f * (k1 + 1) / (f + k1 * (1 - b + b * len(d) / avg))
        out.append((s, a, e))
    return sorted(out, reverse=True)


NEAR = 0.8  # the section's best window must score at least this share of the page's best


def ratio(text: str, section: str, prompt: str) -> tuple[float | None, str]:
    """The section's best window score over the page's best for the prompt (None if unscorable), and why.
    A window counts as the section's when at least half of it lies inside the section."""
    span = section_span(text, section)
    if not span:
        return None, "section not found"
    r = rank(text, prompt)
    if not r or r[0][0] == 0:
        return None, "no prompt term on the page"
    inside = [x for x in r if min(x[2], span[1]) - max(x[1], span[0]) >= (x[2] - x[1]) / 2]
    sec = inside[0][0] if inside else 0.0
    return sec / r[0][0], f"section's best {sec:.1f} / page's best {r[0][0]:.1f} (line {r[0][1]}) = {sec / r[0][0]:.2f}"


def serves(text: str, section: str, prompt: str) -> tuple[bool, str]:
    """Whether the stored section holds (nearly) the page's best window for the prompt, and why."""
    x, why = ratio(text, section, prompt)
    return x is not None and x >= NEAR, why


def best(text: str, sections: list[str], prompt: str) -> tuple[str | None, str]:
    """worth-0.1: of several stored sections (pooled cards), the one that best serves the prompt, if any does."""
    scored = [(ratio(text, s, prompt), s) for s in sections]
    ok = sorted(((x, s, why) for (x, why), s in scored if x is not None and x >= NEAR), reverse=True)
    if ok:
        return ok[0][1], ok[0][2]
    return None, "; ".join(f"{s}: {why}" for (_, why), s in scored)

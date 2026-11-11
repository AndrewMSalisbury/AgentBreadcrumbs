"""Canonical URLs and heading trees for the hit-rate questions' answer pages.

  python hitrate/pages.py              # writes hitrate/pages.json

Each docs URL is followed through its redirects over plain HTTP (no credits), so http/https and
renamed paths (gha's using-workflows/... and reference/... for the same page) count as one page.
Each canonical page's headings come from the local fetch tool's Markdown (bc.common.fetch_clean,
bc.web_server._headings): (line, level, title, anchor). An answer's anchor is placed in the heading
it names, or, for an anchor that is not a heading (nginx's directive anchors), in the heading above
the line that carries it.
"""
import json, pathlib, re, sys

import httpx

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE.parent))
from bc.common import fetch_clean, page_id
from bc.web_server import _headings


def canonical(url: str, client: httpx.Client) -> str:
    try:
        r = client.get(url, follow_redirects=True, timeout=30)
        return str(r.url).split("#")[0]
    except Exception:
        return url


def anchor_lines(text: str) -> dict[str, int]:
    """Anchors that appear as link targets or ids on a line, with the first line they're on."""
    out = {}
    for i, line in enumerate(text.splitlines()):
        for a in re.findall(r"#([A-Za-z0-9_.:\-]+)\)", line) + re.findall(r'(?:id|name)="([^"]+)"', line):
            out.setdefault(a.lower(), i)
    return out


def main():
    rows = [json.loads(l) for l in (HERE / "questions.jsonl").read_text(encoding="utf-8").splitlines()]
    urls = sorted({r["doc_url"] for r in rows})
    out = json.loads((HERE / "pages.json").read_text(encoding="utf-8")) if (HERE / "pages.json").exists() else {}
    canon = out.setdefault("canonical", {})
    trees = out.setdefault("pages", {})
    with httpx.Client(headers={"User-Agent": "Mozilla/5.0 (research fetch)"}) as c:
        for u in urls:
            if u not in canon:
                canon[u] = canonical(u, c)
    for cu in sorted(set(canon.values())):
        pid = page_id(cu)
        if pid in trees:
            continue
        try:
            text, m = fetch_clean(cu)
        except Exception as e:
            trees[pid] = {"url": cu, "error": str(e)[:200]}
            continue
        heads = _headings(text.splitlines())
        trees[pid] = {"url": cu, "status": m.get("status"), "lines": len(text.splitlines()),
                      "heads": [list(h) for h in heads], "anchors": anchor_lines(text)}
        print(f"{len(heads):4} headings  {cu}")
    (HERE / "pages.json").write_text(json.dumps(out, ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"{len(canon)} urls -> {len(set(canon.values()))} canonical pages")


if __name__ == "__main__":
    main()

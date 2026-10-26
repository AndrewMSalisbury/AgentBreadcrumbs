import sys, pathlib, re, tiktoken, trafilatura
from bs4 import BeautifulSoup
from markdownify import markdownify

pages = pathlib.Path(sys.argv[1])
out = pathlib.Path(sys.argv[2]); out.mkdir(exist_ok=True)
enc = tiktoken.get_encoding("o200k_base")
tok = lambda s: len(enc.encode(s, disallowed_special=()))

print(f"{'page':14}{'raw_html':>10}{'naive_md':>10}{'text_only':>10}{'clean_md':>10}")
for f in sorted(pages.glob("*.html")):
    html = f.read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(html, "html.parser")
    for t in soup(["script", "style", "noscript", "svg"]):
        t.decompose()
    naive_md = re.sub(r"\n{3,}", "\n\n", markdownify(str(soup)))
    text = re.sub(r"\s+", " ", soup.get_text(" "))
    clean = trafilatura.extract(html, output_format="markdown", include_links=True,
                                include_tables=True, url=None) or ""
    (out / f"{f.stem}.md").write_text(clean, encoding="utf-8")
    print(f"{f.stem:14}{tok(html):>10,}{tok(naive_md):>10,}{tok(text):>10,}{tok(clean):>10,}")

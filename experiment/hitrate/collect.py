"""Real questions for the hit-rate curve (LOG 2026-11-11): Stack Overflow answers that link to a site's docs.

  python hitrate/collect.py            # writes hitrate/questions.jsonl

For each site, the top-voted Stack Overflow answers whose body links to the site's docs (Stack
Exchange API, search/excerpts, no key), then each answer's body, from which the first docs link is
kept with its anchor. An answer that links to the docs points at where its question's answer lives,
so each row is a question asked by someone, with its answer's page and section, and no question
written by us. Popular pages come up as often as people ask about them, which is the distribution
the curve needs. Content is CC BY-SA; rows keep the question's link.
"""
import html, json, pathlib, re, time

import httpx

HERE = pathlib.Path(__file__).parent
API = "https://api.stackexchange.com/2.3"
SITES = {
    "gha": "docs.github.com/en/actions",
    "mdn": "developer.mozilla.org/en-US/docs/Web",
    "git": "git-scm.com/docs",
    "nginx": "nginx.org/en/docs",
}
PER_SITE = 100
LINK = re.compile(r'href="(https?://[^"]+)"')


def get(path: str, **params) -> dict:
    for attempt in range(3):
        r = httpx.get(f"{API}/{path}", params={"site": "stackoverflow", **params}, timeout=60)
        d = r.json()
        if "backoff" in d:
            time.sleep(d["backoff"] + 1)
        if r.status_code == 200:
            return d
        time.sleep(5)
    raise RuntimeError(d.get("error_message"))


def answers(prefix: str) -> list[dict]:
    out, page = [], 1
    while len(out) < PER_SITE and page <= 3:
        d = get("search/excerpts", body=f'"{prefix}"', sort="votes", order="desc", pagesize=100, page=page)
        out += [x for x in d["items"] if x["item_type"] == "answer"]
        if not d.get("has_more"):
            break
        page += 1
    return out[:PER_SITE]


def bodies(ids: list[int]) -> dict[int, dict]:
    out = {}
    for i in range(0, len(ids), 100):
        d = get("answers/" + ";".join(map(str, ids[i:i + 100])), filter="withbody", pagesize=100)
        out.update({a["answer_id"]: a for a in d["items"]})
    return out


def main():
    rows = []
    for site, prefix in SITES.items():
        found = answers(prefix)
        full = bodies([a["answer_id"] for a in found])
        kept = 0
        for a in found:
            b = full.get(a["answer_id"])
            if not b:
                continue
            links = [html.unescape(u) for u in LINK.findall(b["body"]) if prefix in u]
            if not links:
                continue
            url = links[0]
            rows.append({"site": site, "question_id": a["question_id"], "answer_id": a["answer_id"],
                         "title": html.unescape(a["title"]), "score": a["score"],
                         "link": f"https://stackoverflow.com/a/{a['answer_id']}",
                         "doc_url": url.split("#")[0], "anchor": url.split("#")[1] if "#" in url else None,
                         "doc_links": len(set(links))})
            kept += 1
        print(f"{site}: {len(found)} answers, {kept} with a docs link")
    out = HERE / "questions.jsonl"
    out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    print(f"{len(rows)} rows -> {out}")


if __name__ == "__main__":
    main()

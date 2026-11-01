"""Shortlist niche libraries for the knowledge-gap probe (research/knowledge-gap-probe.md).

Criteria: 2k-50k weekly downloads, and first release in the 2 years before the probed
model's training cutoff. The lower bound keeps packages with real users and docs to
check answers against. Writes research/probe/niche_candidates.yaml: per ecosystem, up to
--per candidates in a seeded random order. Picks are then made by hand, in that order,
taking the first 2 per ecosystem that are importable libraries with docs and a changelog
(not CLIs, plugins, type stubs or add-ons to a library already in libraries.yaml).

  python research/scripts/pickniche.py --cutoff 2026-01 [--seed 1] [--per 15]

Sources: npm search (fixed query terms, weekly downloads in results), crates.io sorted
by recent downloads (90 days, scaled to a week), and the top-pypi-packages list (30
days, scaled to a week). First-release dates come from deps.dev for npm and PyPI and
from crates.io's created_at for crates. Families of 4+ packages sharing a name prefix are dropped (see take()).
"""
import argparse, collections, datetime, pathlib, random, re, sys, time, urllib.parse

import requests, yaml

PROBE = pathlib.Path(__file__).resolve().parents[1] / "probe"
UA = {"User-Agent": "agentbreadcrumbs knowledge-gap probe"}
LOW, HIGH = 2_000, 50_000
# npm has no list of all packages; these terms cover common library kinds.
NPM_TERMS = ("client", "sdk", "framework", "orm", "validation", "parser", "router", "state",
             "testing", "database", "http", "ai", "schema", "queue", "auth", "cache")


def get(url: str):
    for attempt in range(5):  # npm search and crates.io rate-limit bursts
        r = requests.get(url, headers=UA, timeout=60)
        if r.status_code != 429:
            break
        time.sleep(10 * (attempt + 1))
    r.raise_for_status()
    return r.json()


def first_release(system: str, name: str) -> str | None:
    try:
        vs = get(f"https://api.deps.dev/v3/systems/{system}/packages/{urllib.parse.quote(name, safe='')}")["versions"]
    except requests.RequestException:
        return None
    dates = [v["publishedAt"][:10] for v in vs if v.get("publishedAt")]
    return min(dates) if dates else None


def family(name: str) -> str:
    """npm scope, or the name before its first - or _ (ra_ap_*, livekit-plugins-*)."""
    return name.split("/")[0] if name.startswith("@") else re.split(r"[-_]", name.lower())[0]


def take(pool: list[dict], system: str | None, start: str, end: str, per: int, rng: random.Random) -> list[dict]:
    """Drop package families, shuffle, then keep candidates first released in [start, end] until `per`.

    A family is 4+ packages in the pool sharing a family() prefix: sub-crates of one
    workspace, plugins for one framework, one org's scoped packages. They are parts of a
    larger project, not niche libraries in their own right.
    """
    sizes = collections.Counter(family(c["name"]) for c in pool)
    pool = [c for c in pool if sizes[family(c["name"])] < 4]
    rng.shuffle(pool)
    out = []
    for c in pool:
        if system:
            c["first_released"] = first_release(system, c["name"])
        if c.get("first_released") and start <= c["first_released"] <= end:
            out.append(c)
            print(f"  {c['name']:<36} {c['first_released']}  weekly {c['weekly_downloads']}", file=sys.stderr)
            if len(out) == per:
                break
    return out


def npm_pool() -> list[dict]:
    seen = {}
    for term in NPM_TERMS:
        for start in range(0, 1000, 250):
            objs = get(f"https://registry.npmjs.org/-/v1/search?text={term}&size=250&from={start}")["objects"]
            for o in objs:
                w = o.get("downloads", {}).get("weekly", 0)
                if LOW <= w <= HIGH and not o["package"]["name"].startswith("@types/"):
                    seen[o["package"]["name"]] = {"name": o["package"]["name"], "weekly_downloads": w,
                                                   "description": o["package"].get("description", "")}
            if len(objs) < 250:
                break
            time.sleep(1)
    return sorted(seen.values(), key=lambda c: c["name"])  # stable order before the seeded shuffle


def pypi_pool() -> list[dict]:
    rows = get("https://hugovk.github.io/top-pypi-packages/top-pypi-packages.min.json")["rows"]
    return [{"name": r["project"], "weekly_downloads": round(r["download_count"] * 7 / 30)}
            for r in rows if LOW <= r["download_count"] * 7 / 30 <= HIGH]


def cargo_pool(start: str, end: str) -> list[dict]:
    """Page through crates by recent downloads from HIGH down to LOW; created_at is in the listing."""
    pool, page = [], 1
    while True:
        crates = get(f"https://crates.io/api/v1/crates?sort=recent-downloads&per_page=100&page={page}")["crates"]
        if not crates:
            break
        for c in crates:
            w = round((c["recent_downloads"] or 0) * 7 / 90)
            if LOW <= w <= HIGH and start <= c["created_at"][:10] <= end:
                pool.append({"name": c["name"], "weekly_downloads": w, "first_released": c["created_at"][:10],
                             "description": (c.get("description") or "").strip()})
        if round((crates[-1]["recent_downloads"] or 0) * 7 / 90) < LOW:
            break
        # Skip ahead quickly through crates above HIGH.
        page += 10 if round((crates[-1]["recent_downloads"] or 0) * 7 / 90) > HIGH * 3 else 1
    return pool


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cutoff", required=True, help="probed model's training cutoff, YYYY-MM")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--per", type=int, default=15, help="candidates per ecosystem (default 15)")
    ap.add_argument("--out", default=str(PROBE / "niche_candidates.yaml"))
    a = ap.parse_args()
    y, m = map(int, a.cutoff.split("-"))
    end = (datetime.date(y + m // 12, m % 12 + 1, 1) - datetime.timedelta(days=1)).isoformat()  # last day of cutoff month
    start = datetime.date(y - 2, m, 1).isoformat()
    rng = random.Random(a.seed)
    out = {"cutoff": a.cutoff, "first_release_window": [start, end], "weekly_downloads": [LOW, HIGH],
           "seed": a.seed, "fetched": datetime.date.today().isoformat()}
    print("npm", file=sys.stderr)
    out["npm"] = take(npm_pool(), "npm", start, end, a.per, rng)
    print("pypi", file=sys.stderr)
    out["pypi"] = take(pypi_pool(), "pypi", start, end, a.per, rng)
    print("cargo", file=sys.stderr)
    out["cargo"] = take(cargo_pool(start, end), None, start, end, a.per, rng)
    pathlib.Path(a.out).write_text(yaml.safe_dump(out, sort_keys=False, allow_unicode=True), encoding="utf-8")


if __name__ == "__main__":
    main()

"""Registry metadata for the knowledge-gap probe's libraries.

Reads research/probe/libraries.yaml and writes research/probe/libmeta.yaml: per library,
the latest stable version, first and latest release dates, stable releases in the last
12 months, the first release of each major (of each minor below 1.0), and weekly downloads.

  python research/scripts/libmeta.py

Release dates come from deps.dev for every ecosystem. Weekly downloads come from
api.npmjs.org (last week), pypistats.org (last week) and crates.io (recent_downloads,
90 days, divided by 90/7). Stable means a version of digits and dots only, so
pre-releases, dev and post releases are left out of every count.
"""
import datetime, pathlib, re, sys, time, urllib.parse

import requests, yaml

PROBE = pathlib.Path(__file__).resolve().parents[1] / "probe"
UA = {"User-Agent": "agentbreadcrumbs knowledge-gap probe"}
STABLE = re.compile(r"\d+(\.\d+)*")
DEPS_SYSTEM = {"npm": "npm", "pypi": "pypi", "cargo": "cargo"}


def get(url: str):
    for attempt in range(3):
        r = requests.get(url, headers=UA, timeout=60)
        if r.status_code == 429:  # pypistats rate limit
            time.sleep(5 * (attempt + 1))
            continue
        r.raise_for_status()
        return r.json()
    r.raise_for_status()


def weekly_downloads(name: str, eco: str) -> int | None:
    try:
        if eco == "npm":
            return get(f"https://api.npmjs.org/downloads/point/last-week/{name}")["downloads"]
        if eco == "pypi":
            return get(f"https://pypistats.org/api/packages/{name.lower()}/recent")["data"]["last_week"]
        return round(get(f"https://crates.io/api/v1/crates/{name}")["crate"]["recent_downloads"] * 7 / 90)
    except requests.RequestException as e:
        print(f"  downloads failed for {name}: {e}", file=sys.stderr)
        return None


def series(version: str) -> str:
    """The release line a question would name: the major, or major.minor below 1.0."""
    parts = version.split(".")
    return parts[0] if parts[0] != "0" or len(parts) == 1 else ".".join(parts[:2])


def meta(name: str, eco: str, today: datetime.date) -> dict:
    pkg = urllib.parse.quote(name, safe="")
    versions = get(f"https://api.deps.dev/v3/systems/{DEPS_SYSTEM[eco]}/packages/{pkg}")["versions"]
    stable = sorted(((v["publishedAt"][:10], v["versionKey"]["version"]) for v in versions
                     if v.get("publishedAt") and STABLE.fullmatch(v["versionKey"]["version"])),
                    key=lambda dv: (dv[0], tuple(int(x) for x in dv[1].split("."))))
    if not stable:
        return {"error": "no stable versions with release dates"}
    year_ago = (today - datetime.timedelta(days=365)).isoformat()
    first_of = {}
    for date, v in stable:
        first_of.setdefault(series(v), {"version": v, "released": date})
    # Highest version number, not the latest upload: projects backport fixes to old lines.
    date, latest = max(stable, key=lambda dv: tuple(int(x) for x in dv[1].split(".")))
    return {"latest": latest, "latest_released": date, "first_released": stable[0][0],
            "stable_versions": len(stable), "releases_12mo": sum(d >= year_ago for d, _ in stable),
            "series": first_of, "weekly_downloads": weekly_downloads(name, eco)}


def main():
    groups = yaml.safe_load((PROBE / "libraries.yaml").read_text(encoding="utf-8"))
    today = datetime.date.today()
    out = {"fetched": today.isoformat(), "libraries": {}}
    for group, libs in groups.items():
        for lib in libs or []:
            print(f"{group:<16} {lib['name']}", file=sys.stderr)
            try:
                m = meta(lib["name"], lib["ecosystem"], today)
            except requests.RequestException as e:
                m = {"error": str(e)}
            out["libraries"][lib["name"]] = {"group": group, "ecosystem": lib["ecosystem"], **m}
    (PROBE / "libmeta.yaml").write_text(yaml.safe_dump(out, sort_keys=False, allow_unicode=True), encoding="utf-8")
    for name, m in out["libraries"].items():
        print(f"{name:<22} {m.get('latest', m.get('error', '')):<12} {m.get('latest_released', ''):<11}"
              f" 12mo {m.get('releases_12mo', ''):>4}  series {len(m.get('series', {})):>3}"
              f"  weekly {m.get('weekly_downloads') or '':>11}")


if __name__ == "__main__":
    main()

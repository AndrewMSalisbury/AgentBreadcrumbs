import sys, json, tiktoken
enc = tiktoken.get_encoding("o200k_base"); t = lambda s: len(enc.encode(s, disallowed_special=()))
raw = open(sys.argv[1], encoding="utf-8").read(); d = json.loads(raw)
c = d["crate"]; slim = {k: c.get(k) for k in ("name","description","max_stable_version","downloads","recent_downloads","repository","documentation","updated_at")}
print("full_api", t(raw), "slim_fields", t(json.dumps(slim)), "versions_listed", len(d.get("versions", [])))

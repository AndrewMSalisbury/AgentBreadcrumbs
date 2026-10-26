import sys, pathlib, tiktoken
enc = tiktoken.get_encoding("o200k_base")
for p in sys.argv[1:]:
    for f in sorted(pathlib.Path(p).glob("*.md")):
        print(f"{p.split('/')[-1]:10}{f.stem:14}{len(enc.encode(f.read_text(encoding='utf-8'), disallowed_special=())):>8,}")

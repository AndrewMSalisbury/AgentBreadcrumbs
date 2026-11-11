"""Launch the stock firecrawl-mcp server over stdio (run.py --backend firecrawl-mcp).

  python bc/firecrawl_mcp.py

The key comes from FIRECRAWL_API_KEY or the file BC_FIRECRAWL_KEY_FILE (default
~/.firecrawl_key), so a run's mcp.json names only this script, never the key.
"""
import os, pathlib, shutil, subprocess, sys

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
from bc.common import _firecrawl_key

VERSION = "3.39.0"  # pinned so runs on different days use the same tools

env = {**os.environ, "FIRECRAWL_API_KEY": _firecrawl_key()}
npx = shutil.which("npx") or "npx"
sys.exit(subprocess.run([npx, "-y", f"firecrawl-mcp@{VERSION}"], env=env).returncode)

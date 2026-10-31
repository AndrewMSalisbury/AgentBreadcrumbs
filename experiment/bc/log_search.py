"""PreToolUse hook for WebSearch under enforced-*: appends the search to the
run's call log (argv[1], same format as bc.common.log_call) so the registry can
count it. Never blocks the call; kept free of bc.common's heavy imports."""
import sys, json

try:
    query = json.load(sys.stdin).get("tool_input", {}).get("query", "")
except ValueError:
    query = ""
with open(sys.argv[1], "a", encoding="utf-8") as f:
    f.write(f"search\t{query}\n")

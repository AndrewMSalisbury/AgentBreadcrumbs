"""Stop hook for miss-0.3+: if the run was told a page card would be stored
(a "nudge" line in the call log, argv[1]) and nothing was stored since, block the
stop once and ask for the card. Kept free of bc.common's heavy imports."""
import sys, json

try:
    event = json.load(sys.stdin)
except ValueError:
    event = {}
path = sys.argv[1]
try:
    lines = open(path, encoding="utf-8").read().splitlines()
except FileNotFoundError:
    lines = []
kinds = [l.split("\t", 1)[0] for l in lines]
where = "the fetch result's note" if "note\tdefer" in lines else "the lookup note"  # miss-0.9
if event.get("stop_hook_active") or "nudge" not in kinds or "stored" in kinds or "stop" in kinds:
    sys.exit(0)
with open(path, "a", encoding="utf-8") as f:
    f.write("stop\tnudge\n")
fetches = sum(k in ("fetch", "render") for k in kinds)
print(json.dumps({"decision": "block", "reason": (
    f"[breadcrumbs: this run took {fetches} fetches and stored no breadcrumbs. Before finishing, call write "
    f"with a page card for the page that held the answer, as {where} describes, then repeat your "
    "final ANSWER line.]")}))

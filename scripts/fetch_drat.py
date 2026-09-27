"""Fetch pinned upstream proof-checker sources only; do not execute them."""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
destination = ROOT/"vendor/drat-trim"
destination.mkdir(parents=True, exist_ok=True)

def fetch(url):
    with urlopen(Request(url, headers={"User-Agent":"gf5-matroid-research"}), timeout=30) as response:
        return response.read()

commit = json.loads(fetch("https://api.github.com/repos/marijnheule/drat-trim/commits/master"))["sha"]
assert len(commit) == 40 and all(c in "0123456789abcdef" for c in commit)
files = {}
for name in ("drat-trim.c", "LICENSE", "README.md"):
    url = f"https://raw.githubusercontent.com/marijnheule/drat-trim/{commit}/{name}"
    data = fetch(url)
    path = destination/name
    with path.open("xb") as output:
        output.write(data)
    files[name] = {"url":url, "sha256":sha256(data).hexdigest(), "bytes":len(data)}
manifest = {"commit":commit,"downloaded_utc":datetime.now(timezone.utc).isoformat(),"files":files}
(destination/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
print(json.dumps(manifest,indent=2))

"""Cache a few author-provided reference files as INERT bytes with SHA-256.

No downloaded code or pickle is executed. Files are small and downloads serial.
"""
from datetime import datetime, timezone
from hashlib import sha256
from html.parser import HTMLParser
import json
from pathlib import Path
import urllib.parse
import urllib.request


ROOT = Path(__file__).resolve().parents[1]
PAGE = "https://homepages.ecs.vuw.ac.nz/~bretteni/code.html"
MAX_BYTES = 8 * 1024 * 1024


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            for key, value in attrs:
                if key == "href":
                    self.links.append(urllib.parse.urljoin(PAGE, value))


def fetch(url, target):
    if target.exists():
        return target.read_bytes(), "cached"
    request = urllib.request.Request(url, headers={"User-Agent": "gf5-minors-research/0.1"})
    with urllib.request.urlopen(request, timeout=25) as response:
        data = response.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("reference exceeds the 8 MiB download limit")
    target.write_bytes(data)
    return data, "downloaded"


def main():
    directory = ROOT / "data" / "raw" / "brettell"
    directory.mkdir(parents=True, exist_ok=True)
    page, state = fetch(PAGE, directory / "code.html")
    parser = Links()
    parser.feed(page.decode("utf-8"))
    chosen = [(PAGE, "code.html", page, state)]
    for suffix in ("matroid_utils.sage", "p_representable_matroids.sage", "gf5_excluded_minors10.sobj"):
        matches = [link for link in parser.links if urllib.parse.urlparse(link).path.endswith("/" + suffix)]
        if len(matches) != 1:
            raise ValueError(f"could not identify exactly one author link for {suffix}: {matches}")
        data, state = fetch(matches[0], directory / suffix)
        chosen.append((matches[0], suffix, data, state))
    manifest = {"retrieved_utc": datetime.now(timezone.utc).isoformat(),
                "landing_page": PAGE, "executed_downloaded_content": False,
                "files": [{"url": url, "path": str((directory / name).relative_to(ROOT)),
                           "bytes": len(data), "sha256": sha256(data).hexdigest(), "state": state}
                          for url, name, data, state in chosen]}
    path = ROOT / "data" / "reference_manifest.json"
    path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()

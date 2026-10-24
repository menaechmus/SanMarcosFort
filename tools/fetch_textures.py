"""Download the game's CC0 texture sets from Poly Haven (https://polyhaven.com, license CC0).

Each set goes into assets/textures/<slug>/ as <slug>_<map>_<res>.jpg. Already-downloaded
files are skipped. Standard library only:
    python -I tools/fetch_textures.py
"""

import json
import time
import urllib.request
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
OUT = PROJECT / "assets" / "textures"
USER_AGENT = "SanMarcosFort-texture-fetch/1.0 (personal game project)"

# slug -> (use, resolution). Maps fetched for every set: colour, OpenGL normal, roughness.
TEXTURES = {
    "large_sandstone_blocks_01": ("fort walls: coquina blocks (today's look)", "1k"),
    "painted_plaster_wall": ("fort walls: lime plaster (colonial look), tinted red for garitas", "1k"),
    "brown_planks_03": ("ship hulls, decks, gun carriages, bridges", "1k"),
    "cotton_jersey": ("sailcloth", "1k"),
    "grass_ground": ("ground around the fort", "1k"),
    "coast_sand_01": ("beaches and the island", "1k"),
}
MAPS = {"Diffuse": "albedo", "nor_gl": "normal", "Rough": "rough"}


def get(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def main() -> int:
    for slug, (use, res) in TEXTURES.items():
        files = json.loads(get(f"https://api.polyhaven.com/files/{slug}"))
        folder = OUT / slug
        folder.mkdir(parents=True, exist_ok=True)
        for api_name, short in MAPS.items():
            target = folder / f"{slug}_{short}_{res}.jpg"
            if target.exists():
                continue
            entry = files.get(api_name, {}).get(res, {})
            url = (entry.get("jpg") or entry.get("png") or {}).get("url")
            if not url:
                print(f"missing {slug} {api_name} {res}")
                continue
            data = get(url)
            if url.endswith(".png"):
                target = target.with_suffix(".png")
            target.write_bytes(data)
            print(f"saved {target.relative_to(PROJECT)} ({len(data) // 1024} KB) - {use}")
            time.sleep(0.2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

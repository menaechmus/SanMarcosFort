"""Download the HABS FL-17 measured drawings of the Castillo de San Marcos.

The Historic American Buildings Survey drawings are U.S. Government works held by the Library
of Congress (https://www.loc.gov/item/fl0095/), with no known restrictions. They are the
reference for the fort model; tools/blender/fort_dims.py records what was measured from them.

Usage (standard library only):
    python -I tools/fetch_habs.py                   # all 21 sheets as 1024 px previews
    python -I tools/fetch_habs.py --width 4000 3 5  # sheets 3 and 5 at 4000 px wide
    python -I tools/fetch_habs.py --width 1600 --region 30,25,30,40 12
                                                    # a crop (x, y, w, h in % of the sheet)
"""

import argparse
import time
import urllib.request
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
OUT_DIR = PROJECT / "reference" / "habs"
SHEET_COUNT = 21
PREVIEW_URL = "https://tile.loc.gov/storage-services/service/pnp/habshaer/fl/fl0000/fl0095/sheet/{id}v.jpg"
IIIF_URL = ("https://tile.loc.gov/image-services/iiif/"
            "service:pnp:habshaer:fl:fl0000:fl0095:sheet:{id}a/{region}/{width},/0/default.jpg")
# Full-resolution 1-bit scans (about 1 MB each); crop them with tools/crop_image.ps1.
MASTER_URL = "https://tile.loc.gov/storage-services/master/pnp/habshaer/fl/fl0000/fl0095/sheet/{id}a.tif"
USER_AGENT = "SanMarcosFort-reference-fetch/1.0 (personal game project)"


def fetch(url: str, target: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response:
        data = response.read()
    if not (data.startswith(b"\xff\xd8") or data[:4] in (b"II*\x00", b"MM\x00*")):
        raise RuntimeError(f"not a JPEG or TIFF: {url}")
    target.write_bytes(data)


def main() -> int:
    parser = argparse.ArgumentParser(description="Download HABS FL-17 drawing sheets")
    parser.add_argument("sheets", nargs="*", type=int, help="sheet numbers 1-21 (default: all)")
    parser.add_argument("--width", type=int, default=1024, help="1024 = preview JPEGs, otherwise IIIF width")
    parser.add_argument("--region", default="", help="crop as x,y,w,h percentages of the sheet")
    parser.add_argument("--master", action="store_true", help="download the full-resolution TIFF scans")
    options = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    sheets = options.sheets or list(range(1, SHEET_COUNT + 1))
    for sheet in sheets:
        sheet_id = f"{sheet - 1:05d}"
        if options.master:
            url = MASTER_URL.format(id=sheet_id)
            target = OUT_DIR / f"sheet_{sheet:02d}_master.tif"
        elif options.region:
            url = IIIF_URL.format(id=sheet_id, region="pct:" + options.region, width=options.width)
            tag = options.region.replace(",", "_")
            target = OUT_DIR / f"sheet_{sheet:02d}_crop_{tag}.jpg"
        elif options.width <= 1024:
            url = PREVIEW_URL.format(id=sheet_id)
            target = OUT_DIR / f"sheet_{sheet:02d}_preview.jpg"
        else:
            url = IIIF_URL.format(id=sheet_id, region="full", width=options.width)
            target = OUT_DIR / f"sheet_{sheet:02d}_{options.width}.jpg"
        if target.exists():
            print(f"have  {target.name}")
            continue
        fetch(url, target)
        print(f"saved {target.name} ({target.stat().st_size // 1024} KB)")
        time.sleep(0.5)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

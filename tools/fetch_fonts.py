"""Download the game's title font from the Google Fonts repository (SIL Open Font License).

IM Fell English roman (IMFeENrm28P): Igino Marini's digitization of the Fell types, cut in the
late 1600s. It goes into assets/fonts/im_fell_english/ with its license. Downloads and files
already there are checked against the SHA-256 recorded below. Standard library only:
    python -I tools/fetch_fonts.py
"""

import hashlib
import urllib.request
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
OUT = PROJECT / "assets" / "fonts" / "im_fell_english"
USER_AGENT = "SanMarcosFort-font-fetch/1.0 (personal game project)"
BASE = "https://raw.githubusercontent.com/google/fonts/main/ofl/imfellenglish/"

# file name -> SHA-256 of the copy the game was made with ("" = not recorded yet).
FILES = {
    "IMFeENrm28P.ttf": "fe9705bbde51af802719246d4608d08d37bde956ab99d9a590da996a5221a24c",
    "OFL.txt": "2a3ca501fc4d5efcad9798531e3e06962b1e20c60e464f6cbd6c17630112c773",
}


def get(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    failed = False
    for name, expected in FILES.items():
        target = OUT / name
        data = target.read_bytes() if target.exists() else get(BASE + name)
        digest = hashlib.sha256(data).hexdigest()
        if expected and digest != expected:
            print(f"{name}: SHA-256 {digest} does not match the recorded {expected}; not saved")
            failed = True
            continue
        if not target.exists():
            target.write_bytes(data)
            print(f"saved {target.relative_to(PROJECT)} ({len(data) // 1024} KB) sha256={digest}")
        else:
            print(f"ok {target.relative_to(PROJECT)} sha256={digest}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

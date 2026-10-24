"""Write Godot import settings (.import files) for the downloaded textures and the
synthesized sounds.

Textures: VRAM-compressed with mipmaps (S3TC/BPTC on desktop, ETC2/ASTC on mobile and web);
normal maps flagged so Godot uses a two-channel normal-map compression.
Sounds: QOA-compressed WAV; *_loop.wav files loop. Existing settings are replaced; Godot
re-imports on the next editor start or `--import`. Standard library only:
    python -I tools/import_settings.py
"""

from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
TEXTURE = """[remap]

importer="texture"
type="CompressedTexture2D"

[params]

compress/mode=2
compress/high_quality=false
compress/lossy_quality=0.7
compress/hdr_compression=1
compress/normal_map={normal}
compress/channel_pack=0
mipmaps/generate=true
mipmaps/limit=-1
roughness/mode=0
roughness/src_normal=""
process/fix_alpha_border=true
process/premult_alpha=false
process/normal_map_invert_y=false
process/hdr_as_srgb=false
process/hdr_clamp_exposure=false
process/size_limit=0
detect_3d/compress_to=0
"""
SOUND = """[remap]

importer="wav"
type="AudioStreamWAV"

[params]

force/8_bit=false
force/mono=false
force/max_rate=false
force/max_rate_hz=44100
edit/trim=false
edit/normalize=false
edit/loop_mode={loop}
edit/loop_begin=0
edit/loop_end=-1
compress/mode=2
"""


def main() -> int:
    textures = sounds = 0
    for image in sorted((PROJECT / "assets" / "textures").rglob("*")):
        if image.suffix.lower() in (".jpg", ".jpeg", ".png"):
            normal = 1 if "_normal" in image.stem else 2
            image.with_name(image.name + ".import").write_text(TEXTURE.format(normal=normal), encoding="utf-8")
            textures += 1
    for sound in sorted((PROJECT / "assets" / "audio").glob("*.wav")):
        loop = 2 if sound.stem.endswith("_loop") else 1
        sound.with_name(sound.name + ".import").write_text(SOUND.format(loop=loop), encoding="utf-8")
        sounds += 1
    print(f"wrote import settings for {textures} textures and {sounds} sounds")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

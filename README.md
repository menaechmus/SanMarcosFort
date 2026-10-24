# San Marcos Fort

A 3D cannon-defense game built with Godot 4.7. You command the guns of the Castillo de San Marcos
in St. Augustine, Florida, and sink the late-1500s and 1600s ships sailing past on Matanzas Bay.
It targets desktop, the browser and phones from one project.

## Requirements

- Godot 4.7.2 (standard build, not .NET), installed at `%USERPROFILE%\Tools\Godot\` (the scripts in `tools/` look there; set `$env:GODOT` to use another binary),
  with the 4.7.2 export templates installed.
- Blender 5.2: only needed to rebuild the 3D models (`tools/blender/`).
- Python 3.12 (standard library only): only needed for the download, sound and test tools in `tools/`.
- For Android builds: the Android SDK (build-tools and platform-tools) and JDK 21. Android Studio
  installs both.

## Running

Open `project.godot` in the Godot editor and press F5, or from a terminal:

```powershell
& "$env:USERPROFILE\Tools\Godot\Godot_v4.7.2-stable_win64.exe" --path .
```

## How to play

Ships sail in from the inlet to the north and past the fort toward the town. Sink them before they
get through. Each wave ends at the shop, where gold buys faster reloads, longer range, tighter
groups, chain shot (wrecks masts and sails, slowing ships), heated shot (sets ships on fire), an
extra gun, and repairs. From wave 4, armed ships fire broadsides at the fort. A hit near a gun
sends its crew to cover for a few seconds. The run ends when the town has taken too much damage or
the Castillo's walls fall. After wave 8 the last waves repeat with more and faster ships.

Settings has graphics quality, aim assist (a marker showing where a ship will be when your shot
arrives), volume, and the fort's look: today's bare coquina, or the Spanish colonial white plaster
with red sentry boxes.

### Controls

| Action | Desktop | Touch |
| --- | --- | --- |
| Aim | Move the mouse over the water | Drag one finger (the marker sits above it) |
| Fire | Left click, F or Enter | FIRE button |
| Switch gun | Tab / Q / E, or 1–6 | ◀ Gun / Gun ▶ |
| Switch ammunition | R | Ammo button |
| Look around | Right- or middle-drag, WASD or arrow keys | Two-finger drag |
| Zoom | Mouse wheel, + / − | Pinch |
| Spyglass | Space | Spyglass button |
| Pause | Esc or P | II button |

The ring on the water is where the shot will land. Gold means the gun can reach that point. Red means
out of range, orange means too close for the gun to depress, and grey means outside this gun's field of fire.
Balls take a few seconds to arrive, so aim ahead of moving ships.

## Building

```powershell
powershell -File tools/export_all.ps1             # all three
powershell -File tools/export_all.ps1 Web         # or one: Web, Windows, Android
```

| Platform | Output | Notes |
| --- | --- | --- |
| Web | `build/web/` (index.html + .wasm + .pck, about 73 MB) | Threads are off, so any static host works (itch.io, GitHub Pages, `python -m http.server -d build/web`) without special headers. Serve it compressed: the .wasm shrinks to about a quarter. |
| Windows | `build/windows/SanMarcosFort.exe` (about 123 MB) | One file; the game data is embedded. |
| Android | `build/android/SanMarcosFort.apk` (about 46 MB) | 64-bit ARM. A debug build unless a release keystore is set up (below). |

Quality defaults to High on desktop, Medium in desktop browsers, and Low on phones (app or browser).

### Android

One-time setup (already done on this PC): in the Godot editor, Editor Settings > Export > Android,
set the Java SDK path (`C:\Program Files\Android\openjdk\jdk-21.0.8`) and the Android SDK path
(`%LOCALAPPDATA%\Android\Sdk`). The debug keystore is `%APPDATA%\Godot\keystores\debug.keystore`.

To install on a phone, turn on USB debugging (Settings > Developer options), plug it in, and run:

```powershell
& "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe" install -r build\android\SanMarcosFort.apk
```

Before publishing:
- Change the package name in the Android preset (`package/unique_name`, now the placeholder
  `com.sanmarcosfort.game`). It can't change after the first release.
- Make a release keystore with `keytool -genkeypair` and keep it safe. Set
  `GODOT_ANDROID_KEYSTORE_RELEASE_PATH`, `GODOT_ANDROID_KEYSTORE_RELEASE_USER` and
  `GODOT_ANDROID_KEYSTORE_RELEASE_PASSWORD`; `export_all.ps1` then makes a signed release build.
- Google Play wants an AAB rather than an APK. That needs a Gradle build: Project > Install Android
  Build Template, then in the Android preset turn on `gradle_build/use_gradle_build` and set the
  export format to AAB.

### iOS

iOS exports need a Mac with Xcode and an Apple Developer account. On the Mac, add an iOS preset in
Project > Export and export an Xcode project. Until then, iPhones can play the web build in Safari.

## Rebuilding assets

Everything under `assets/` can be regenerated:

```powershell
powershell -File tools/build_assets.ps1           # 3D models with Blender: fort terrain cannon ships props
python -I tools/fetch_textures.py                 # CC0 textures from Poly Haven
python -I tools/fetch_fonts.py                    # the title font (checked against recorded hashes)
python -I tools/synth_audio.py                    # the sound effects, synthesized from scratch
python -I tools/import_settings.py                # Godot import settings for textures and sounds
python -I tools/fetch_habs.py                     # the HABS drawings the fort is measured from
```

The models come from Python scripts in `tools/blender/`. `fort_dims.py` records each fort
measurement and the HABS sheet it came from. Each script also saves a `.blend` file and preview
renders under `build/`. The `.glb` files carry named material slots, and Godot swaps in the real
materials (`MaterialMapper`), so textures can be tuned without rebuilding models.

## Tests and checks

```powershell
powershell -File tools/run_tests.ps1              # GUT unit tests, headless
python -I tools/web_smoke_test.py                 # runs the web build in headless Chrome
```

Debug options go after `--` on the Godot command line (all listed in `game/common/debug_cli.gd`):

```powershell
$godot = "$env:USERPROFILE\Tools\Godot\Godot_v4.7.2-stable_win64_console.exe"
# 4 simulated minutes with the autoplay bot, headless, then print a report
& $godot --headless --fixed-fps 60 --path . -- --autoplay --quit-after-sec=240
# start at wave 7
& $godot --headless --fixed-fps 60 --path . -- --autoplay --wave=7 --quit-after-sec=200
# screenshot from a camera bookmark (overview, fort, fort_close, town, lanes, ship, ship:galleon, gun:<n>)
& $godot --path . -- --start --frames=300 --capture=build/shots/overview.png --cam=overview
# frame rate and draw calls for a quality preset (printed as [stats] with the screenshot)
& $godot --disable-vsync --fixed-fps 60 --path . -- --autoplay --wave=8 --frames=3000 --cam=gun:1 --quality=low --capture=build/shots/perf.png
```

`--shop` opens the shop with some gold, and `--timescale=<x>` speeds the game up.

## Performance

Measured on this PC's Intel integrated graphics at 1280×720, from a gun position. Draw calls include
shadow passes.

| Preset | Quiet bay | Wave 8 (nine ships in view) |
| --- | --- | --- |
| Low | 202 fps, 140 draw calls, 145k triangles | 140–190 fps, 250–315 draw calls, 155k triangles |
| Medium | 142 fps, 142 draw calls, 211k triangles | (not measured) |
| High | 96 fps, 142 draw calls, 306k triangles | about 82 fps, 300–330 draw calls, 322k triangles |

The presets change render scale, MSAA, the water mesh density, vegetation density, the sun's
shadow-map size, and whether ships cast shadows. The biggest waves go a little over the 300 draw
call budget because each ship has 17 to 23 material surfaces. Merging the ship materials into one
atlas texture is the next step if phones struggle.

## Project layout

| Folder | Contents |
| --- | --- |
| `game/autoload/` | Global services: game clock, settings and input map, run state, audio |
| `game/common/` | Debug command line, material mapping for imported models |
| `game/water/` | Gerstner wave shader, its CPU mirror (`WaveMath`), and the graded water mesh |
| `game/weapons/` | Ballistics, cannons, pooled cannonballs, ammo types, shop upgrades |
| `game/ships/` | Ship behaviour (lanes, riding the waves, damage, return fire, sinking) and ship types |
| `game/fort/` | Fort scene, its stone/plaster shader, and gun emplacements |
| `game/level/` | Main level, sky, terrain, vegetation, ship lanes, waves and the wave director |
| `game/player/` | Input, camera rig, aim marker, player controller |
| `game/fx/`, `game/ui/` | Effects; HUD, menus, shop and theme |
| `assets/` | Generated models, downloaded textures and font, synthesized sounds |
| `tests/` | GUT unit tests |
| `tools/` | Asset build scripts (Blender), download, sound, export and test tools |

`reference/` (the HABS downloads) and `build/` (exports, screenshots, previews) are not tracked by git.

Conventions: 1 unit = 1 metre. +X is east (the bay), −Z is north (the inlet), and sea level is y = 0.
The fort stands at the origin.

## Credits

See [CREDITS.md](CREDITS.md).

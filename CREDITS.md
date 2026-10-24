# Credits and licenses

## Engine and tools

- **Godot Engine**: MIT license. Copyright (c) 2014-present Godot Engine contributors;
  (c) 2007-2014 Juan Linietsky, Ariel Manzur. Released builds must include this notice; the in-game
  credits screen shows `Engine.get_license_text()`.
- **GUT (Godot Unit Test)** 9.7.1 by Butch Wesley: MIT license. Used for development only, and
  excluded from exported builds.
- **Blender** 5.2 generated the 3D models (`tools/blender/`). Blender's GPL license doesn't extend to
  the models it produces.

## Historical reference

- **Castillo de San Marcos**: Historic American Buildings Survey, HABS FL-17 (Library of Congress,
  Prints & Photographs Division, https://www.loc.gov/item/fl0095/). U.S. Government work, no known
  restrictions. The fort model is built from these measured drawings, plus facts published by the
  National Park Service.

## Art and audio

- **3D models**: made for this game by the scripts in `tools/blender/`.
- **Textures**: Poly Haven (https://polyhaven.com), CC0 1.0 (public domain). Downloaded by
  `tools/fetch_textures.py`:

  | Set | Used for |
  | --- | --- |
  | large_sandstone_blocks_01 | Fort walls, today's bare coquina |
  | painted_plaster_wall | Fort walls in the Spanish colonial look; red sentry boxes |
  | brown_planks_03 | Ship hulls and decks, gun carriages, bridges |
  | cotton_jersey | Sailcloth |
  | grass_ground | Ground around the fort |
  | coast_sand_01 | Beaches and Anastasia Island |

  Water ripples, clouds and flags are generated in shaders and noise textures.
- **Font**: IM Fell English (roman) by Igino Marini, from the Google Fonts repository. SIL Open Font
  License 1.1; the license is in `assets/fonts/im_fell_english/OFL.txt`. Used for titles and wave
  banners.
- **Sound effects**: synthesized for this game by `tools/synth_audio.py` (noise, filters and
  oscillators; no recorded samples).

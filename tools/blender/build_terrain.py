"""Builds the land around Matanzas Bay (terrain.glb).

The mainland with the town's shore runs along the west of the bay; Anastasia Island lies
about a kilometre east, its dunes ending in a hooked point at the inlet to the north-east;
the bay floor deepens toward the channel. World coordinates: the fort's court centre at
x = z = 0, sea level at y = 0. The fort's grounds rectangle is left open (build_fort.py
fills it). The land is split into tiles so Godot can level-of-detail them separately.

Headless:
    blender -b --factory-startup -P tools/blender/build_terrain.py -- --out assets/models/terrain/terrain.glb
            [--preview build/previews/terrain]
"""

import argparse
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402
import build_fort as F  # noqa: E402
import fort_dims as D  # noqa: E402
import meshkit as mk  # noqa: E402

GRADE = F.WORLD_Y + D.GRADE
X_RANGE = (-1600.0, 3200.0)
Z_RANGE = (-3400.0, 3200.0)
DENSE_X = (-160.0, 130.0)
DENSE_Z = (-200.0, 220.0)
DENSE_STEP = 5.0
TILE_CELLS = 40
UV_TILE = 6.0


def lerp(a, b, t):
    return a + (b - a) * t


def shore_x(z: float) -> float:
    """Mainland shoreline. Straight along the fort's seawall, then wandering; north of the
    fort the coast swings east to form the north side of the inlet."""
    x = 75.0
    if z < -185.0:
        t = mk.smoothstep(-185.0, -420.0, z)
        x += t * (16.0 * math.sin((z + 185.0) / 210.0) + 10.0)
        x += 420.0 * mk.smoothstep(-1300.0, -2800.0, z)
    elif z > 200.0:
        t = mk.smoothstep(200.0, 420.0, z)
        x += t * (12.0 * math.sin((z - 200.0) / 170.0) - 5.0) - 0.035 * max(z - 700.0, 0.0)
    return x


def island_x(z: float) -> float:
    """West shore of Anastasia Island; its north tip curves away east at the inlet."""
    x = 1060.0 + 70.0 * math.sin(z / 620.0 + 0.4) + 22.0 * math.sin(z / 170.0)
    if z < -1650.0:
        x += ((-1650.0 - z) ** 1.35) * 0.9
    return x


def grounds_distance(x: float, z: float) -> float:
    x0, x1, z0, z1 = F.GROUNDS
    dx = max(x0 - x, 0.0, x - x1)
    dz = max(z0 - z, 0.0, z - z1)
    return math.hypot(dx, dz)


def in_grounds(x: float, z: float) -> bool:
    x0, x1, z0, z1 = F.GROUNDS
    return x0 <= x <= x1 and z0 <= z <= z1


def height(x: float, z: float) -> float:
    sx, ix = shore_x(z), island_x(z)
    broad = mk.fbm(x * 0.005, 0.3, z * 0.005, 3)
    local = mk.fbm(x * 0.03 + 5.0, 1.7, z * 0.03, 2)
    if x <= sx:
        inland = sx - x
        land = GRADE + min(inland, 700.0) * 0.003
        land += (broad - 0.5) * 2.4 * mk.smoothstep(60.0, 260.0, inland)
        land += (local - 0.5) * 0.7 * mk.smoothstep(15.0, 60.0, inland)
        # Near the fort the ground settles to the grounds' level.
        land = lerp(GRADE, land, mk.smoothstep(0.0, 40.0, grounds_distance(x, z)))
        # A steep bank at the shore (beside the seawall), gentler beaches farther away.
        bank = 3.0 if abs(z) < 420.0 else 22.0
        return lerp(0.3, land, mk.smoothstep(0.0, bank, inland))
    if x >= ix:
        inland = x - ix
        dunes = 1.6 + 4.8 * mk.smoothstep(40.0, 240.0, inland) * (0.55 + 0.9 * broad)
        dunes += (local - 0.5) * 1.4 * mk.smoothstep(30.0, 120.0, inland)
        return lerp(0.25, dunes, mk.smoothstep(0.0, 45.0, inland))
    d = min(x - sx, ix - x)
    return 0.3 - 1.5 * mk.smoothstep(0.0, 25.0, d) - 5.2 * mk.smoothstep(20.0, 330.0, d) - (local - 0.5) * 0.6


def ground_color(x: float, y: float, z: float):
    """R sand, G grass, B wet (vertex colour for game/level/terrain.gdshader)."""
    patch = mk.fbm(x * 0.02 + 11.0, 0.5, z * 0.02 - 4.0, 3)
    on_island = x > island_x(z) - 5.0
    if y < 1.0:
        grass = 0.0
    elif on_island:
        grass = mk.smoothstep(0.52, 0.72, patch) * mk.smoothstep(2.2, 3.8, y)
    else:
        grass = mk.smoothstep(1.0, 2.0, y) * (1.0 - 0.6 * mk.smoothstep(0.62, 0.8, patch))
    wet = 1.0 - mk.smoothstep(-0.2, 0.9, y)
    return (1.0 - grass, grass, wet, 1.0)


def axis(lo: float, hi: float, dense_lo: float, dense_hi: float, step: float, growth: float, max_step: float):
    pts = []
    v = dense_lo
    while v < dense_hi - 1e-6:
        pts.append(v)
        v += step
    pts.append(dense_hi)
    s, v = step, dense_hi
    while v < hi:
        s = min(s * growth, max_step)
        v = min(v + s, hi)
        pts.append(v)
    s, v = step, dense_lo
    while v > lo:
        s = min(s * growth, max_step)
        v = max(v - s, lo)
        pts.insert(0, v)
    return pts


def build_tiles(xs, zs, heights):
    nx, nz = len(xs), len(zs)
    tiles = 0
    for ti in range(0, nx - 1, TILE_CELLS):
        for tj in range(0, nz - 1, TILE_CELLS):
            mb = mk.MeshBuilder(f"Terrain_{ti // TILE_CELLS}_{tj // TILE_CELLS}", UV_TILE)
            for i in range(ti, min(ti + TILE_CELLS, nx - 1)):
                for j in range(tj, min(tj + TILE_CELLS, nz - 1)):
                    cx, cz = (xs[i] + xs[i + 1]) / 2, (zs[j] + zs[j + 1]) / 2
                    if in_grounds(cx, cz):
                        continue
                    corners = [(i, j), (i, j + 1), (i + 1, j + 1), (i + 1, j)]
                    pts = [(xs[a], heights[a][b], zs[b]) for a, b in corners]
                    uvs = [(p[0] / UV_TILE, -p[2] / UV_TILE) for p in pts]
                    cols = [ground_color(*p) for p in pts]
                    if mk.face_normal(pts).y < 0:
                        pts.reverse()
                        uvs.reverse()
                        cols.reverse()
                    mb.face(pts, "terrain", uvs, smooth=True, cols=cols)
            if mb.faces:
                mb.build()
                tiles += 1
    return tiles


def build_collision(xs, zs, heights, stride: int = 3):
    """Coarse collision for land above the water (shots that land ashore raise dust)."""
    mb = mk.MeshBuilder("TerrainCollision-colonly")
    ii = list(range(0, len(xs) - 1, stride)) + [len(xs) - 1]
    jj = list(range(0, len(zs) - 1, stride)) + [len(zs) - 1]
    for a in range(len(ii) - 1):
        for b in range(len(jj) - 1):
            i0, i1, j0, j1 = ii[a], ii[a + 1], jj[b], jj[b + 1]
            pts = [(xs[i0], heights[i0][j0], zs[j0]), (xs[i0], heights[i0][j1], zs[j1]),
                   (xs[i1], heights[i1][j1], zs[j1]), (xs[i1], heights[i1][j0], zs[j0])]
            if max(p[1] for p in pts) < -0.5 or in_grounds((xs[i0] + xs[i1]) / 2, (zs[j0] + zs[j1]) / 2):
                continue
            if mk.face_normal(pts).y < 0:
                pts.reverse()
            mb.face(pts, "terrain")
    mb.build()


def build() -> None:
    mk.material("terrain", (0.55, 0.52, 0.38))
    xs = axis(*X_RANGE, *DENSE_X, DENSE_STEP, 1.16, 70.0)
    zs = axis(*Z_RANGE, *DENSE_Z, DENSE_STEP, 1.14, 60.0)
    heights = []
    for x in xs:
        column = []
        for z in zs:
            h = GRADE if in_grounds(x, z) and x < F.GROUNDS[1] else height(x, z)
            if abs(x - F.GROUNDS[1]) < 1e-6 and F.GROUNDS[2] <= z <= F.GROUNDS[3]:
                h = -1.5  # under the seawall
            column.append(h)
        heights.append(column)
    tiles = build_tiles(xs, zs, heights)
    build_collision(xs, zs, heights)
    print(f"[terrain] grid {len(xs)} x {len(zs)}, {tiles} tiles")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--blend", default="")
    parser.add_argument("--preview", default="")
    args = parser.parse_args(mk.script_args())
    mk.reset_scene()
    build()
    mk.export_glb(os.path.abspath(args.out))
    if args.blend:
        mk.save_blend(os.path.abspath(args.blend))
    if args.preview:
        for obj in bpy.data.objects:
            if obj.name.endswith("-colonly"):
                obj.hide_render = True
        # Preview-only sea (the game's water is a shader); exported already, so not in the .glb.
        sea = mk.MeshBuilder("PreviewSea")
        sea.color_fn = lambda p, n: (0.15, 0.35, 0.5, 1.0)
        sea.face([(-1600.0, 0.0, -3400.0), (-1600.0, 0.0, 3200.0), (3200.0, 0.0, 3200.0), (3200.0, 0.0, -3400.0)], "terrain")
        sea.build()
        mk.render_views(os.path.abspath(args.preview), [
            ("top", (800.0, 8000.0, -100.0), (800.0, 0.0, -100.0), 6800.0),
            ("from_fort", (40.0, 14.0, 0.0), (900.0, 0.0, -300.0), None),
            ("inlet", (300.0, 60.0, -400.0), (1200.0, 0.0, -2200.0), None),
        ], color_type="VERTEX")
    return 0


if __name__ == "__main__":
    main()

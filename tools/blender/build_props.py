"""Builds the scenery props (props.glb) and their placements (props_scatter.tres).

Props, each with its origin at its base: Palm (cabbage palm), Oak (live oak), Palmetto (saw
palmetto clump), HouseA (one-storey coquina house), HouseB (two storeys with a street
balcony), HouseC (thatched hut), Church (with a bell gable). Placements are computed on the
terrain (build_terrain.height): trees on the mainland and Anastasia Island's dunes, the fort's
field of fire kept clear as it was, and the colonial town on a street grid south of the fort.
game/level/scatter.gd turns the placements into MultiMeshes.

Headless:
    blender -b --factory-startup -P tools/blender/build_props.py -- --out assets/models/props/props.glb
            --scatter assets/models/props/props_scatter.tres [--preview build/previews/props]
"""

import argparse
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402
import build_fort as F  # noqa: E402
import build_terrain as T  # noqa: E402
import meshkit as mk  # noqa: E402

VEGETATION = ("Palm", "Oak", "Palmetto")
# Keep the ground around the fort open (the Spanish kept a clear field of fire).
CLEAR_RADIUS = 230.0
TOWN = (-480.0, 40.0, 260.0, 1100.0)  # x_min, x_max, z_min, z_max


def ao_color(base_y: float, top_y: float):
    """Grey vertex colour, darker toward the base (props materials multiply by it)."""
    def fn(p, n):
        v = 0.62 + 0.38 * mk.smoothstep(base_y, top_y, p[1])
        return (v, v, v, 1.0)
    return fn


# --- Props --------------------------------------------------------------------------------

def frond(mb, top, azimuth, length, droop, width=1.1):
    dx, dz = math.cos(azimuth), math.sin(azimuth)
    sx, sz = -dz, dx
    rows = []
    for t in (0.0, 0.25, 0.5, 0.75, 1.0):
        cx = top[0] + dx * length * t
        cz = top[2] + dz * length * t
        cy = top[1] + 1.3 * math.sin(math.pi * t * 0.75) - droop * 1.6 * t * t
        w = width * math.sin(math.pi * min(t * 1.15, 1.0)) * 0.5
        rows.append(((cx + sx * w, cy + w * 0.25, cz + sz * w), (cx - sx * w, cy + w * 0.25, cz - sz * w)))
    for (l0, r0), (l1, r1) in zip(rows, rows[1:]):
        mb.quad_facing(l0, r0, r1, l1, (0.0, 1.0, 0.0), "leaf", [(0, 0), (1, 0), (1, 1), (0, 1)], smooth=True)


def build_palm():
    mb = mk.MeshBuilder("Palm", 1.0)
    mb.color_fn = ao_color(0.0, 9.0)
    pts = [(0.0, -0.3, 0.0), (0.12, 3.4, 0.04), (0.32, 6.8, 0.08), (0.42, 9.4, 0.1)]
    radii = [0.27, 0.23, 0.21, 0.2]
    for a, b, r0, r1 in zip(pts, pts[1:], radii, radii[1:]):
        mk.tube(mb, a, b, r0, r1, "bark", 7, caps=False)
    top = (pts[-1][0], pts[-1][1] + 0.1, pts[-1][2])
    mk.dome(mb, (top[0], top[2]), 0.32, top[1] - 0.25, "bark", segments=7, rings=2)
    for i in range(12):
        az = 2 * math.pi * i / 12 + 0.25 * ((i * 37) % 7) / 7
        droop = 0.55 + 0.6 * ((i * 7) % 5) / 4
        length = 3.0 + 0.6 * ((i * 3) % 4) / 3
        frond(mb, top, az, length, droop)
    return mb.build()


def lumpy_sphere(mb, center, radius, mat, seed, segments=7, rings=5):
    cx, cy, cz = center
    pts = []
    for r in range(rings + 1):
        lat = -math.pi / 2 * 0.7 + (math.pi * 0.85) * r / rings
        row = []
        for s in range(segments):
            lon = 2 * math.pi * s / segments
            bump = 0.82 + 0.36 * mk.value_noise(math.cos(lon) * 1.7 + seed, math.sin(lat) * 1.7, math.sin(lon) * 1.7)
            rr = radius * bump
            row.append((cx + rr * math.cos(lat) * math.cos(lon), cy + rr * math.sin(lat) * 0.78, cz + rr * math.cos(lat) * math.sin(lon)))
        pts.append(row)
    for r in range(rings):
        for s in range(segments):
            s2 = (s + 1) % segments
            q = [pts[r][s], pts[r][s2], pts[r + 1][s2], pts[r + 1][s]]
            mid = [sum(p[i] for p in q) / 4 for i in range(3)]
            mb.quad_facing(*q, (mid[0] - cx, mid[1] - cy, mid[2] - cz), mat, smooth=True)
    for ring, up in ((pts[0], -1.0), (pts[-1], 1.0)):
        if mk.face_normal(ring).y * up < 0:
            ring = list(reversed(ring))
        mb.face(ring, mat, smooth=True)


def build_oak():
    mb = mk.MeshBuilder("Oak", 1.5)
    mb.color_fn = ao_color(0.0, 8.5)
    mk.tube(mb, (0.0, -0.3, 0.0), (0.3, 2.8, 0.0), 0.55, 0.42, "bark", 7, caps=False)
    blobs = [((0.0, 6.2, 0.0), 3.4), ((2.9, 5.2, 1.2), 2.7), ((-2.7, 5.4, -0.9), 2.8),
             ((0.9, 5.0, -2.7), 2.5), ((-1.1, 7.4, 1.5), 2.3)]
    for (c, r) in blobs[1:4]:
        mk.tube(mb, (0.3, 2.6, 0.0), (c[0] * 0.75, c[1] - 0.8, c[2] * 0.75), 0.32, 0.16, "bark", 5, caps=False)
    for i, (c, r) in enumerate(blobs):
        lumpy_sphere(mb, c, r, "foliage", seed=i * 3.1)
    return mb.build()


def build_palmetto():
    mb = mk.MeshBuilder("Palmetto", 1.0)
    mb.color_fn = ao_color(0.0, 1.4)
    for i in range(7):
        az = 2 * math.pi * i / 7 + 0.3 * (i % 2)
        tilt = math.radians(40 + 20 * ((i * 5) % 3) / 2)
        stalk = (0.35 * math.cos(az), 0.45, 0.35 * math.sin(az))
        r = 0.9 + 0.35 * ((i * 3) % 4) / 3
        prev = None
        for k in range(6):
            a = az - 0.9 + 1.8 * k / 5
            out = (math.cos(a) * math.cos(tilt), math.sin(tilt), math.sin(a) * math.cos(tilt))
            pleat = 0.08 if k % 2 else -0.04
            tip = (stalk[0] + out[0] * r, stalk[1] + out[1] * r + pleat, stalk[2] + out[2] * r)
            if prev is not None:
                mb.face([stalk, prev, tip] if mk.face_normal([stalk, prev, tip]).y > 0 else [stalk, tip, prev], "leaf",
                        [(0.5, 0), (0, 1), (1, 1)], smooth=True)
            prev = tip
    return mb.build()


def walls_box(mb, half_x, half_z, height, mat="plaster"):
    poly = [(-half_x, -half_z), (half_x, -half_z), (half_x, half_z), (-half_x, half_z)]
    mk.ring_wall(mb, poly, -0.6, poly, height, mat)


def hip_roof(mb, half_x, half_z, eave_y, ridge_y, ridge_half, overhang, mat):
    ex, ez = half_x + overhang, half_z + overhang
    a, b, c, d = (-ex, eave_y, -ez), (ex, eave_y, -ez), (ex, eave_y, ez), (-ex, eave_y, ez)
    r0, r1 = (-ridge_half, ridge_y, 0.0), (ridge_half, ridge_y, 0.0)
    mb.quad_facing(a, b, r1, r0, (0.0, 1.0, -1.0), mat)
    mb.quad_facing(c, d, r0, r1, (0.0, 1.0, 1.0), mat)
    for tri, facing in (([b, c, r1], (1.0, 1.0, 0.0)), ([d, a, r0], (-1.0, 1.0, 0.0))):
        if mk.face_normal(tri).dot(mk.Vector(facing)) < 0:
            tri.reverse()
        mb.face(tri, mat)
    mk.cap(mb, [(p[0], p[2]) for p in (a, b, c, d)], eave_y - 0.01, mat, up=False)


def gable_roof(mb, half_x, half_z, eave_y, ridge_y, overhang, mat, wall_mat="plaster"):
    """Ridge along X; gable ends at +-half_x."""
    ex, ez = half_x + overhang, half_z + overhang
    a, b = (-ex, eave_y, -ez), (ex, eave_y, -ez)
    c, d = (ex, eave_y, ez), (-ex, eave_y, ez)
    r0, r1 = (-ex, ridge_y, 0.0), (ex, ridge_y, 0.0)
    mb.quad_facing(a, b, r1, r0, (0.0, 1.0, -1.0), mat)
    mb.quad_facing(c, d, r0, r1, (0.0, 1.0, 1.0), mat)
    for side in (-1, 1):
        tri = [(side * half_x, eave_y, -half_z), (side * half_x, eave_y, half_z), (side * half_x, ridge_y - 0.2, 0.0)]
        if mk.face_normal(tri).x * side < 0:
            tri.reverse()
        mb.face(tri, wall_mat)
    mk.cap(mb, [(p[0], p[2]) for p in (a, b, c, d)], eave_y - 0.01, mat, up=False)


def front_opening(mb, x, y0, w, h, z, mat="opening"):
    """Opening on the front wall (front faces -Z)."""
    mb.quad_facing((x + w / 2, y0, z - 0.02), (x - w / 2, y0, z - 0.02), (x - w / 2, y0 + h, z - 0.02),
                   (x + w / 2, y0 + h, z - 0.02), (0.0, 0.0, -1.0), mat)


def build_house_a():
    mb = mk.MeshBuilder("HouseA", 3.0)
    mb.color_fn = ao_color(-0.5, 3.0)
    walls_box(mb, 4.0, 3.0, 4.0)
    hip_roof(mb, 4.0, 3.0, 4.0, 5.9, 1.4, 0.45, "roof")
    front_opening(mb, 0.0, 0.0, 1.1, 2.2, -3.0)
    for x in (-2.5, 2.5):
        front_opening(mb, x, 1.2, 0.9, 1.2, -3.0)
        front_opening(mb, x - 0.65, 1.15, 0.38, 1.3, -3.0, "wood")
    return mb.build()


def build_house_b():
    mb = mk.MeshBuilder("HouseB", 3.0)
    mb.color_fn = ao_color(-0.5, 6.0)
    walls_box(mb, 5.0, 3.5, 7.0)
    gable_roof(mb, 5.0, 3.5, 7.0, 9.2, 0.45, "roof")
    front_opening(mb, -2.6, 0.0, 1.2, 2.3, -3.5)
    for x in (0.6, 3.2):
        front_opening(mb, x, 1.2, 0.9, 1.2, -3.5)
    for x in (-2.8, 0.0, 2.8):
        front_opening(mb, x, 3.8, 1.0, 2.1, -3.5)
    # Street balcony on wooden brackets.
    mk.box(mb, (0.0, 3.7, -4.15), (10.0, 0.18, 1.3), "wood")
    mk.box(mb, (0.0, 4.75, -4.75), (10.0, 0.08, 0.08), "wood")
    for k in range(9):
        x = -4.9 + 9.8 * k / 8
        mk.box(mb, (x, 4.25, -4.75), (0.07, 1.0, 0.07), "wood")
        if k % 2 == 0:
            mk.box(mb, (x, 3.3, -3.75), (0.12, 0.6, 0.5), "wood")
    return mb.build()


def build_house_c():
    mb = mk.MeshBuilder("HouseC", 2.0)
    mb.color_fn = ao_color(-0.5, 2.5)
    walls_box(mb, 2.6, 2.0, 2.3)
    hip_roof(mb, 2.6, 2.0, 2.3, 5.2, 0.8, 0.6, "thatch")
    front_opening(mb, 0.0, 0.0, 0.9, 1.9, -2.0)
    return mb.build()


def build_church():
    mb = mk.MeshBuilder("Church", 3.0)
    mb.color_fn = ao_color(-0.5, 8.0)
    # Nave along Z (front at -Z), gable roof along Z.
    poly = [(-5.0, -13.0), (5.0, -13.0), (5.0, 13.0), (-5.0, 13.0)]
    mk.ring_wall(mb, poly, -0.6, poly, 8.0, "plaster")
    ex, ez = 5.5, 13.4
    a, b, c, d = (-ex, 8.0, -ez), (-ex, 8.0, ez), (ex, 8.0, ez), (ex, 8.0, -ez)
    r0, r1 = (0.0, 11.6, -ez), (0.0, 11.6, ez)
    mb.quad_facing(a, b, r1, r0, (-1.0, 1.0, 0.0), "roof")
    mb.quad_facing(c, d, r0, r1, (1.0, 1.0, 0.0), "roof")
    mk.cap(mb, [(p[0], p[2]) for p in (a, b, c, d)], 7.99, "roof", up=False)
    # Front facade rising into a bell gable (espadana) with two bell openings and a cross.
    facade = [(-5.6, -0.6), (5.6, -0.6), (5.6, 9.0), (3.6, 9.0), (3.6, 12.4), (1.6, 14.2), (-1.6, 14.2),
              (-3.6, 12.4), (-3.6, 9.0), (-5.6, 9.0)]
    for z, facing in ((-13.4, -1.0), (-12.7, 1.0)):
        for tri in mk.triangulate(facade):
            pts = [(x, y, z) for x, y in tri]
            if mk.face_normal(pts).z * facing < 0:
                pts.reverse()
            mb.face(pts, "plaster")
    edge_normals = mk.outward_normals(facade)
    for i, ((x0, y0), (x1, y1)) in enumerate(zip(facade, facade[1:] + facade[:1])):
        nx, ny = edge_normals[i]
        mb.quad_facing((x0, y0, -13.4), (x1, y1, -13.4), (x1, y1, -12.7), (x0, y0, -12.7), (nx, ny, 0.0), "plaster")
    for x in (-1.6, 1.6):
        front_opening(mb, x, 10.6, 1.1, 1.8, -13.4)
    front_opening(mb, 0.0, 0.0, 2.2, 3.8, -13.4)
    front_opening(mb, 0.0, 5.2, 1.0, 1.4, -13.4)
    mk.box(mb, (0.0, 15.1, -13.05), (0.16, 1.8, 0.16), "wood")
    mk.box(mb, (0.0, 15.4, -13.05), (0.9, 0.16, 0.16), "wood")
    return mb.build()


# --- Placement ----------------------------------------------------------------------------

def fort_distance(x, z):
    return T.grounds_distance(x, z)


def in_town(x, z, margin=0.0):
    x0, x1, z0, z1 = TOWN
    return x0 - margin <= x <= x1 + margin and z0 - margin <= z <= z1 + margin


def scatter():
    rng = random.Random(1672)
    out = {name: [] for name in ("Palm", "Oak", "Palmetto", "HouseA", "HouseB", "HouseC", "Church")}

    def place(name, x, z, yaw=None, scale=None):
        y = T.height(x, z)
        out[name].append((x, y - 0.05, z, rng.uniform(0, 2 * math.pi) if yaw is None else yaw,
                          rng.uniform(0.8, 1.25) if scale is None else scale))

    # Mainland woods: patches of live oak and palm, open near the fort, the town and the shore.
    for gx in range(-900, 140, 28):
        for gz in range(-2300, 2300, 28):
            x, z = gx + rng.uniform(-12, 12), gz + rng.uniform(-12, 12)
            if x > T.shore_x(z) - 25 or fort_distance(x, z) < CLEAR_RADIUS or in_town(x, z, 30):
                continue
            if T.height(x, z) < 1.2:
                continue
            density = mk.smoothstep(0.42, 0.68, mk.fbm(x * 0.0035 + 4.0, 0.2, z * 0.0035 - 2.0, 3))
            if rng.random() < 0.05 + 0.5 * density:
                place("Oak" if rng.random() < 0.55 else "Palm", x, z)
    for gx in range(-700, 140, 20):
        for gz in range(-1600, 1600, 20):
            x, z = gx + rng.uniform(-8, 8), gz + rng.uniform(-8, 8)
            if x > T.shore_x(z) - 15 or fort_distance(x, z) < CLEAR_RADIUS or in_town(x, z, 10):
                continue
            if T.height(x, z) > 1.2 and rng.random() < 0.16:
                place("Palmetto", x, z)
    # Anastasia Island: palms along the dunes, palmetto scrub, a few oaks farther in.
    for gz in range(-1600, 2700, 22):
        for off in range(25, 430, 22):
            z = gz + rng.uniform(-9, 9)
            x = T.island_x(z) + off + rng.uniform(-9, 9)
            h = T.height(x, z)
            if h < 1.6:
                continue
            r = rng.random()
            if r < 0.22 * (1.3 - off / 600):
                place("Palm", x, z)
            elif r < 0.5:
                place("Palmetto", x, z, scale=rng.uniform(0.9, 1.5))
            elif r < 0.53 and off > 150:
                place("Oak", x, z, scale=rng.uniform(0.7, 1.0))
    # The colonial town: streets parallel to the bay, houses facing them, a plaza by the water.
    streets = [-60.0, -150.0, -240.0, -330.0, -420.0]
    cross = [300.0, 380.0, 460.0, 540.0, 650.0, 730.0, 810.0, 890.0, 970.0, 1050.0]
    for sx in streets:
        for z0, z1 in zip(cross, cross[1:]):
            for side in (-1, 1):
                x = sx + side * 10.0
                z = z0 + 9.0
                while z < z1 - 9.0:
                    if not (z0 >= 540.0 and z1 <= 650.0 and sx > -200.0):  # plaza
                        if sx == -60.0 and side > 0:
                            kind = "HouseB"
                        else:
                            r = rng.random()
                            kind = "HouseA" if r < 0.45 else ("HouseB" if r < 0.72 else "HouseC")
                        # Fronts face the street: -Z of the prop points across to it.
                        place(kind, x, z, yaw=(math.pi / 2 if side > 0 else -math.pi / 2), scale=rng.uniform(0.9, 1.1))
                    z += rng.uniform(12.0, 17.0)
    place("Church", -130.0, 595.0, yaw=-math.pi / 2, scale=1.0)
    for x, z in ((-95.0, 560.0), (-35.0, 560.0), (-95.0, 630.0), (-35.0, 630.0), (-65.0, 595.0)):
        place("Palm", x, z)
    return out


def write_scatter(path, data):
    names = list(data.keys())
    arrays = []
    for name in names:
        flat = ", ".join(f"{v:.2f}" for row in data[name] for v in row)
        arrays.append(f"PackedFloat32Array({flat})")
    text = ("[gd_resource type=\"Resource\" script_class=\"ScatterData\" load_steps=2 format=3]\n\n"
            "[ext_resource type=\"Script\" path=\"res://game/level/scatter_data.gd\" id=\"1_data\"]\n\n"
            "[resource]\n"
            "script = ExtResource(\"1_data\")\n"
            f"names = PackedStringArray({', '.join(chr(34) + n + chr(34) for n in names)})\n"
            f"data = [{', '.join(arrays)}]\n")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    counts = ", ".join(f"{n} {len(data[n])}" for n in names)
    print(f"[props] placements: {counts}")


def build():
    for name, color in [("bark", (0.36, 0.3, 0.24)), ("leaf", (0.3, 0.45, 0.18)), ("foliage", (0.2, 0.32, 0.14)),
                        ("plaster", (0.9, 0.88, 0.82)), ("roof", (0.32, 0.24, 0.18)), ("thatch", (0.62, 0.52, 0.32)),
                        ("opening", (0.04, 0.03, 0.03)), ("wood", (0.42, 0.3, 0.2))]:
        mk.material(name, color)
    builders = [build_palm, build_oak, build_palmetto, build_house_a, build_house_b, build_house_c, build_church]
    for i, builder in enumerate(builders):
        obj = builder()
        obj["preview_x"] = i * 16.0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--scatter", required=True)
    parser.add_argument("--blend", default="")
    parser.add_argument("--preview", default="")
    args = parser.parse_args(mk.script_args())
    mk.reset_scene()
    build()
    mk.export_glb(os.path.abspath(args.out))
    write_scatter(os.path.abspath(args.scatter), scatter())
    if args.blend:
        mk.save_blend(os.path.abspath(args.blend))
    if args.preview:
        # Line the props up for the preview only (the exported models stay at the origin).
        for obj in bpy.data.objects:
            if "preview_x" in obj:
                obj.location = mk.to_blender((obj["preview_x"] * 1.6, 0.0, 0.0))
        mk.render_views(os.path.abspath(args.preview), [
            ("lineup", (85.0, 22.0, -70.0), (85.0, 4.0, 0.0), None),
        ], color_type="MATERIAL")
    return 0


if __name__ == "__main__":
    main()

"""Builds the fort's cannon (cannon.glb): a late-1600s Spanish bronze gun on a garrison carriage.

Headless:
    blender -b --factory-startup -P tools/blender/build_cannon.py -- --out assets/models/cannon/cannon.glb
            [--blend build/blend/cannon.blend] [--preview build/previews/cannon]

Node hierarchy (what game/weapons/cannon.gd drives):
    Yaw (turns the whole carriage)  -> Carriage mesh
      Pitch (trunnion axis, 1.05 m up) -> Barrel mesh, Muzzle marker (2.3 m forward)
Local -Z (Godot forward) is where the gun points. Materials: bronze, iron, wood, opening.
"""

import argparse
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402
import meshkit as mk  # noqa: E402

TRUNNION_HEIGHT = 1.05
MUZZLE = -2.3
SEGMENTS = 20

# Barrel profile from the cascabel (+z, behind the trunnions) to the muzzle (-z):
# (z, outer radius). Proportions of a Spanish bronze 12-pounder of the period.
PROFILE = [
    (0.86, 0.0), (0.85, 0.035), (0.81, 0.07), (0.76, 0.075), (0.71, 0.05), (0.66, 0.045),
    (0.62, 0.14), (0.58, 0.25), (0.53, 0.275), (0.49, 0.275), (0.47, 0.245),
    (-0.42, 0.226), (-0.44, 0.245), (-0.50, 0.245), (-0.52, 0.215),
    (-1.05, 0.2), (-1.07, 0.215), (-1.11, 0.215), (-1.13, 0.192),
    (-2.02, 0.158), (-2.06, 0.172), (-2.1, 0.168), (-2.2, 0.192), (-2.27, 0.2), (-2.3, 0.185),
]
BORE_RADIUS = 0.065


def lathe(mb, profile, mat, center=(0.0, 0.0, 0.0)):
    """Surface of revolution around the local Z axis (gun barrel)."""
    cx, cy, cz = center
    rings = []
    for z, r in profile:
        ring = [(cx + r * math.cos(2 * math.pi * k / SEGMENTS), cy + r * math.sin(2 * math.pi * k / SEGMENTS), cz + z)
                for k in range(SEGMENTS)]
        rings.append(ring)
    for a in range(len(rings) - 1):
        for k in range(SEGMENTS):
            k2 = (k + 1) % SEGMENTS
            p = [rings[a][k], rings[a][k2], rings[a + 1][k2], rings[a + 1][k]]
            ang = 2 * math.pi * (k + 0.5) / SEGMENTS
            facing = (math.cos(ang), math.sin(ang), 0.0)
            if profile[a][1] == 0.0 or profile[a + 1][1] == 0.0:
                facing = (math.cos(ang), math.sin(ang), 0.35 if profile[a][1] == 0.0 else -0.35)
            u0, u1 = k / SEGMENTS, (k + 1) / SEGMENTS
            mb.quad_facing(p[0], p[1], p[2], p[3], facing, mat,
                           [(u0, profile[a][0]), (u1, profile[a][0]), (u1, profile[a + 1][0]), (u0, profile[a + 1][0])],
                           smooth=True)


def barrel():
    mb = mk.MeshBuilder("Barrel", 0.5)
    mb.color_fn = lambda p, n: (1.0, 0.0, 0.0, 1.0)
    lathe(mb, PROFILE, "bronze")
    # Muzzle face and dark bore.
    muzzle_r = PROFILE[-1][1]
    ring_o = [(muzzle_r * math.cos(2 * math.pi * k / SEGMENTS), muzzle_r * math.sin(2 * math.pi * k / SEGMENTS)) for k in range(SEGMENTS)]
    ring_i = [(BORE_RADIUS * math.cos(2 * math.pi * k / SEGMENTS), BORE_RADIUS * math.sin(2 * math.pi * k / SEGMENTS)) for k in range(SEGMENTS)]
    for k in range(SEGMENTS):
        k2 = (k + 1) % SEGMENTS
        mb.quad_facing((ring_o[k][0], ring_o[k][1], MUZZLE), (ring_o[k2][0], ring_o[k2][1], MUZZLE),
                       (ring_i[k2][0], ring_i[k2][1], MUZZLE), (ring_i[k][0], ring_i[k][1], MUZZLE),
                       (0.0, 0.0, -1.0), "bronze")
        mb.quad_facing((ring_i[k][0], ring_i[k][1], MUZZLE), (ring_i[k2][0], ring_i[k2][1], MUZZLE),
                       (ring_i[k2][0], ring_i[k2][1], MUZZLE + 0.6), (ring_i[k][0], ring_i[k][1], MUZZLE + 0.6),
                       (-ring_i[k][0], -ring_i[k][1], 0.0), "opening")
    # Trunnions (axis along X) with rimbases.
    for side in (-1, 1):
        cyl_x(mb, side * 0.2, side * 0.36, 0.068, "bronze")
        cyl_x(mb, side * 0.2, side * 0.25, 0.1, "bronze")
    # Dolphins: the lifting handles cast on Spanish bronze guns.
    for side in (-1, 1):
        mk.box(mb, (side * 0.085, 0.255, -0.28), (0.04, 0.07, 0.2), "bronze")
    mk.box(mb, (0.0, 0.24, 0.42), (0.06, 0.05, 0.05), "bronze")  # vent field
    return mb


def cyl_x(mb, x0, x1, r, mat, y=0.0, z=0.0, segments=12):
    """Cylinder along X from x0 to x1, centred at (y, z)."""
    ring = [(r * math.cos(2 * math.pi * k / segments), r * math.sin(2 * math.pi * k / segments)) for k in range(segments)]
    for k in range(segments):
        k2 = (k + 1) % segments
        a = (x0, y + ring[k][0], z + ring[k][1])
        b = (x0, y + ring[k2][0], z + ring[k2][1])
        c = (x1, y + ring[k2][0], z + ring[k2][1])
        d = (x1, y + ring[k][0], z + ring[k][1])
        ang = 2 * math.pi * (k + 0.5) / segments
        mb.quad_facing(a, b, c, d, (0.0, math.cos(ang), math.sin(ang)), mat, smooth=True)
    for x, sign in ((x0, -1), (x1, 1)):
        pts = [(x, y + p[0], z + p[1]) for p in ring]
        if mk.face_normal(pts).x * sign * (1 if x1 > x0 else -1) < 0:
            pts.reverse()
        mb.face(pts, mat)


def carriage():
    mb = mk.MeshBuilder("Carriage", 1.2)
    mb.color_fn = lambda p, n: (0.75 + 0.25 * mk.smoothstep(0.0, 0.8, p[1]), 0.0, 0.0, 1.0)
    # Cheeks: stepped side planks. Side profile (z, top y), bottom at y = 0.32.
    steps = [(-0.55, 0.78), (-0.2, 0.78), (-0.2, 0.92), (0.18, 0.92), (0.18, 0.74), (0.55, 0.74),
             (0.55, 0.6), (0.9, 0.6), (0.9, 0.46), (1.25, 0.46)]
    outline = [(z, y) for z, y in steps] + [(1.25, 0.32), (-0.55, 0.32)]
    for side in (-1, 1):
        x_in, x_out = side * 0.27, side * 0.41
        extrude_profile_x(mb, outline, x_in, x_out, "wood")
    # Axletrees, transom and bed.
    for z in (-0.35, 0.95):
        mk.box(mb, (0.0, 0.3, z), (1.18, 0.17, 0.17), "wood")
    mk.box(mb, (0.0, 0.5, -0.45), (0.56, 0.22, 0.14), "wood")
    mk.box(mb, (0.0, 0.36, 0.45), (0.56, 0.08, 0.9), "wood")
    # Quoin: the wedge under the breech that sets the elevation.
    mk.box(mb, (0.0, 0.58, 0.72), (0.3, 0.14, 0.42), "wood")
    # Trucks (solid wheels) with iron hubs.
    for z in (-0.35, 0.95):
        for side in (-1, 1):
            cyl_x(mb, side * 0.47, side * 0.6, 0.28, "wood", y=0.28, z=z, segments=16)
            cyl_x(mb, side * 0.6, side * 0.66, 0.06, "iron", y=0.28, z=z, segments=8)
    # Cap squares over the trunnions.
    for side in (-1, 1):
        mk.box(mb, (side * 0.34, 1.06, 0.0), (0.15, 0.04, 0.22), "iron")
    return mb


def extrude_profile_x(mb, outline, x0, x1, mat):
    """Prism from a (z, y) side profile, between x0 and x1."""
    poly_lo = [(x0, y, z) for z, y in outline]
    poly_hi = [(x1, y, z) for z, y in outline]
    n = len(outline)
    sign = 1.0 if x1 > x0 else -1.0
    for i in range(n):
        j = (i + 1) % n
        a, b, c, d = poly_lo[i], poly_lo[j], poly_hi[j], poly_hi[i]
        dz, dy = outline[j][0] - outline[i][0], outline[j][1] - outline[i][1]
        mb.quad_facing(a, b, c, d, (0.0, -dz, dy) if mk.signed_area(outline) > 0 else (0.0, dz, -dy), mat)
    for pts, nx in ((poly_lo, -sign), (poly_hi, sign)):
        for tri in mk.triangulate([(p[2], p[1]) for p in pts]):
            tri3 = [(pts[0][0], y, z) for z, y in tri]
            if mk.face_normal(tri3).x * nx < 0:
                tri3.reverse()
            mb.face(tri3, mat)


def build() -> None:
    mk.material("bronze", (0.55, 0.38, 0.18), metallic=0.9, roughness=0.35)
    mk.material("iron", (0.12, 0.12, 0.12), metallic=0.7, roughness=0.6)
    mk.material("wood", (0.42, 0.3, 0.2))
    mk.material("opening", (0.03, 0.03, 0.03))
    yaw = mk.empty("Yaw", (0.0, 0.0, 0.0))
    carriage_obj = carriage().build()
    carriage_obj.parent = yaw
    pitch = mk.empty("Pitch", (0.0, TRUNNION_HEIGHT, 0.0), parent=yaw)
    barrel_obj = barrel().build()
    barrel_obj.parent = pitch
    barrel_obj.location = (0.0, 0.0, 0.0)
    pitch.location = mk.to_blender((0.0, TRUNNION_HEIGHT, 0.0))
    muzzle = mk.empty("Muzzle", (0.0, 0.0, MUZZLE), parent=pitch)
    muzzle.location = mk.to_blender((0.0, 0.0, MUZZLE))
    # Barrel vertices are in its own frame (axis along -Z); the Pitch empty carries the height.
    print("[cannon] built")


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
        mk.render_views(os.path.abspath(args.preview), [
            ("side", (4.2, 1.2, -0.8), (0.0, 0.8, -0.6), None),
            ("front", (2.2, 2.0, -4.2), (0.0, 0.8, -0.6), None),
            ("rear", (-2.4, 2.4, 3.2), (0.0, 0.8, -0.4), None),
        ])
    return 0


if __name__ == "__main__":
    main()

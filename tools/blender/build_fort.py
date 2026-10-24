"""Builds the Castillo de San Marcos (fort.glb) from the HABS measurements in fort_dims.py.

Headless:
    blender -b --factory-startup -P tools/blender/build_fort.py -- --out assets/models/fort/fort.glb
            [--blend build/blend/fort.blend] [--preview build/previews/fort]

Origin: centre of the court, moat floor at y = 0 (game axes, see meshkit.py). Material slot
names are mapped to game materials by game/common/material_mapper.gd. Empties named Gun_*
mark gun emplacements: each sits at the throat of its embrasure, the point the gun turns about,
and its Godot -Z looks out through the opening. The node FortCollision-colonly (walls and the
parapet with its embrasures) becomes the fort's collision shape in Godot.
"""

import argparse
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402
import fort_dims as D  # noqa: E402
import meshkit as mk  # noqa: E402
from build_cannon import CARRIAGE_BACK, PROFILE, TRUNNION_HEIGHT, barrel_radius  # noqa: E402

# The guns' limits, mirrored from the game (min_elevation_deg in game/weapons/cannon.gd, the ball
# in game/weapons/projectile_pool.gd): embrasure floors slope so a gun at full depression clears them.
GUN_MIN_ELEVATION_DEG = -5.0
BALL_RADIUS = 0.18
# Room left between gun or ball and the masonry, metres.
GUN_CLEARANCE = 0.04

# Grounds plateau around the fort (x_min, x_max, z_min, z_max); the level terrain leaves it open.
GROUNDS = (-110.0, 75.0, -125.0, 140.0)
SEAWALL_BOTTOM = -3.6
SEAWALL_OVERRUN = 60.0
# Where the model's y = 0 (moat floor) sits in the level; sea level is world y = 0. High
# enough that wave crests never show in the dry moat.
WORLD_Y = 1.6
# Wall subdivision for vertex-colour detail, metres.
GRID = 2.0
WALL_UV = 3.0

MATERIALS = {
    "coquina": (0.62, 0.58, 0.50),
    "deck": (0.66, 0.62, 0.55),
    "garita": (0.60, 0.55, 0.47),
    "opening": (0.06, 0.05, 0.04),
    "wood": (0.42, 0.30, 0.20),
    "grass": (0.36, 0.42, 0.25),
    "moat": (0.40, 0.44, 0.28),
}

# Embrasures per wall segment: (bastion or "curtain", part) -> count.
EMBRASURES = {
    ("San Carlos", "face_ns"): 3, ("San Carlos", "face_ew"): 3, ("curtain", "E"): 4,
    ("San Agustin", "face_ew"): 3, ("San Agustin", "face_ns"): 3, ("curtain", "S"): 4,
    ("San Pedro", "face_ns"): 3, ("San Pedro", "face_ew"): 3, ("curtain", "W"): 5,
    ("San Pablo", "face_ew"): 3, ("San Pablo", "face_ns"): 3, ("curtain", "N"): 5,
}
# Gun emplacements for the player, north to south along the bay side: (segment, embrasure, name).
GUNS = [
    (("San Carlos", "face_ew"), 1, "Gun_1_SanCarlos"),
    (("curtain", "E"), 1, "Gun_2_EastCurtainNorth"),
    (("curtain", "E"), 2, "Gun_3_EastCurtainSouth"),
    (("San Agustin", "face_ew"), 1, "Gun_4_SanAgustin"),
]


# --- Plan ---------------------------------------------------------------------------------

def plan():
    """Exterior outline at parapet level: 20 vertices, an edge key per edge, salients."""
    hx, hz = D.COURT_X / 2, D.COURT_Z / 2
    x_e, x_w = hx + D.RING_EAST, -(hx + D.RING_WEST)
    z_n, z_s = -(hz + D.RING_NORTH), hz + D.RING_SOUTH
    cx, cz = (x_e + x_w) / 2, (z_n + z_s) / 2
    spans = {
        "E": (cz - D.CURTAIN_EAST / 2, cz + D.CURTAIN_EAST / 2),
        "W": (cz - D.CURTAIN_WEST / 2, cz + D.CURTAIN_WEST / 2),
        "N": (cx - D.CURTAIN_NORTH / 2, cx + D.CURTAIN_NORTH / 2),
        "S": (cx - D.CURTAIN_SOUTH / 2, cx + D.CURTAIN_SOUTH / 2),
    }
    blocks = {}
    salients = {}
    for name, b in D.BASTIONS.items():
        sx, sz = b["corner"]
        ew, ns = ("E" if sx > 0 else "W"), ("N" if sz < 0 else "S")
        x_c = x_e if sx > 0 else x_w
        z_c = z_n if sz < 0 else z_s
        z_end = spans[ew][0] if sz < 0 else spans[ew][1]
        x_end = spans[ns][1] if sx > 0 else spans[ns][0]
        junction_ew, shoulder_ew = (x_c, z_end), (x_c + sx * b["flank_ew"], z_end)
        junction_ns, shoulder_ns = (x_end, z_c), (x_end, z_c + sz * b["flank_ns"])
        salient = mk.circle_intersection(shoulder_ew, b["face_ew"], shoulder_ns, b["face_ns"], (0.0, 0.0))
        salients[name] = salient
        ns_first = (sx > 0) == (sz < 0)  # NE and SW start on their north/south side
        if ns_first:
            pts = [junction_ns, shoulder_ns, salient, shoulder_ew, junction_ew]
            keys = ["flank_ns", "face_ns", "face_ew", "flank_ew"]
        else:
            pts = [junction_ew, shoulder_ew, salient, shoulder_ns, junction_ns]
            keys = ["flank_ew", "face_ew", "face_ns", "flank_ns"]
        blocks[name] = (pts, [(name, k) for k in keys])
    order = [("San Carlos", "E"), ("San Agustin", "S"), ("San Pedro", "W"), ("San Pablo", "N")]
    poly, keys = [], []
    for name, curtain in order:
        pts, ks = blocks[name]
        poly += pts
        keys += ks + [("curtain", curtain)]
    return poly, keys, salients, (x_e, x_w, z_n, z_s, cx, cz)


def ravelin_outline(z_s: float, cx: float):
    gorge_x = D.RAVELIN_GORGE_SIDE * math.cos(math.radians(25))
    gorge_z = D.RAVELIN_GORGE_SIDE * math.sin(math.radians(25))
    apex_z = z_s + D.RAVELIN_GAP
    reach = math.sqrt(max(D.RAVELIN_FACE ** 2 - gorge_x ** 2, 1.0))
    gate = 1.9
    return [(cx - gate, apex_z + gate * gorge_z / gorge_x), (cx + gate, apex_z + gate * gorge_z / gorge_x),
            (cx + gorge_x, apex_z + gorge_z), (cx, apex_z + gorge_z + reach), (cx - gorge_x, apex_z + gorge_z)]


def counterscarp(poly, keys, salients, ravelin):
    """Outer edge of the moat: bastion faces offset by the moat width, rounded around each
    salient, meeting in a V before each curtain and running around the ravelin on the south."""
    normals = mk.outward_normals(poly)
    lines = {}
    for i, key in enumerate(keys):
        if key[1].startswith("face"):
            a, b = poly[i], poly[(i + 1) % len(poly)]
            n = normals[i]
            lines[key] = ((a[0] + n[0] * D.MOAT_WIDTH, a[1] + n[1] * D.MOAT_WIDTH), (b[0] - a[0], b[1] - a[1]), n)
    r_normals = mk.outward_normals(ravelin)
    r_east = ((ravelin[2][0] + r_normals[2][0] * D.RAVELIN_MOAT, ravelin[2][1] + r_normals[2][1] * D.RAVELIN_MOAT),
              (ravelin[3][0] - ravelin[2][0], ravelin[3][1] - ravelin[2][1]), r_normals[2])
    r_west = ((ravelin[3][0] + r_normals[3][0] * D.RAVELIN_MOAT, ravelin[3][1] + r_normals[3][1] * D.RAVELIN_MOAT),
              (ravelin[4][0] - ravelin[3][0], ravelin[4][1] - ravelin[3][1]), r_normals[3])

    def arc(center, n1, n2, radius, steps=8):
        a1, a2 = math.atan2(n1[1], n1[0]), math.atan2(n2[1], n2[0])
        delta = (a2 - a1 + math.pi) % (2 * math.pi) - math.pi
        return [(center[0] + radius * math.cos(a1 + delta * k / steps),
                 center[1] + radius * math.sin(a1 + delta * k / steps)) for k in range(steps + 1)]

    def meet(l1, l2):
        return mk.line_intersection(l1[0], l1[1], l2[0], l2[1])

    sequence = [("San Carlos", "face_ns", "face_ew"), ("San Agustin", "face_ew", "face_ns"),
                ("San Pedro", "face_ns", "face_ew"), ("San Pablo", "face_ew", "face_ns")]
    out = []
    for i, (name, first, second) in enumerate(sequence):
        out += arc(salients[name], lines[(name, first)][2], lines[(name, second)][2], D.MOAT_WIDTH)
        nxt = sequence[(i + 1) % 4]
        here = lines[(name, second)]
        there = lines[(nxt[0], nxt[1])]
        if name == "San Agustin":
            out.append(meet(here, r_east))
            out += arc(ravelin[3], r_east[2], r_west[2], D.RAVELIN_MOAT, 6)
            out.append(meet(r_west, there))
        else:
            out.append(meet(here, there))
    return out


# --- Builders -----------------------------------------------------------------------------

def fort_color(p, n):
    x, y, z = p
    ao = 0.6 + 0.4 * mk.smoothstep(-0.3, 2.8, y)
    if D.SCARP_TOP - 0.9 < y < D.SCARP_TOP + 0.05:
        ao *= 0.82
    ao *= 0.86 + 0.28 * mk.fbm(x * 0.21 + 7.0, y * 0.06, z * 0.21, 3)
    plaster = mk.smoothstep(0.56, 0.68, mk.fbm(x * 0.07 + 3.1, y * 0.11 - 2.0, z * 0.07 - 1.7, 4))
    plaster *= mk.smoothstep(1.0, 3.0, y)
    return (min(ao, 1.0), plaster, 0.0, 1.0)


def walls(mb, poly, ravelin, segments):
    """Scarp and cordon of the fort, and the ravelin's scarp."""
    base = mk.offset_polygon(poly, (D.SCARP_TOP + 0.3) * D.SCARP_BATTER)
    mk.ring_wall(mb, base, -0.3, poly, D.SCARP_TOP, "coquina", cell=GRID, segments=segments)
    cordon_rings = []
    for k in range(5):
        a = -math.pi / 2 + math.pi * k / 4
        cordon_rings.append((mk.offset_polygon(poly, D.CORDON_PROJECTION * math.cos(a)),
                             D.SCARP_TOP + D.CORDON_HEIGHT * (0.5 + 0.5 * math.sin(a))))
    for (r0, y0), (r1, y1) in zip(cordon_rings, cordon_rings[1:]):
        mk.ring_wall(mb, r0, y0, r1, y1, "coquina", segments=segments)
    # Ravelin: lower walls without a cordon.
    r_top = 3.6
    r_base = mk.offset_polygon(ravelin, (r_top + 0.3) * D.SCARP_BATTER)
    mk.ring_wall(mb, r_base, -0.3, ravelin, r_top, "coquina", cell=GRID,
                 segments=mk.segment_counts(ravelin, GRID))


def parapet(name, outer, inner, y_outer_bottom, y_inner_bottom, y_top, segments):
    """Closed parapet ring (a watertight solid, so embrasures can be cut with booleans)."""
    mb = mk.MeshBuilder(name, WALL_UV)
    mb.color_fn = fort_color
    mk.ring_wall(mb, outer, y_outer_bottom, outer, y_top - 0.12, "coquina", segments=segments)
    mk.ring_wall(mb, outer, y_top - 0.12, inner, y_top, "deck", vertical=1, segments=segments)
    mk.ring_wall(mb, inner, y_inner_bottom, inner, y_top, "coquina", outward=False, segments=segments)
    mk.ring_wall(mb, outer, y_outer_bottom, inner, y_inner_bottom, "coquina", vertical=-1, segments=segments)
    return mb


def embrasure_sites(poly, keys):
    """(position on the exterior line, outward normal, key, index) for every embrasure."""
    normals = mk.outward_normals(poly)
    sites = []
    for i, key in enumerate(keys):
        count = EMBRASURES.get(key, 0)
        a, b = poly[i], poly[(i + 1) % len(poly)]
        margin = 0.0 if key[0] == "curtain" else 0.15
        for k in range(count):
            t = margin + (1 - 2 * margin) * (k + 0.5) / count
            sites.append(((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t), normals[i], key, k))
    return sites


def embrasure_floor():
    """Heights above the deck of the embrasure floor at the throat (the parapet's inner face)
    and at the mouth. The floor slopes with the bore at full depression, just below the barrel
    (which turns about the throat) and then the ball."""
    slope = math.tan(math.radians(-GUN_MIN_ELEVATION_DEG))
    axis_at_throat = TRUNNION_HEIGHT - CARRIAGE_BACK * slope
    # The thickest part of the barrel ahead of the throat, or the ball, whichever is bigger.
    radii = [r for z, r in PROFILE if -z >= CARRIAGE_BACK] + [barrel_radius(-CARRIAGE_BACK)]
    throat = axis_at_throat - max(radii + [BALL_RADIUS]) - GUN_CLEARANCE
    return throat, throat - D.PARAPET_THICKNESS * slope


def embrasure_arc_deg():
    """How far a gun turning about the throat can be laid either side of the embrasure's axis
    before its ball touches a cheek at the mouth (game/fort/gun_position.gd stays within it)."""
    depth_in = D.PARAPET_THICKNESS + 0.6
    w_in, w_out = D.EMBRASURE_INNER_WIDTH / 2, D.EMBRASURE_OUTER_WIDTH / 2
    mouth = w_in + (w_out - w_in) * depth_in / (depth_in + 0.6)
    return math.degrees(math.atan((mouth - BALL_RADIUS - GUN_CLEARANCE) / D.PARAPET_THICKNESS))


def embrasure_cutter(site, index, floor):
    """Solid that cuts one embrasure: the HABS splay in plan, open above, and a floor sloping down
    toward the mouth (see embrasure_floor). It overruns both faces of the parapet by 0.6 m."""
    (px, pz), (nx, nz), _, _ = site
    tx, tz = -nz, nx
    depth_in = D.PARAPET_THICKNESS + 0.6
    w_in, w_out = D.EMBRASURE_INNER_WIDTH / 2, D.EMBRASURE_OUTER_WIDTH / 2
    throat, mouth = floor
    slope = (throat - mouth) / D.PARAPET_THICKNESS

    def corner(u, half_width, y):
        # u: metres outward from the exterior line; y: height above the deck.
        return (px + nx * u + tx * half_width, D.TERREPLEIN + y, pz + nz * u + tz * half_width)

    bottom = [corner(-depth_in, w_in, mouth + slope * depth_in), corner(0.6, w_out, mouth - slope * 0.6),
              corner(0.6, -w_out, mouth - slope * 0.6), corner(-depth_in, -w_in, mouth + slope * depth_in)]
    top = [(x, D.PARAPET_TOP + 1.0, z) for x, _, z in bottom]
    mb = mk.MeshBuilder(f"Cutter{index}", WALL_UV)
    mb.color_fn = fort_color
    mk.solid(mb, bottom, top, "coquina")
    return mb.build()


def court(mb, hx, hz):
    rect = [(-hx, -hz), (hx, -hz), (hx, hz), (-hx, hz)]
    rim = mk.offset_polygon(rect, 0.7)
    top = D.TERREPLEIN + 0.9
    mk.ring_wall(mb, rect, D.COURT_FLOOR, rect, top, "coquina", outward=False, cell=GRID)
    mk.ring_wall(mb, rim, D.TERREPLEIN - 0.05, rim, top, "coquina")
    mk.cap(mb, rim, top, "deck", holes=[rect])
    mk.cap(mb, rect, D.COURT_FLOOR, "deck")
    return rect, rim


def arched_opening(mb, origin, along, facing, width, height, y0, mat="opening"):
    """Flat arched opening (door or window) just in front of a wall."""
    ox, oz = origin
    ax, az = along
    fx, fz = facing
    r = width / 2
    pts = [(-r, 0.0), (r, 0.0), (r, height - r)]
    for k in range(1, 8):
        a = math.pi * k / 8
        pts.append((r * math.cos(a), height - r + r * math.sin(a)))
    pts.append((-r, height - r))
    world = [(ox + ax * u + fx * 0.03, y0 + v, oz + az * u + fz * 0.03) for u, v in pts]
    if mk.face_normal(world).dot(mk.Vector((fx, 0.0, fz))) < 0:
        world.reverse()
    mb.face(world, mat)


def court_openings(mb, hx, hz):
    sides = [  # (start corner, along, facing into the court, length, doors)
        ((-hx, -hz), (1, 0), (0, 1), 2 * hx, 7),
        ((hx, hz), (-1, 0), (0, -1), 2 * hx, 6),
        ((hx, -hz), (0, 1), (-1, 0), 2 * hz, 4),
        ((-hx, hz), (0, -1), (1, 0), 2 * hz, 6),
    ]
    for (sx, sz), (ax, az), facing, length, doors in sides:
        for k in range(doors):
            t = (k + 0.5) / doors * length
            origin = (sx + ax * t, sz + az * t)
            arched_opening(mb, origin, (ax, az), facing, 1.5, 3.2, D.COURT_FLOOR)
            arched_opening(mb, origin, (ax, az), facing, 0.9, 1.3, D.COURT_FLOOR + 4.2)
    # The sally port passage, centred on the south side.
    arched_opening(mb, (0.0, hz), (-1, 0), (0, -1), D.SALLY_PORT_WIDTH, D.SALLY_PORT_HEIGHT, D.COURT_FLOOR)


def court_stair(mb, hx, hz):
    rise = D.TERREPLEIN - D.COURT_FLOOR
    steps = math.ceil(rise / 0.3)
    tread = 0.36
    z_top = hz - 1.0
    for k in range(steps):
        h = min((k + 1) * rise / steps, rise)
        zc = z_top - (steps - k - 0.5) * tread
        mk.box(mb, (hx - 1.25, D.COURT_FLOOR + h / 2, zc), (2.5, h, tread), "coquina")


def tower(mb, center, radius, y_base, body_top, dome_r, openings_band, inward, door_y):
    """Garita or bell tower: corbel, body, cap moulding, dome, openings."""
    cx, cz = center
    mk.cylinder(mb, center, 0.25, y_base - 0.9, y_base, "garita", radius_top=radius + 0.04, top=False)
    mk.cylinder(mb, center, radius + 0.12, y_base, y_base + D.CORDON_HEIGHT, "garita")
    mk.cylinder(mb, center, radius, y_base + D.CORDON_HEIGHT, body_top, "garita", top=False)
    mk.cylinder(mb, center, radius + 0.08, body_top, body_top + 0.18, "garita", top=False)
    mk.dome(mb, center, radius + 0.02, body_top + 0.18, "garita")
    ix, iz = inward
    out_angle = math.atan2(-iz, -ix)
    band_lo, band_hi, count, w = openings_band

    def surface(width):
        # Flat openings sit on the chord, so push them out by the arc's sagitta.
        return radius - 0.03 + (radius - math.sqrt(max(radius * radius - width * width / 4, 0.0)))

    for k in range(count):
        a = out_angle + (k - (count - 1) / 2) * (2 * math.pi / count if count >= 4 else 0.9)
        fx, fz = math.cos(a), math.sin(a)
        origin = (cx + fx * surface(w), cz + fz * surface(w))
        arched_opening(mb, origin, (-fz, fx), (fx, fz), w, band_hi - band_lo, band_lo)
    origin = (cx + ix * surface(0.75), cz + iz * surface(0.75))
    arched_opening(mb, origin, (-iz, ix), (ix, iz), 0.75, 1.9, door_y)


def towers(mb, poly, salients):
    normals = mk.outward_normals(poly)
    for name, salient in salients.items():
        i = poly.index(salient)
        n1, n2 = normals[i - 1], normals[i]
        inward = (-(n1[0] + n2[0]), -(n1[1] + n2[1]))
        length = math.hypot(*inward)
        inward = (inward[0] / length, inward[1] / length)
        if D.BASTIONS[name]["tower"] == "bell":
            r = D.BELL_TOWER_RADIUS
            c = (salient[0] + inward[0] * r * 1.1, salient[1] + inward[1] * r * 1.1)
            top = D.BELL_TOWER_TOP - D.BELL_TOWER_DOME - 0.18
            tower(mb, c, r, D.SCARP_TOP, top, r, (top - D.BELL_TOWER_OPENINGS + 0.3, top - 0.3, 4, 0.95),
                  inward, D.TERREPLEIN)
        else:
            r = D.GARITA_RADIUS
            c = (salient[0] + inward[0] * r * 0.7, salient[1] + inward[1] * r * 0.7)
            top = D.PARAPET_TOP + 0.75
            tower(mb, c, r, D.SCARP_TOP, top, r, (D.PARAPET_TOP + 0.1, D.PARAPET_TOP + 0.45, 3, 0.18),
                  inward, D.TERREPLEIN)


def moat_and_grounds(mb, poly, ravelin, scarp_line):
    fort_base = mk.offset_polygon(poly, D.SCARP_TOP * D.SCARP_BATTER)
    rav_base = mk.offset_polygon(ravelin, 3.6 * D.SCARP_BATTER)
    mk.cap(mb, scarp_line, 0.0, "moat", holes=[fort_base, rav_base])
    mk.ring_wall(mb, scarp_line, -0.2, scarp_line, D.GRADE, "coquina", outward=False, cell=GRID)
    x0, x1, z0, z1 = GROUNDS
    rect = [(x0, z0), (x1, z0), (x1, z1), (x0, z1)]
    mk.cap(mb, rect, D.GRADE, "grass", holes=[scarp_line])
    # Seawall along the bay, with a low parapet. It runs past the grounds so the terrain's
    # shore bank meets it cleanly at both ends.
    s0, s1 = z0 - SEAWALL_OVERRUN, z1 + SEAWALL_OVERRUN
    wall = [(x1, s0), (x1, s1)]
    mk.ring_wall(mb, wall, SEAWALL_BOTTOM, wall, D.GRADE + 0.6, "coquina", cell=GRID, closed=False)
    mk.box(mb, (x1 - 0.6, D.GRADE + 0.3, (s0 + s1) / 2), (1.2, 0.6, s1 - s0), "coquina")


def ravelin_body(mb, ravelin):
    """Ravelin deck and parapet (gorge side low)."""
    inner = mk.offset_polygon(ravelin, -1.6)
    mk.ring_wall(mb, ravelin, 3.6, ravelin, 5.6, "coquina", cell=GRID,
                 segments=mk.segment_counts(ravelin, GRID))
    mk.ring_wall(mb, inner, 4.4, inner, 5.7, "coquina", outward=False)
    mk.ring_wall(mb, ravelin, 5.6, inner, 5.7, "deck", vertical=1)
    mk.cap(mb, inner, 4.4, "deck")


def bridge(mb, start, end, width, y_top):
    """Timber bridge on coquina piers, with rails."""
    sx, sz = start
    ex, ez = end
    length = math.hypot(ex - sx, ez - sz)
    yaw = math.atan2(ex - sx, ez - sz)
    cx, cz = (sx + ex) / 2, (sz + ez) / 2
    mk.box(mb, (cx, y_top - 0.18, cz), (width, 0.36, length), "wood", yaw)
    dx, dz = (ex - sx) / length, (ez - sz) / length
    px, pz = dz, -dx
    piers = max(1, int(length // 5))
    for k in range(1, piers + 1):
        t = k / (piers + 1)
        x, z = sx + (ex - sx) * t, sz + (ez - sz) * t
        mk.box(mb, (x, (y_top - 0.36) / 2, z), (width * 0.8, y_top - 0.36, 1.0), "coquina", yaw)
    posts = max(2, int(length // 2.5) + 1)
    for side in (-1, 1):
        for k in range(posts):
            t = k / (posts - 1)
            x = sx + (ex - sx) * t + px * side * (width / 2 - 0.1)
            z = sz + (ez - sz) * t + pz * side * (width / 2 - 0.1)
            mk.box(mb, (x, y_top + 0.5, z), (0.14, 1.0, 0.14), "wood", yaw)
        mx, mz = cx + px * side * (width / 2 - 0.1), cz + pz * side * (width / 2 - 0.1)
        mk.box(mb, (mx, y_top + 1.0, mz), (0.12, 0.1, length), "wood", yaw)


def portal(mb, x, wall_z, facing_z, wall_top, door_w, door_h):
    """Vertical gateway frame on a sloped (battered) wall, with an arched door. The wall's
    outline is at wall_z at height wall_top; facing_z is +1 (south) or -1 (north).
    Returns the z of the portal's front face."""
    face_z = wall_z + facing_z * (D.SCARP_BATTER * (wall_top - D.GRADE) + 0.25)
    w, h = door_w + 2.4, door_h + 1.3
    mk.box(mb, (x, D.GRADE + h / 2 - 0.2, face_z - facing_z * 1.0), (w, h, 2.0), "coquina")
    arched_opening(mb, (x, face_z), (1, 0), (0, facing_z), door_w, door_h, D.GRADE)
    return face_z


def ray_to_polygon(origin, direction, poly):
    best = None
    for i in range(len(poly)):
        a, b = poly[i], poly[(i + 1) % len(poly)]
        hit = mk.line_intersection(origin, direction, a, (b[0] - a[0], b[1] - a[1]))
        if hit is None:
            continue
        t = ((hit[0] - origin[0]) * direction[0] + (hit[1] - origin[1]) * direction[1])
        seg = ((hit[0] - a[0]) * (b[0] - a[0]) + (hit[1] - a[1]) * (b[1] - a[1])) / (
            (b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2)
        if t > 0 and 0 <= seg <= 1 and (best is None or t < best[0]):
            best = (t, hit)
    return best[1] if best else None


def collision(poly, inner, ravelin, scarp_line, sites, floor):
    """Two simplified collision meshes: the walls with the parapet and its embrasures (fort
    layer in the game: hits damage the fort, and no ball passes through a merlon) and the moat
    floor plus grounds (terrain layer: hits only raise dust)."""
    walls_mb = mk.MeshBuilder("FortCollision-colonly")
    base = mk.offset_polygon(poly, D.SCARP_TOP * D.SCARP_BATTER)
    rav_base = mk.offset_polygon(ravelin, 3.6 * D.SCARP_BATTER)
    mk.prism(walls_mb, base, -0.3, D.TERREPLEIN, "coquina")
    mk.prism(walls_mb, rav_base, -0.3, 4.4, "coquina")
    walls = walls_mb.build()
    parapet_obj = parapet("ParapetCollision", poly, inner, D.SCARP_TOP + D.CORDON_HEIGHT,
                          D.TERREPLEIN - 0.05, D.PARAPET_TOP, None).build()
    mk.apply_boolean_difference(parapet_obj, [embrasure_cutter(s, i, floor) for i, s in enumerate(sites)])
    with bpy.context.temp_override(active_object=walls, selected_editable_objects=[walls, parapet_obj],
                                   selected_objects=[walls, parapet_obj]):
        bpy.ops.object.join()
    ground_mb = mk.MeshBuilder("GroundsCollision-colonly")
    mk.cap(ground_mb, scarp_line, 0.0, "moat", holes=[base, rav_base])
    x0, x1, z0, z1 = GROUNDS
    mk.cap(ground_mb, [(x0, z0), (x1, z0), (x1, z1), (x0, z1)], D.GRADE, "grass", holes=[scarp_line])
    ground_mb.build()


def build():
    for name, color in MATERIALS.items():
        mk.material(name, color)
    poly, keys, salients, (x_e, x_w, z_n, z_s, cx, cz) = plan()
    ravelin = ravelin_outline(z_s, cx)
    scarp_line = counterscarp(poly, keys, salients, ravelin)
    hx, hz = D.COURT_X / 2, D.COURT_Z / 2

    segments = mk.segment_counts(poly, GRID)
    mb = mk.MeshBuilder("Fort", WALL_UV)
    mb.color_fn = fort_color
    walls(mb, poly, ravelin, segments)
    inner = mk.offset_polygon(poly, -D.PARAPET_THICKNESS)
    rect, rim = court(mb, hx, hz)
    mk.cap(mb, inner, D.TERREPLEIN, "deck", holes=[rim])
    court_openings(mb, hx, hz)
    court_stair(mb, hx, hz)
    mk.cylinder(mb, (hx - 6.0, hz - 5.0), 1.0, D.COURT_FLOOR, D.COURT_FLOOR + 0.9, "coquina")
    towers(mb, poly, salients)
    moat_and_grounds(mb, poly, ravelin, scarp_line)
    ravelin_body(mb, ravelin)
    gorge_mid = ((ravelin[0][0] + ravelin[1][0]) / 2, (ravelin[0][1] + ravelin[1][1]) / 2)
    sally_front = portal(mb, cx, z_s, 1, D.SCARP_TOP, D.SALLY_PORT_WIDTH, D.SALLY_PORT_HEIGHT)
    gate_front = portal(mb, gorge_mid[0], gorge_mid[1], -1, 3.6, 2.6, 3.0)
    bridge(mb, (cx, sally_front), (gorge_mid[0], gate_front), 3.4, D.GRADE)
    exit_start = ((ravelin[1][0] + ravelin[2][0]) / 2, (ravelin[1][1] + ravelin[2][1]) / 2)
    exit_end = ray_to_polygon(exit_start, (1.0, 0.0), scarp_line)
    if exit_end:
        bridge(mb, (exit_start[0] + 0.4, exit_start[1]), (exit_end[0] + 0.5, exit_end[1]), 3.0, D.GRADE)
    fort = mb.build()

    pmb = parapet("Parapet", poly, inner, D.SCARP_TOP + D.CORDON_HEIGHT, D.TERREPLEIN - 0.05,
                  D.PARAPET_TOP, segments)
    parapet_obj = pmb.build()
    sites = embrasure_sites(poly, keys)
    floor = embrasure_floor()
    mk.apply_boolean_difference(parapet_obj, [embrasure_cutter(s, i, floor) for i, s in enumerate(sites)])

    with bpy.context.temp_override(active_object=fort, selected_editable_objects=[fort, parapet_obj],
                                   selected_objects=[fort, parapet_obj]):
        bpy.ops.object.join()
    mk.weld(fort)

    for (key, index, name) in GUNS:
        site = next(s for s in sites if s[2] == key and s[3] == index)
        (px, pz), (nx, nz), _, _ = site
        # The throat: the middle of the embrasure at the parapet's inner face.
        depth = D.PARAPET_THICKNESS
        mk.empty(name, (px - nx * depth, D.TERREPLEIN, pz - nz * depth), facing=(nx, nz))
    collision(poly, inner, ravelin, scarp_line, sites, floor)
    print_summary(poly, salients, ravelin, fort)
    print(f"[fort] embrasure floor {floor[0]:.2f} m above the deck at the throat, {floor[1]:.2f} m at "
          f"the mouth; a gun turning at the throat can be laid {embrasure_arc_deg():.1f} deg either side")


def print_summary(poly, salients, ravelin, fort):
    xs = [p[0] for p in poly]
    zs = [p[1] for p in poly]
    print(f"[fort] outline x {min(xs):.1f}..{max(xs):.1f} m, z {min(zs):.1f}..{max(zs):.1f} m")
    for name, s in salients.items():
        print(f"[fort] salient {name}: ({s[0]:.1f}, {s[1]:.1f})")
    print(f"[fort] ravelin salient z {ravelin[3][1]:.1f}; triangles ~{sum(len(p.vertices) - 2 for p in fort.data.polygons)}")


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
        mk.render_views(os.path.abspath(args.preview), [
            ("top", (0.0, 400.0, 0.001), (0.0, 0.0, 0.0), 200.0),
            ("southeast", (150.0, 70.0, 150.0), (0.0, 5.0, 0.0), None),
            ("bay", (230.0, 22.0, -20.0), (10.0, 8.0, 0.0), None),
            ("deck", (34.0, 12.5, 22.0), (44.0, 9.0, -40.0), None),
            ("court", (-10.0, 16.0, 30.0), (8.0, 4.0, -10.0), None),
        ])
    return 0


if __name__ == "__main__":
    main()

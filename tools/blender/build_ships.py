"""Builds the enemy ships (pinnace, caravel, galleon) from one parametric generator.

Headless:
    blender -b --factory-startup -P tools/blender/build_ships.py -- --out-dir assets/models/ships
            [--blend-dir build/blend] [--preview-dir build/previews/ships] [--only galleon]

Model frame (game axes): origin at the waterline amidships, -Z toward the bow, +X to starboard.
Objects:
    Hull           planking, decks, castles, transom, gunports, guns, beakhead, ensign
    Mast_<name>    one per mast and the bowsprit, origin at its foot (so it can topple), with
                   its yards, sails, tops, shrouds, stays and pennant
    Port_<P|S>_<n> empties at the gun muzzles (port/starboard), for return-fire effects
Materials: hull, hull_dark, hull_paint, deck, opening, iron, spar, sail, rope, flag, gold.
"""

import argparse
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402
import meshkit as mk  # noqa: E402

STATIONS = 26
# Hull section levels: (height as a function of draft D and freeboard F, half-beam factor).
LEVELS = [
    (lambda d, f, bw: -d, 0.04),
    (lambda d, f, bw: -0.9 * d, 0.38),
    (lambda d, f, bw: -0.6 * d, 0.78),
    (lambda d, f, bw: -0.25 * d, 0.95),
    (lambda d, f, bw: 0.0, 0.99),
    (lambda d, f, bw: 0.18 * f, 1.0),
    (lambda d, f, bw: 0.27 * f, 1.0),
    (lambda d, f, bw: 0.55 * f, 0.965),
    (lambda d, f, bw: 0.63 * f, 0.95),
    (lambda d, f, bw: 0.85 * f, 0.89),
    (lambda d, f, bw: f, 0.86),
    (lambda d, f, bw: f + bw, 0.83),
]
# Material of the band between level i and i+1: tarred bottom, wales, natural planking,
# painted upper works.
BANDS = ["hull_dark", "hull_dark", "hull_dark", "hull_dark", "hull", "hull_dark", "hull", "hull_dark",
         "hull_paint", "hull_paint", "hull_paint"]
DECK_LEVEL = 10
RAIL_LEVEL = 11
BULWARK_THICKNESS = 0.14

SPECS = {
    "pinnace": dict(
        length=18.0, beam=5.2, draft=1.6, freeboard=1.5, sheer_aft=0.9, sheer_fwd=0.7, bulwark=0.8,
        stern_tiers=[(0.2, 1.5)], fore_tiers=[], beakhead=False,
        masts=[
            dict(name="Fore", s=0.7, height=12.0, sails=[(0.42, 0.13, 2.9, 3.2), (0.78, 0.44, 2.1, 2.8)]),
            dict(name="Main", s=0.42, height=13.5, sails=[(0.44, 0.12, 3.2, 3.5), (0.8, 0.46, 2.3, 3.0)]),
        ],
        bowsprit=dict(length=6.5, angle=22.0, spritsail=False),
        gunports=[], guns=False, port_size=0.42, windows=2, lanterns=1,
        ensign=dict(height=3.0, size=(1.8, 1.2)),
    ),
    "caravel": dict(
        length=24.0, beam=7.0, draft=2.3, freeboard=2.0, sheer_aft=1.4, sheer_fwd=1.0, bulwark=0.9,
        stern_tiers=[(0.26, 2.0)], fore_tiers=[(0.86, 1.4)], beakhead=False,
        masts=[
            dict(name="Fore", s=0.74, height=15.0, sails=[(0.44, 0.13, 3.6, 4.0), (0.78, 0.46, 2.6, 3.4)]),
            dict(name="Main", s=0.48, height=18.0, sails=[(0.44, 0.12, 4.4, 4.8), (0.8, 0.46, 3.0, 4.0)]),
            dict(name="Mizzen", s=0.17, height=12.0, lateen=True),
        ],
        bowsprit=dict(length=8.0, angle=25.0, spritsail=True),
        gunports=[(0.42, 5, 0.25, 0.72)], guns=True, port_size=0.48, windows=3, lanterns=1,
        ensign=dict(height=3.5, size=(2.4, 1.6)),
    ),
    "galleon": dict(
        length=40.0, beam=10.5, draft=3.8, freeboard=3.0, sheer_aft=2.0, sheer_fwd=1.4, bulwark=1.0,
        stern_tiers=[(0.32, 2.4), (0.15, 2.2)], fore_tiers=[(0.84, 2.2)], beakhead=True,
        masts=[
            dict(name="Fore", s=0.76, height=25.0, sails=[(0.45, 0.12, 6.0, 6.6), (0.78, 0.47, 4.2, 5.6)]),
            dict(name="Main", s=0.5, height=29.0, sails=[(0.45, 0.11, 7.0, 7.6), (0.8, 0.47, 4.8, 6.6)]),
            dict(name="Mizzen", s=0.2, height=19.0, lateen=True),
        ],
        bowsprit=dict(length=13.0, angle=28.0, spritsail=True),
        gunports=[(0.41, 9, 0.18, 0.8), (0.78, 8, 0.22, 0.76)], guns=True, port_size=0.62, windows=4, lanterns=3,
        ensign=dict(height=5.0, size=(3.2, 2.1)),
    ),
}


class Hull:
    """Hull shape functions for one spec: station s runs from 0 (stern) to 1 (bow)."""

    def __init__(self, spec):
        self.spec = spec
        self.length = spec["length"]
        self.b = spec["beam"] / 2

    def z(self, s):
        return self.length / 2 - s * self.length

    def half_beam(self, s):
        if s <= 0.45:
            return self.b * (1.0 - 0.25 * ((0.45 - s) / 0.45) ** 2)
        t = (s - 0.45) / 0.55
        return self.b * (max(1.0 - t ** 2.2, 0.0) * 0.97 + 0.03)

    def draft(self, s):
        return self.spec["draft"] * (1.0 - 0.12 * s) * (1.0 - 0.75 * mk.smoothstep(0.82, 1.0, s) ** 1.5)

    def sheer(self, s):
        f = self.spec["freeboard"]
        if s < 0.5:
            return f + self.spec["sheer_aft"] * ((0.5 - s) / 0.5) ** 2
        return f + self.spec["sheer_fwd"] * ((s - 0.5) / 0.5) ** 2

    def section(self, s):
        """Half section (x >= 0) from keel to rail as [(x, y)]."""
        d, f, bw, hb = self.draft(s), self.sheer(s), self.spec["bulwark"], self.half_beam(s)
        return [(factor * hb, fn(d, f, bw)) for fn, factor in LEVELS]

    def x_at(self, s, y):
        sec = self.section(s)
        for (x0, y0), (x1, y1) in zip(sec, sec[1:]):
            if y0 <= y <= y1:
                t = (y - y0) / max(y1 - y0, 1e-6)
                return x0 + (x1 - x0) * t
        return sec[-1][0]


def stations():
    return [i / (STATIONS - 1) for i in range(STATIONS)]


def hull_color(p, n):
    return (0.68 + 0.32 * mk.smoothstep(-0.6, 1.4, p[1]), 0.0, 0.0, 1.0)


def build_hull(spec, hull):
    mb = mk.MeshBuilder("Hull", 2.0)
    mb.color_fn = hull_color
    ss = stations()
    secs = [hull.section(s) for s in ss]
    girths = []
    for sec in secs:
        g = [0.0]
        for (x0, y0), (x1, y1) in zip(sec, sec[1:]):
            g.append(g[-1] + math.hypot(x1 - x0, y1 - y0))
        girths.append(g)
    for side in (1, -1):
        for i in range(len(ss) - 1):
            z0, z1 = hull.z(ss[i]), hull.z(ss[i + 1])
            for lv in range(len(LEVELS) - 1):
                a = (side * secs[i][lv][0], secs[i][lv][1], z0)
                b = (side * secs[i + 1][lv][0], secs[i + 1][lv][1], z1)
                c = (side * secs[i + 1][lv + 1][0], secs[i + 1][lv + 1][1], z1)
                d = (side * secs[i][lv + 1][0], secs[i][lv + 1][1], z0)
                uvs = [(girths[i][lv] / 2.0, z0 / 4.0), (girths[i + 1][lv] / 2.0, z1 / 4.0),
                       (girths[i + 1][lv + 1] / 2.0, z1 / 4.0), (girths[i][lv + 1] / 2.0, z0 / 4.0)]
                mb.quad_facing(a, b, c, d, (side, -0.3 if lv < 3 else 0.0, 0.0), BANDS[lv], uvs, smooth=True)
            # Keel strip between the two sides is added once (side == 1).
            if side == 1:
                a = (secs[i][0][0], secs[i][0][1], z0)
                b = (secs[i + 1][0][0], secs[i + 1][0][1], z1)
                mb.quad_facing(a, b, (-b[0], b[1], z1), (-a[0], a[1], z0), (0.0, -1.0, 0.0), "hull_dark")
    build_deck_and_bulwarks(mb, spec, hull, ss)
    build_castles(mb, spec, hull, ss)
    build_ends(mb, spec, hull)
    build_gunports(mb, spec, hull)
    if spec["beakhead"]:
        build_beakhead(mb, hull)
    build_ensign(mb, spec, hull)
    return mb.build()


def build_deck_and_bulwarks(mb, spec, hull, ss):
    bw = spec["bulwark"]
    for i in range(len(ss) - 1):
        s0, s1 = ss[i], ss[i + 1]
        z0, z1 = hull.z(s0), hull.z(s1)
        x0 = max(LEVELS[DECK_LEVEL][1] * hull.half_beam(s0) - BULWARK_THICKNESS, 0.02)
        x1 = max(LEVELS[DECK_LEVEL][1] * hull.half_beam(s1) - BULWARK_THICKNESS, 0.02)
        y0, y1 = hull.sheer(s0), hull.sheer(s1)
        mb.quad_facing((x0, y0, z0), (x1, y1, z1), (-x1, y1, z1), (-x0, y0, z0), (0.0, 1.0, 0.0), "deck",
                       [(x0 / 3, z0 / 3), (x1 / 3, z1 / 3), (-x1 / 3, z1 / 3), (-x0 / 3, z0 / 3)])
        r0 = max(LEVELS[RAIL_LEVEL][1] * hull.half_beam(s0) - BULWARK_THICKNESS, 0.02)
        r1 = max(LEVELS[RAIL_LEVEL][1] * hull.half_beam(s1) - BULWARK_THICKNESS, 0.02)
        o0 = LEVELS[RAIL_LEVEL][1] * hull.half_beam(s0)
        o1 = LEVELS[RAIL_LEVEL][1] * hull.half_beam(s1)
        for side in (1, -1):
            mb.quad_facing((side * x0, y0, z0), (side * x1, y1, z1), (side * r1, y1 + bw, z1), (side * r0, y0 + bw, z0),
                           (-side, 0.0, 0.0), "hull")
            mb.quad_facing((side * r0, y0 + bw, z0), (side * r1, y1 + bw, z1), (side * o1, y1 + bw, z1),
                           (side * o0, y0 + bw, z0), (0.0, 1.0, 0.0), "hull_dark")


def tier_ranges(spec):
    """(s0, s1, base_height, height) for every castle tier, stern then fore."""
    out = []
    h = 0.0
    for s_end, height in spec["stern_tiers"]:
        out.append((0.0, s_end, h, h + height, "stern"))
        h += height
    h = 0.0
    for s_start, height in spec["fore_tiers"]:
        out.append((s_start, 1.0, h, h + height, "fore"))
        h += height
    return out


def tier_x(hull, s, level):
    return (LEVELS[RAIL_LEVEL][1] - 0.03 * level) * hull.half_beam(s)


def build_castles(mb, spec, hull, ss):
    bw = spec["bulwark"]
    level = {"stern": 0, "fore": 0}
    for s0, s1, base, top, end in tier_ranges(spec):
        level[end] += 1
        k = level[end]
        pts = [s0] + [s for s in ss if s0 < s < s1] + [s1]
        for i in range(len(pts) - 1):
            sa, sb = pts[i], pts[i + 1]
            za, zb = hull.z(sa), hull.z(sb)
            fa, fb = hull.sheer(sa), hull.sheer(sb)
            xa_lo, xb_lo = tier_x(hull, sa, k - 1), tier_x(hull, sb, k - 1)
            xa, xb = tier_x(hull, sa, k), tier_x(hull, sb, k)
            for side in (1, -1):
                mb.quad_facing((side * xa_lo, fa + base + bw, za), (side * xb_lo, fb + base + bw, zb),
                               (side * xb, fb + top + bw, zb), (side * xa, fa + top + bw, za),
                               (side, 0.0, 0.0), "hull_paint")
                ia, ib = xa - BULWARK_THICKNESS, xb - BULWARK_THICKNESS
                mb.quad_facing((side * ia, fa + top, za), (side * ib, fb + top, zb), (side * ib, fb + top + bw, zb),
                               (side * ia, fa + top + bw, za), (-side, 0.0, 0.0), "hull")
                mb.quad_facing((side * ia, fa + top + bw, za), (side * ib, fb + top + bw, zb),
                               (side * xb, fb + top + bw, zb), (side * xa, fa + top + bw, za), (0.0, 1.0, 0.0), "hull_dark")
            ia, ib = xa - BULWARK_THICKNESS, xb - BULWARK_THICKNESS
            mb.quad_facing((ia, fa + top, za), (ib, fb + top, zb), (-ib, fb + top, zb), (-ia, fa + top, za),
                           (0.0, 1.0, 0.0), "deck", [(ia / 3, za / 3), (ib / 3, zb / 3), (-ib / 3, zb / 3), (-ia / 3, za / 3)])
        # The open end of the tier (its "break"): a wall across the ship with a door.
        s_break = s1 if end == "stern" else s0
        facing = -1.0 if end == "stern" else 1.0
        zb = hull.z(s_break)
        fb = hull.sheer(s_break)
        xb = tier_x(hull, s_break, k) - BULWARK_THICKNESS
        y_lo, y_hi = fb + base, fb + top + 0.9
        mb.quad_facing((xb, y_lo, zb), (-xb, y_lo, zb), (-xb, y_hi, zb), (xb, y_hi, zb), (0.0, 0.0, facing), "hull_paint")
        door_h = min(top - base - 0.2, 1.9)
        if door_h > 0.8:
            dz = zb + facing * 0.02
            mb.quad_facing((0.45, y_lo, dz), (-0.45, y_lo, dz), (-0.45, y_lo + door_h, dz), (0.45, y_lo + door_h, dz),
                           (0.0, 0.0, facing), "opening")


def build_ends(mb, spec, hull):
    """Transom at the stern (with windows and lanterns) and the bow cap, each closing the hull
    and the castle tiers at that end."""
    bw = spec["bulwark"]
    for end, s, facing in (("stern", 0.0, 1.0), ("fore", 1.0, -1.0)):
        sec = hull.section(s)
        f = hull.sheer(s)
        tiers = [t for t in tier_ranges(spec) if t[4] == end]
        right = [(x, y) for x, y in sec]
        for k, (_, _, base, top, _) in enumerate(tiers, start=1):
            right.append((tier_x(hull, s, k), f + top + bw))
        outline = right + [(-x, y) for x, y in reversed(right)]
        z = hull.z(s)
        for tri in mk.triangulate(outline):
            pts = [(x, y, z) for x, y in tri]
            if mk.face_normal(pts).z * facing < 0:
                pts.reverse()
            mb.face(pts, "hull_paint")
        if end == "stern" and tiers:
            # Stern gallery windows in each tier, and lanterns on the taffrail.
            for k, (_, _, base, top, _) in enumerate(tiers, start=1):
                width = tier_x(hull, s, k) * 1.6
                n = spec["windows"]
                for w in range(n):
                    cx = -width / 2 + width * (w + 0.5) / n
                    y0, y1 = f + base + bw * 0.6 + 0.3, f + top + bw * 0.4
                    if y1 - y0 < 0.4:
                        continue
                    hw = min(width / n * 0.32, 0.45)
                    zz = z + 0.02
                    mb.quad_facing((cx - hw, y0, zz), (cx + hw, y0, zz), (cx + hw, y1, zz), (cx - hw, y1, zz),
                                   (0.0, 0.0, 1.0), "opening")
            top_y = f + tiers[-1][3] + bw
            span = tier_x(hull, s, len(tiers)) * 0.7
            for i in range(spec["lanterns"]):
                x = 0.0 if spec["lanterns"] == 1 else -span + 2 * span * i / (spec["lanterns"] - 1)
                mk.tube(mb, (x, top_y, z - 0.3), (x, top_y + 0.9, z - 0.3), 0.22, 0.15, "gold", 8)
                mk.dome(mb, (x, z - 0.3), 0.15, top_y + 0.9, "gold", segments=8, rings=3)


def build_gunports(mb, spec, hull):
    p = spec["port_size"]
    index = {1: 0, -1: 0}
    for y_frac, count, s_from, s_to in spec["gunports"]:
        for i in range(count):
            s = s_from + (s_to - s_from) * (i + 0.5) / count
            y = y_frac * hull.sheer(s)
            z = hull.z(s)
            x = hull.x_at(s, y) + 0.02
            for side in (1, -1):
                xs = side * x
                mb.quad_facing((xs, y - p / 2, z + p / 2), (xs, y - p / 2, z - p / 2), (xs, y + p / 2, z - p / 2),
                               (xs, y + p / 2, z + p / 2), (side, 0.0, 0.0), "opening")
                # Port lid, propped open above the port.
                lid = [(xs, y + p / 2, z + p / 2), (xs, y + p / 2, z - p / 2),
                       (xs + side * p * 0.55, y + p / 2 + p * 0.55, z - p / 2),
                       (xs + side * p * 0.55, y + p / 2 + p * 0.55, z + p / 2)]
                mb.quad_facing(*lid, (side, -1.0, 0.0), "hull_paint")
                mb.quad_facing(*reversed(lid), (-side, 1.0, 0.0), "hull_paint")
                if spec["guns"]:
                    muzzle = (xs + side * 0.75, y, z)
                    mk.tube(mb, (xs - side * 0.3, y, z), muzzle, 0.13, 0.1, "iron", 8)
                    tag = "S" if side > 0 else "P"
                    mk.empty(f"Port_{tag}_{index[side]:02d}", muzzle, facing=(side, 0.0))
                    index[side] += 1


def build_beakhead(mb, hull):
    """The galleon's beakhead: a tapering platform projecting under the bowsprit."""
    z = hull.z(1.0)
    f = hull.sheer(1.0)
    mk.tube(mb, (0.0, f - 1.0, z + 0.6), (0.0, f - 1.1, z - 4.2), 0.85, 0.22, "hull_paint", 4)
    mk.box(mb, (0.0, f - 0.36, z - 1.6), (1.1, 0.08, 3.4), "deck")
    mk.box(mb, (0.0, f - 1.05, z - 4.3), (0.35, 0.75, 0.5), "gold")


def build_ensign(mb, spec, hull):
    tiers = [t for t in tier_ranges(spec) if t[4] == "stern"]
    f = hull.sheer(0.0)
    top = f + (tiers[-1][3] if tiers else 0.0) + spec["bulwark"]
    z = hull.z(0.0) - 0.4
    e = spec["ensign"]
    mk.tube(mb, (0.0, top - 0.5, z), (0.0, top + e["height"], z), 0.09, 0.06, "spar", 6)
    w, h = e["size"]
    y_top = top + e["height"] - 0.1
    mk.grid_surface(mb, lambda u, v: (0.0, y_top - v * h, z + 0.05 + u * w), 6, 3, "flag")


# --- Masts ------------------------------------------------------------------------------

def build_mast(spec, hull, m, stays_to):
    s = m["s"]
    foot = (0.0, hull.sheer(s), hull.z(s))
    h = m["height"]
    mb = mk.MeshBuilder(f"Mast_{m['name']}", 2.0)
    mb.color_fn = lambda p, n: (1.0, 0.0, 0.0, 1.0)
    r = 0.016 * h + 0.05
    mk.tube(mb, (0, -1.0, 0), (0, 0.52 * h, 0), r, r * 0.75, "spar", 10)
    mk.tube(mb, (0, 0.44 * h, 0), (0, 0.86 * h, 0), r * 0.55, r * 0.38, "spar", 8)
    mk.tube(mb, (0, 0.84 * h, 0), (0, h, 0), r * 0.3, r * 0.18, "spar", 6)
    top_r = 0.06 * h
    mk.cylinder(mb, (0.0, 0.0), top_r, 0.48 * h - 0.14, 0.48 * h + 0.14, "spar", segments=12)
    if m.get("lateen"):
        build_lateen(mb, h)
    else:
        for top_f, bottom_f, w_top, w_bot in m["sails"]:
            build_square_sail(mb, h, top_f, bottom_f, w_top, w_bot)
    # Shrouds to the chainwales, topmast shrouds to the top.
    hb = hull.half_beam(s)
    for side in (1, -1):
        for dz in (-0.9, -0.3, 0.3, 0.9):
            spread = hb / 5.0
            mk.tube(mb, (side * top_r * 0.8, 0.47 * h, dz * spread * 0.4),
                    (side * (hb * 0.95), 0.4, dz * spread + 0.7), 0.035, 0.035, "rope", 4, caps=False)
        for dz in (-0.25, 0.25):
            mk.tube(mb, (side * 0.15, 0.83 * h, 0.0), (side * top_r * 0.95, 0.49 * h, dz), 0.025, 0.025, "rope", 4, caps=False)
    # Stays forward to the next mast or the bowsprit (points given in ship space).
    if stays_to is not None:
        target = (stays_to[0] - foot[0], stays_to[1] - foot[1], stays_to[2] - foot[2])
        mk.tube(mb, (0.0, 0.47 * h, -0.3), target, 0.045, 0.045, "rope", 4, caps=False)
    # Pennant at the masthead, streaming aft.
    mk.grid_surface(mb, lambda u, v: (0.0, h - 0.1 - v * 0.55 * (1.0 - u * 0.9), 0.1 + u * 0.28 * h), 8, 1, "flag")
    obj = mb.build()
    obj.location = mk.to_blender(foot)
    return obj


def build_square_sail(mb, h, top_f, bottom_f, w_top, w_bot):
    y_t, y_b = top_f * h, bottom_f * h
    z_yard = -0.45
    mk.tube(mb, (-w_top * 1.08, y_t, z_yard), (0.0, y_t, z_yard), 0.06, 0.12 + 0.004 * h, "spar", 6)
    mk.tube(mb, (0.0, y_t, z_yard), (w_top * 1.08, y_t, z_yard), 0.12 + 0.004 * h, 0.06, "spar", 6)
    belly = 0.14 * w_bot

    def point(u, v):
        x = (-w_top + 2 * w_top * u) * (1 - v) + (-w_bot + 2 * w_bot * u) * v
        y = y_t - 0.15 + (y_b - y_t + 0.15) * v
        d = belly * math.sin(math.pi * u) * math.sin(math.pi * (0.1 + 0.8 * v))
        return (x, y, z_yard - 0.12 - d)

    mk.grid_surface(mb, point, 6, 6, "sail", uv_size=(2 * w_bot / 1.5, (y_t - y_b) / 1.5))


def build_lateen(mb, h):
    ly = 1.1 * h
    ang = math.radians(50)
    cross = 0.55 * h
    p1 = (0.0, cross - 0.42 * ly * math.sin(ang), -0.42 * ly * math.cos(ang))
    p2 = (0.0, cross + 0.58 * ly * math.sin(ang), 0.58 * ly * math.cos(ang))
    p3 = (0.0, 0.16 * h, p2[2] * 0.85)
    yard_off = 0.35
    mk.tube(mb, (yard_off, p1[1], p1[2]), (yard_off, p2[1], p2[2]), 0.13, 0.07, "spar", 6)
    belly = 0.08 * ly

    def point(u, v):
        w1, w2, w3 = (1 - u) * (1 - v), u, v * (1 - u)
        x = yard_off + 0.15 + belly * math.sin(math.pi * u) * math.sin(math.pi * min(v + 0.1, 1.0)) * (1 - u * 0.3)
        y = p1[1] * w1 + p2[1] * w2 + p3[1] * w3
        z = p1[2] * w1 + p2[2] * w2 + p3[2] * w3
        return (x, y, z)

    mk.grid_surface(mb, point, 7, 5, "sail", uv_size=(ly / 1.5, 0.6 * h / 1.5))


def build_bowsprit(spec, hull):
    bs = spec["bowsprit"]
    foot = (0.0, hull.sheer(0.97) + 0.3, hull.z(0.97) + 1.0)
    ang = math.radians(bs["angle"])
    length = bs["length"]
    tip = (0.0, length * math.sin(ang), -length * math.cos(ang))
    mb = mk.MeshBuilder("Mast_Bowsprit", 2.0)
    mb.color_fn = lambda p, n: (1.0, 0.0, 0.0, 1.0)
    mk.tube(mb, (0.0, -0.4, 1.0), tip, 0.32 * length / 13 + 0.1, 0.1, "spar", 8)
    if bs["spritsail"]:
        at = 0.6
        yard = (0.0, tip[1] * at - 0.35, tip[2] * at)
        w = 0.28 * length
        mk.tube(mb, (-w * 1.05, yard[1], yard[2]), (w * 1.05, yard[1], yard[2]), 0.07, 0.07, "spar", 6)
        drop = 0.3 * length
        belly = 0.12 * w

        def point(u, v):
            x = -w + 2 * w * u
            d = belly * math.sin(math.pi * u) * math.sin(math.pi * (0.1 + 0.8 * v))
            return (x, yard[1] - 0.1 - drop * v, yard[2] - 0.1 - d)

        mk.grid_surface(mb, point, 5, 4, "sail", uv_size=(2 * w / 1.5, drop / 1.5))
    obj = mb.build()
    obj.location = mk.to_blender(foot)
    world_tip = (foot[0] + tip[0], foot[1] + tip[1], foot[2] + tip[2])
    return obj, world_tip


def build_ship(name, spec):
    mk.reset_scene()
    for mat, color, metal, rough in [
        ("hull", (0.45, 0.32, 0.2), 0.0, 0.8), ("hull_dark", (0.16, 0.12, 0.1), 0.0, 0.8),
        ("hull_paint", (0.55, 0.2, 0.12), 0.0, 0.7), ("deck", (0.6, 0.5, 0.36), 0.0, 0.8),
        ("opening", (0.04, 0.03, 0.03), 0.0, 1.0), ("iron", (0.12, 0.12, 0.12), 0.7, 0.6),
        ("spar", (0.35, 0.25, 0.16), 0.0, 0.8), ("sail", (0.86, 0.82, 0.7), 0.0, 0.9),
        ("rope", (0.18, 0.14, 0.1), 0.0, 0.9), ("flag", (0.9, 0.9, 0.9), 0.0, 0.9),
        ("gold", (0.75, 0.55, 0.2), 0.8, 0.4),
    ]:
        mk.material(mat, color, metal, rough)
    hull = Hull(spec)
    build_hull(spec, hull)
    bowsprit_obj, bowsprit_tip = build_bowsprit(spec, hull)
    masts = sorted(spec["masts"], key=lambda m: -m["s"])  # bow first
    previous_foot = None
    for m in masts:
        if previous_foot is None:
            target = (bowsprit_tip[0], bowsprit_tip[1] - 0.5, bowsprit_tip[2] + 1.5)
        else:
            target = previous_foot
        build_mast(spec, hull, m, target)
        previous_foot = (0.0, hull.sheer(m["s"]) + 0.6, hull.z(m["s"]))
    tris = sum(len(p.vertices) - 2 for o in bpy.data.objects if o.type == "MESH" for p in o.data.polygons)
    print(f"[ship] {name}: ~{tris} triangles, {len([o for o in bpy.data.objects if o.name.startswith('Port_')])} gun ports")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--blend-dir", default="")
    parser.add_argument("--preview-dir", default="")
    parser.add_argument("--only", default="")
    args = parser.parse_args(mk.script_args())
    for name, spec in SPECS.items():
        if args.only and name != args.only:
            continue
        build_ship(name, spec)
        mk.export_glb(os.path.abspath(os.path.join(args.out_dir, f"{name}.glb")))
        if args.blend_dir:
            mk.save_blend(os.path.abspath(os.path.join(args.blend_dir, f"{name}.blend")))
        if args.preview_dir:
            L = spec["length"]
            mk.render_views(os.path.abspath(os.path.join(args.preview_dir, name)), [
                ("broadside", (L * 1.5, L * 0.35, -L * 0.1), (0.0, L * 0.25, 0.0), None),
                ("bow_quarter", (L * 0.9, L * 0.45, -L * 1.1), (0.0, L * 0.2, 0.0), None),
                ("stern_quarter", (-L * 0.9, L * 0.4, L * 1.0), (0.0, L * 0.2, 0.0), None),
            ])
    return 0


if __name__ == "__main__":
    main()

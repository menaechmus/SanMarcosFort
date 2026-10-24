"""Mesh-building helpers for the asset generators (run inside Blender, headless).

All geometry is written in *game* coordinates (Godot): +X east, +Y up, +Z south, metres.
MeshBuilder converts to Blender's Z-up axes when it creates the mesh; the glTF exporter
converts back, so the .glb lands in Godot exactly as written here.

Faces are wound counter-clockwise seen from the side they face (right-hand rule).
Vertex colour channels, read by the game's shaders:
    R  ambient occlusion / grime (1 = clean)
    G  plaster remnant mask (today's look shows old plaster where this is high)
    B  free
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Vector


# --- Scene -------------------------------------------------------------------------------

def reset_scene() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)


def script_args() -> list:
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def to_blender(p) -> Vector:
    """Game (x east, y up, z south) -> Blender (x, y north, z up)."""
    return Vector((p[0], -p[2], p[1]))


def material(name: str, color, metallic: float = 0.0, roughness: float = 0.8):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.diffuse_color = (color[0], color[1], color[2], 1.0)
    mat.metallic = metallic
    mat.roughness = roughness
    return mat


# --- 2D polygon helpers (x, z) -----------------------------------------------------------

def signed_area(poly) -> float:
    a = 0.0
    for i in range(len(poly)):
        x1, z1 = poly[i]
        x2, z2 = poly[(i + 1) % len(poly)]
        a += x1 * z2 - x2 * z1
    return a * 0.5


def outward_normals(poly):
    """Outward unit normal of each edge i (poly[i] -> poly[i+1])."""
    sign = 1.0 if signed_area(poly) > 0 else -1.0
    normals = []
    for i in range(len(poly)):
        x1, z1 = poly[i]
        x2, z2 = poly[(i + 1) % len(poly)]
        dx, dz = x2 - x1, z2 - z1
        length = math.hypot(dx, dz) or 1.0
        normals.append((sign * dz / length, -sign * dx / length))
    return normals


def offset_polygon(poly, d: float):
    """Moves every edge outward by d (inward when negative) with mitred corners."""
    normals = outward_normals(poly)
    out = []
    n = len(poly)
    for i in range(n):
        n1 = normals[i - 1]
        n2 = normals[i]
        mx, mz = n1[0] + n2[0], n1[1] + n2[1]
        denom = 1.0 + n1[0] * n2[0] + n1[1] * n2[1]
        if denom < 1e-4:
            mx, mz, denom = n2[0], n2[1], 1.0
        out.append((poly[i][0] + d * mx / denom, poly[i][1] + d * mz / denom))
    return out


def line_intersection(p1, d1, p2, d2):
    """Intersection of lines p1 + t*d1 and p2 + s*d2 (2D), or None when parallel."""
    cross = d1[0] * d2[1] - d1[1] * d2[0]
    if abs(cross) < 1e-9:
        return None
    t = ((p2[0] - p1[0]) * d2[1] - (p2[1] - p1[1]) * d2[0]) / cross
    return (p1[0] + d1[0] * t, p1[1] + d1[1] * t)


def circle_intersection(c1, r1, c2, r2, away_from):
    """The intersection of two circles farther from `away_from`."""
    dx, dz = c2[0] - c1[0], c2[1] - c1[1]
    d = math.hypot(dx, dz)
    a = (r1 * r1 - r2 * r2 + d * d) / (2 * d)
    h = math.sqrt(max(r1 * r1 - a * a, 0.0))
    mx, mz = c1[0] + a * dx / d, c1[1] + a * dz / d
    p1 = (mx + h * dz / d, mz - h * dx / d)
    p2 = (mx - h * dz / d, mz + h * dx / d)
    dist = lambda p: math.hypot(p[0] - away_from[0], p[1] - away_from[1])
    return p1 if dist(p1) > dist(p2) else p2


def perimeter_positions(poly, closed: bool = True):
    """Cumulative length along the polygon at each vertex (plus the closing length)."""
    out = [0.0]
    count = len(poly) if closed else len(poly) - 1
    for i in range(count):
        a, b = poly[i], poly[(i + 1) % len(poly)]
        out.append(out[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    return out


# --- Procedural masks --------------------------------------------------------------------

def _hash(ix: int, iy: int, iz: int) -> float:
    h = (ix * 374761393 + iy * 668265263 + iz * 2147483647) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFF) / 65535.0


def value_noise(x: float, y: float, z: float) -> float:
    ix, iy, iz = math.floor(x), math.floor(y), math.floor(z)
    fx, fy, fz = x - ix, y - iy, z - iz
    sx, sy, sz = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy), fz * fz * (3 - 2 * fz)
    total = 0.0
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                w = (sx if dx else 1 - sx) * (sy if dy else 1 - sy) * (sz if dz else 1 - sz)
                total += w * _hash(ix + dx, iy + dy, iz + dz)
    return total


def fbm(x: float, y: float, z: float, octaves: int = 3) -> float:
    total, amp, freq, norm = 0.0, 1.0, 1.0, 0.0
    for _ in range(octaves):
        total += amp * value_noise(x * freq, y * freq, z * freq)
        norm += amp
        amp *= 0.5
        freq *= 2.0
    return total / norm


def smoothstep(e0: float, e1: float, x: float) -> float:
    t = min(max((x - e0) / (e1 - e0), 0.0), 1.0)
    return t * t * (3 - 2 * t)


# --- Mesh building -----------------------------------------------------------------------

class MeshBuilder:
    """Collects faces in game space, then creates one Blender mesh object."""

    def __init__(self, name: str, uv_scale: float = 3.0):
        self.name = name
        self.uv_scale = uv_scale
        self.verts = []
        self.faces = []
        self.face_mats = []
        self.face_uvs = []
        self.face_cols = []
        self.face_smooth = []
        self.materials = []
        # Function (position, normal) -> RGBA used when a face gives no colours.
        self.color_fn = lambda p, n: (1.0, 0.0, 0.0, 1.0)

    def vert(self, p) -> int:
        self.verts.append((float(p[0]), float(p[1]), float(p[2])))
        return len(self.verts) - 1

    def face(self, points, mat: str, uvs=None, smooth: bool = False, cols=None) -> None:
        """Adds a polygon from game-space points (CCW seen from the front)."""
        idx = [self.vert(p) for p in points]
        if mat not in self.materials:
            self.materials.append(mat)
        self.faces.append(idx)
        self.face_mats.append(self.materials.index(mat))
        self.face_uvs.append(uvs)
        self.face_cols.append(cols)
        self.face_smooth.append(smooth)

    def quad_facing(self, a, b, c, d, facing, mat: str, uvs=None, smooth: bool = False) -> None:
        """Quad a-b-c-d, flipped if needed so its normal points along `facing`."""
        n = face_normal([a, b, c])
        if n.dot(Vector(facing)) < 0:
            a, b, c, d = d, c, b, a
            if uvs:
                uvs = [uvs[3], uvs[2], uvs[1], uvs[0]]
        self.face([a, b, c, d], mat, uvs, smooth)

    def build(self, collection=None):
        mesh = bpy.data.meshes.new(self.name)
        mesh.from_pydata([to_blender(v) for v in self.verts], [], self.faces)
        for mat_name in self.materials:
            mesh.materials.append(bpy.data.materials.get(mat_name) or material(mat_name, (0.7, 0.7, 0.7)))
        mesh.polygons.foreach_set("material_index", self.face_mats)
        mesh.polygons.foreach_set("use_smooth", self.face_smooth)
        uv_layer = mesh.uv_layers.new(name="UVMap")
        colors = mesh.color_attributes.new(name="Col", type="FLOAT_COLOR", domain="CORNER")
        for poly in mesh.polygons:
            fi = poly.index
            pts = [Vector(self.verts[i]) for i in self.faces[fi]]
            normal = face_normal(pts)
            uvs = self.face_uvs[fi] or box_uvs(pts, normal, self.uv_scale)
            cols = self.face_cols[fi]
            for corner, loop_index in enumerate(poly.loop_indices):
                uv_layer.data[loop_index].uv = uvs[corner]
                c = cols[corner] if cols else self.color_fn(pts[corner], normal)
                colors.data[loop_index].color = c
        mesh.color_attributes.active_color = colors
        # Weld coincident vertices: closed solids for booleans, shared normals for smooth parts.
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0005)
        bm.to_mesh(mesh)
        bm.free()
        mesh.validate()
        mesh.update()
        obj = bpy.data.objects.new(self.name, mesh)
        (collection or bpy.context.scene.collection).objects.link(obj)
        return obj


def face_normal(points) -> Vector:
    pts = [Vector(p) for p in points]
    n = Vector((0.0, 0.0, 0.0))
    for i in range(len(pts)):
        a, b = pts[i], pts[(i + 1) % len(pts)]
        n.x += (a.y - b.y) * (a.z + b.z)
        n.y += (a.z - b.z) * (a.x + b.x)
        n.z += (a.x - b.x) * (a.y + b.y)
    return n.normalized() if n.length > 1e-9 else Vector((0.0, 1.0, 0.0))


def box_uvs(points, normal, scale: float):
    """World-space box projection; walls keep v = height so stone courses stay level."""
    ax, ay, az = abs(normal.x), abs(normal.y), abs(normal.z)
    if ay >= ax and ay >= az:
        return [(p[0] / scale, -p[2] / scale) for p in points]
    if ax >= az:
        return [(p[2] / scale, p[1] / scale) for p in points]
    return [(p[0] / scale, p[1] / scale) for p in points]


# --- Shapes ------------------------------------------------------------------------------

def segment_counts(ring, cell: float):
    """Per-edge subdivision counts for a closed ring; pass the same list to every ring_wall
    that shares edges with it, so the strips meet without T-junctions."""
    return [max(1, math.ceil(math.hypot(ring[(i + 1) % len(ring)][0] - ring[i][0],
                                        ring[(i + 1) % len(ring)][1] - ring[i][1]) / cell))
            for i in range(len(ring))]


def ring_wall(mb: MeshBuilder, bottom, y_bottom, top, y_top, mat: str, outward: bool = True,
              u_offset: float = 0.0, cell: float = 0.0, closed: bool = True, vertical: int = 0,
              segments=None) -> None:
    """Wall between two rings of equal vertex count. UVs wrap along the perimeter, so stone
    courses run continuously around corners. `cell` > 0 subdivides into roughly cell-sized
    quads (gives vertex-colour grime enough resolution); `segments` fixes the per-edge
    count instead (see segment_counts). For near-horizontal strips pass vertical=+1 (face
    up) or -1 (face down) instead of relying on `outward`."""
    s_bottom = perimeter_positions(bottom, closed)
    s_top = perimeter_positions(top, closed)
    normals = outward_normals(bottom) if closed else _open_normals(bottom)
    n = len(bottom)
    for i in range(n if closed else n - 1):
        j = (i + 1) % n
        facing = (normals[i][0], 0.0, normals[i][1]) if outward else (-normals[i][0], 0.0, -normals[i][1])
        if vertical:
            facing = (0.0, float(vertical), 0.0)
        elif abs(y_top - y_bottom) < 1e-6:
            facing = (0.0, 1.0 if outward else -1.0, 0.0)
        length = math.hypot(bottom[j][0] - bottom[i][0], bottom[j][1] - bottom[i][1])
        if segments:
            nu = segments[i]
        else:
            nu = max(1, math.ceil(length / cell)) if cell > 0 else 1
        nv = max(1, math.ceil(abs(y_top - y_bottom) / cell)) if cell > 0 else 1

        def point(fu, fv):
            bx = bottom[i][0] + (bottom[j][0] - bottom[i][0]) * fu
            bz = bottom[i][1] + (bottom[j][1] - bottom[i][1]) * fu
            tx = top[i][0] + (top[j][0] - top[i][0]) * fu
            tz = top[i][1] + (top[j][1] - top[i][1]) * fu
            y = y_bottom + (y_top - y_bottom) * fv
            p = (bx + (tx - bx) * fv, y, bz + (tz - bz) * fv)
            s0 = s_bottom[i] + (s_bottom[i + 1] - s_bottom[i]) * fu
            s1 = s_top[i] + (s_top[i + 1] - s_top[i]) * fu
            u = (u_offset + s0 + (s1 - s0) * fv) / mb.uv_scale
            return p, (u, y / mb.uv_scale)

        for iu in range(nu):
            for iv in range(nv):
                pa, ua = point(iu / nu, iv / nv)
                pb, ub = point((iu + 1) / nu, iv / nv)
                pc, uc = point((iu + 1) / nu, (iv + 1) / nv)
                pd, ud = point(iu / nu, (iv + 1) / nv)
                # Near-flat strips (wall tops) get top-down UVs instead of stretched ones.
                uvs = None if vertical else [ua, ub, uc, ud]
                mb.quad_facing(pa, pb, pc, pd, facing, mat, uvs)


def _open_normals(points):
    """Left-hand normals of an open polyline (callers pick the side with `outward`)."""
    out = []
    for i in range(len(points) - 1):
        dx = points[i + 1][0] - points[i][0]
        dz = points[i + 1][1] - points[i][1]
        length = math.hypot(dx, dz) or 1.0
        out.append((dz / length, -dx / length))
    return out


def cap(mb: MeshBuilder, outer, y: float, mat: str, holes=(), up: bool = True) -> None:
    """Flat horizontal polygon (concave allowed) with optional holes."""
    for tri in triangulate(outer, holes):
        pts = [(p[0], y, p[1]) for p in tri]
        n = face_normal(pts)
        if (n.y < 0) == up:
            pts.reverse()
        mb.face(pts, mat)


def triangulate(outer, holes=()):
    """Triangles (as 2D point triples) filling `outer` minus `holes`, via bmesh."""
    bm = bmesh.new()
    loops = [outer] + list(holes)
    edges = []
    for loop in loops:
        vs = [bm.verts.new((p[0], p[1], 0.0)) for p in loop]
        for i in range(len(vs)):
            edges.append(bm.edges.new((vs[i], vs[(i + 1) % len(vs)])))
    result = bmesh.ops.triangle_fill(bm, use_beauty=True, use_dissolve=False, edges=edges,
                                     normal=(0.0, 0.0, 1.0))
    tris = []
    for f in result["geom"]:
        if isinstance(f, bmesh.types.BMFace):
            tris.append([(v.co.x, v.co.y) for v in f.verts])
    bm.free()
    return tris


def prism(mb: MeshBuilder, poly, y0: float, y1: float, mat: str, cap_bottom: bool = False) -> None:
    """Vertical walls plus top (and optional bottom) of an extruded polygon."""
    ring_wall(mb, poly, y0, poly, y1, mat)
    cap(mb, poly, y1, mat)
    if cap_bottom:
        cap(mb, poly, y0, mat, up=False)


def solid(mb: MeshBuilder, bottom, top, mat: str) -> None:
    """Closed convex solid between two rings of game-space points (same count and order), e.g. a
    block with a sloping floor. Sides get UVs along the ring with v = height; both rings must be
    planar. Every face points away from the centre."""
    n = len(bottom)
    centre = sum((Vector(p) for p in list(bottom) + list(top)), Vector()) / (2 * n)
    s = 0.0
    for i in range(n):
        j = (i + 1) % n
        a, b, c, d = bottom[i], bottom[j], top[j], top[i]
        length = math.hypot(b[0] - a[0], b[2] - a[2])
        uvs = [(s / mb.uv_scale, a[1] / mb.uv_scale), ((s + length) / mb.uv_scale, b[1] / mb.uv_scale),
               ((s + length) / mb.uv_scale, c[1] / mb.uv_scale), (s / mb.uv_scale, d[1] / mb.uv_scale)]
        mid = (Vector(a) + Vector(b) + Vector(c) + Vector(d)) / 4
        mb.quad_facing(a, b, c, d, mid - centre, mat, uvs)
        s += length
    for ring in (bottom, top):
        pts = list(ring)
        mid = sum((Vector(p) for p in pts), Vector()) / n
        if face_normal(pts).dot(mid - centre) < 0:
            pts.reverse()
        mb.face(pts, mat)


def cylinder(mb: MeshBuilder, center, radius: float, y0: float, y1: float, mat: str,
             segments: int = 16, top: bool = True, radius_top: float = None) -> None:
    rt = radius if radius_top is None else radius_top
    cx, cz = center
    ring0 = [(cx + radius * math.cos(a), cz + radius * math.sin(a))
             for a in (2 * math.pi * i / segments for i in range(segments))]
    ring1 = [(cx + rt * math.cos(a), cz + rt * math.sin(a))
             for a in (2 * math.pi * i / segments for i in range(segments))]
    for i in range(segments):
        j = (i + 1) % segments
        a = (ring0[i][0], y0, ring0[i][1])
        b = (ring0[j][0], y0, ring0[j][1])
        c = (ring1[j][0], y1, ring1[j][1])
        d = (ring1[i][0], y1, ring1[i][1])
        mid = ((ring0[i][0] + ring0[j][0]) / 2 - cx, 0.0, (ring0[i][1] + ring0[j][1]) / 2 - cz)
        u0, u1 = i / segments * 2 * math.pi * radius, (i + 1) / segments * 2 * math.pi * radius
        uvs = [(u0 / mb.uv_scale, y0 / mb.uv_scale), (u1 / mb.uv_scale, y0 / mb.uv_scale),
               (u1 / mb.uv_scale, y1 / mb.uv_scale), (u0 / mb.uv_scale, y1 / mb.uv_scale)]
        mb.quad_facing(a, b, c, d, mid, mat, uvs, smooth=True)
    if top:
        cap(mb, ring1, y1, mat)


def dome(mb: MeshBuilder, center, radius: float, y0: float, mat: str, segments: int = 16,
         rings: int = 6) -> None:
    cx, cz = center
    for r in range(rings):
        a0 = (math.pi / 2) * r / rings
        a1 = (math.pi / 2) * (r + 1) / rings
        for i in range(segments):
            t0 = 2 * math.pi * i / segments
            t1 = 2 * math.pi * (i + 1) / segments
            def pt(a, t):
                return (cx + radius * math.cos(a) * math.cos(t), y0 + radius * math.sin(a),
                        cz + radius * math.cos(a) * math.sin(t))
            p = [pt(a0, t0), pt(a0, t1), pt(a1, t1), pt(a1, t0)]
            facing = (math.cos(t0) + math.cos(t1), 0.6, math.sin(t0) + math.sin(t1))
            if r == rings - 1:
                tri = [p[0], p[1], p[2]]
                if face_normal(tri).y < 0:
                    tri.reverse()
                mb.face(tri, mat, smooth=True)
            else:
                mb.quad_facing(p[0], p[1], p[2], p[3], facing, mat, smooth=True)


def box(mb: MeshBuilder, center, size, mat: str, yaw: float = 0.0) -> None:
    """Axis-aligned (then yawed about Y) box, all six faces."""
    cx, cy, cz = center
    hx, hy, hz = size[0] / 2, size[1] / 2, size[2] / 2
    cs, sn = math.cos(yaw), math.sin(yaw)

    def p(x, y, z):
        return (cx + x * cs + z * sn, cy + y, cz - x * sn + z * cs)

    corners = [p(-hx, -hy, -hz), p(hx, -hy, -hz), p(hx, -hy, hz), p(-hx, -hy, hz),
               p(-hx, hy, -hz), p(hx, hy, -hz), p(hx, hy, hz), p(-hx, hy, hz)]
    quads = [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
    centre = Vector((cx, cy, cz))
    for q in quads:
        pts = [corners[i] for i in q]
        mid = sum((Vector(x) for x in pts), Vector()) / 4
        mb.quad_facing(pts[0], pts[1], pts[2], pts[3], mid - centre, mat)


def tube(mb: MeshBuilder, p0, p1, r0: float, r1: float, mat: str, segments: int = 8,
         caps: bool = True, smooth: bool = True) -> None:
    """Tapered cylinder between two game-space points (masts, yards, ropes, gun barrels)."""
    a, b = Vector(p0), Vector(p1)
    axis = b - a
    if axis.length < 1e-6:
        return
    axis.normalize()
    helper = Vector((0.0, 1.0, 0.0)) if abs(axis.y) < 0.9 else Vector((1.0, 0.0, 0.0))
    u = axis.cross(helper).normalized()
    v = axis.cross(u).normalized()
    ring0, ring1 = [], []
    for k in range(segments):
        ang = 2 * math.pi * k / segments
        d = u * math.cos(ang) + v * math.sin(ang)
        ring0.append(a + d * r0)
        ring1.append(b + d * r1)
    length = (b - a).length
    for k in range(segments):
        k2 = (k + 1) % segments
        mid = ((ring0[k] + ring0[k2]) / 2) - a
        uvs = [(k / segments, 0.0), ((k + 1) / segments, 0.0), ((k + 1) / segments, length / mb.uv_scale),
               (k / segments, length / mb.uv_scale)]
        mb.quad_facing(tuple(ring0[k]), tuple(ring0[k2]), tuple(ring1[k2]), tuple(ring1[k]), tuple(mid), mat, uvs, smooth)
    if caps:
        for ring, outward in ((ring0, -axis), (ring1, axis)):
            pts = [tuple(p) for p in ring]
            if face_normal(pts).dot(outward) < 0:
                pts.reverse()
            mb.face(pts, mat)


def grid_surface(mb: MeshBuilder, corner_fn, nu: int, nv: int, mat: str, uv_size=(1.0, 1.0),
                 smooth: bool = True) -> None:
    """Surface from corner_fn(u, v) -> game point over [0,1]^2 (sails, flags). Its front faces
    the side where u x v points; sails and flags use two-sided materials anyway."""
    pts = [[corner_fn(i / nu, j / nv) for j in range(nv + 1)] for i in range(nu + 1)]
    for i in range(nu):
        for j in range(nv):
            quad = [pts[i][j], pts[i + 1][j], pts[i + 1][j + 1], pts[i][j + 1]]
            uvs = [(i / nu * uv_size[0], j / nv * uv_size[1]), ((i + 1) / nu * uv_size[0], j / nv * uv_size[1]),
                   ((i + 1) / nu * uv_size[0], (j + 1) / nv * uv_size[1]), (i / nu * uv_size[0], (j + 1) / nv * uv_size[1])]
            mb.face(quad, mat, uvs, smooth)


# --- Objects, modifiers, export, previews ------------------------------------------------

def weld(obj, dist: float = 0.0005) -> None:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=dist)
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


def apply_boolean_difference(target, cutters) -> None:
    """Subtracts the cutter objects from target and removes the cutters."""
    for cutter in cutters:
        mod = target.modifiers.new(name="cut", type="BOOLEAN")
        mod.operation = "DIFFERENCE"
        mod.object = cutter
        try:
            mod.solver = "EXACT"
            mod.material_mode = "TRANSFER"
        except (TypeError, AttributeError):
            pass
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = target.evaluated_get(depsgraph)
    new_mesh = bpy.data.meshes.new_from_object(evaluated)
    old = target.data
    target.modifiers.clear()
    target.data = new_mesh
    bpy.data.meshes.remove(old)
    for cutter in cutters:
        bpy.data.objects.remove(cutter, do_unlink=True)


def empty(name: str, position, facing=None, parent=None):
    """Empty at a game-space position. `facing` (game x, z) is where its Godot -Z points."""
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_type = "ARROWS"
    obj.location = to_blender(position)
    if facing is not None:
        # Godot -Z is Blender +Y; turn +Y toward (x, -z).
        bx, by = facing[0], -facing[1]
        obj.rotation_euler = (0.0, 0.0, math.atan2(-bx, by))
    bpy.context.scene.collection.objects.link(obj)
    if parent is not None:
        obj.parent = parent
    return obj


def export_glb(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    options = dict(filepath=path, export_format="GLB", use_selection=False, export_apply=True,
                   export_yup=True, export_texcoords=True, export_normals=True,
                   export_materials="EXPORT", export_extras=True)
    try:
        bpy.ops.export_scene.gltf(export_vertex_color="ACTIVE", **options)
    except TypeError:
        bpy.ops.export_scene.gltf(**options)
    print(f"[export] {path}")


def save_blend(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=path, check_existing=False)
    print(f"[blend] {path}")


def render_views(out_dir: str, views, resolution=(1280, 720), color_type: str = "MATERIAL") -> None:
    """Workbench renders. views: list of (name, eye, target, ortho_scale or None) in game space.
    color_type "VERTEX" shows the vertex colours instead of material colours."""
    os.makedirs(out_dir, exist_ok=True)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x, scene.render.resolution_y = resolution
    shading = scene.display.shading
    shading.light = "STUDIO"
    shading.color_type = color_type
    shading.show_shadows = True
    shading.show_cavity = True
    shading.cavity_type = "WORLD"
    scene.world = scene.world or bpy.data.worlds.new("World")
    cam_data = bpy.data.cameras.new("PreviewCam")
    cam = bpy.data.objects.new("PreviewCam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    for name, eye, target, ortho in views:
        cam.location = to_blender(eye)
        direction = to_blender(target) - to_blender(eye)
        if abs(direction.normalized().z) > 0.999:
            cam.rotation_euler = (0.0, 0.0, 0.0)  # straight down, north at the top
        else:
            cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
        cam_data.type = "ORTHO" if ortho else "PERSP"
        if ortho:
            cam_data.ortho_scale = ortho
        cam_data.lens = 35
        cam_data.clip_end = 20000
        scene.render.filepath = os.path.join(out_dir, f"{name}.png")
        bpy.ops.render.render(write_still=True)
        print(f"[preview] {scene.render.filepath}")
    bpy.data.objects.remove(cam, do_unlink=True)

@tool
class_name WaterSurface
extends Node3D
## The bay's water: a graded grid (dense near the fort, coarse far out) plus a flat ring out
## to the horizon. Pushes `waves` into the shader and makes them the CPU WaveMath waves.
## Keep this node's basis at identity: the shader treats model space as world space.

@export var waves: WaveSet
@export var material: ShaderMaterial
## Point (x, z) where the grid is densest, and how far the grid reaches from it.
@export var dense_point: Vector2 = Vector2(150.0, 0.0)
@export var extent_west: float = 600.0
@export var extent_east: float = 2600.0
@export var extent_north: float = 2600.0
@export var extent_south: float = 2600.0
## Share of linear (vs. quadratic) spacing growth away from the dense point.
@export_range(0.0, 1.0) var grading_linear: float = 0.2
@export var editor_resolution: int = 120
@export var horizon_size: float = 40000.0

var _grid: MeshInstance3D
var _ring: MeshInstance3D


func _ready() -> void:
	_grid = _make_instance()
	_ring = _make_instance()
	if not Engine.is_editor_hint():
		WaveMath.current = waves
		Settings.changed.connect(rebuild)
	rebuild()


func rebuild() -> void:
	if waves != null and material != null:
		waves.apply_to(material)
	var resolution := editor_resolution if Engine.is_editor_hint() else Settings.water_grid_resolution()
	_grid.mesh = _build_grid(resolution)
	_ring.mesh = _build_ring()


func _make_instance() -> MeshInstance3D:
	var instance := MeshInstance3D.new()
	instance.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	instance.material_override = material
	instance.extra_cull_margin = 4.0
	add_child(instance)
	return instance


func _build_grid(resolution: int) -> ArrayMesh:
	var xs := _axis(resolution, extent_west, extent_east, dense_point.x)
	var zs := _axis(resolution, extent_north, extent_south, dense_point.y)
	var w := xs.size()
	var verts := PackedVector3Array()
	verts.resize(w * zs.size())
	var v := 0
	for z in zs:
		for x in xs:
			verts[v] = Vector3(x, 0.0, z)
			v += 1
	var indices := PackedInt32Array()
	indices.resize((w - 1) * (zs.size() - 1) * 6)
	var k := 0
	for j in zs.size() - 1:
		for i in w - 1:
			var a := j * w + i
			var c := a + w
			indices[k] = a
			indices[k + 1] = a + 1
			indices[k + 2] = c + 1
			indices[k + 3] = a
			indices[k + 4] = c + 1
			indices[k + 5] = c
			k += 6
	return _mesh_from(verts, indices)


## The flat water beyond the grid: four strips framing it, out to the horizon.
func _build_ring() -> ArrayMesh:
	var h := horizon_size * 0.5
	var x0 := dense_point.x - extent_west
	var x1 := dense_point.x + extent_east
	var z0 := dense_point.y - extent_north
	var z1 := dense_point.y + extent_south
	var rects := [
		Rect2(-h, -h, 2.0 * h, z0 + h),
		Rect2(-h, z1, 2.0 * h, h - z1),
		Rect2(-h, z0, x0 + h, z1 - z0),
		Rect2(x1, z0, h - x1, z1 - z0),
	]
	var verts := PackedVector3Array()
	var indices := PackedInt32Array()
	for r: Rect2 in rects:
		var base := verts.size()
		verts.append(Vector3(r.position.x, 0.0, r.position.y))
		verts.append(Vector3(r.end.x, 0.0, r.position.y))
		verts.append(Vector3(r.position.x, 0.0, r.end.y))
		verts.append(Vector3(r.end.x, 0.0, r.end.y))
		indices.append_array(PackedInt32Array([base, base + 1, base + 3, base, base + 3, base + 2]))
	return _mesh_from(verts, indices)


func _mesh_from(verts: PackedVector3Array, indices: PackedInt32Array) -> ArrayMesh:
	var normals := PackedVector3Array()
	normals.resize(verts.size())
	normals.fill(Vector3.UP)
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = verts
	arrays[Mesh.ARRAY_NORMAL] = normals
	arrays[Mesh.ARRAY_INDEX] = indices
	var mesh := ArrayMesh.new()
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	return mesh


## Grid coordinates along one axis: dense at `center`, spacing growing toward both ends.
## Vertices are split between the sides in proportion to their extents, so the spacing
## right at the centre matches on both sides.
func _axis(resolution: int, neg_extent: float, pos_extent: float, center: float) -> PackedFloat32Array:
	var n_neg := maxi(roundi(resolution * neg_extent / (neg_extent + pos_extent)), 2)
	var n_pos := maxi(resolution - n_neg, 2)
	var out := PackedFloat32Array()
	for i in range(n_neg, 0, -1):
		out.append(center - neg_extent * _grade(float(i) / n_neg))
	out.append(center)
	for i in range(1, n_pos + 1):
		out.append(center + pos_extent * _grade(float(i) / n_pos))
	return out


func _grade(s: float) -> float:
	return grading_linear * s + (1.0 - grading_linear) * s * s

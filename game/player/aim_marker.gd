class_name AimMarker
extends Node3D
## Ring drawn on the water where the active gun will land its shot. The colour says whether
## the gun can reach the point; the ring fills in as the gun reloads, and it scales with
## distance so it stays readable.

const COLORS := {
	Cannon.Aim.READY: Color(1.0, 0.85, 0.35),
	Cannon.Aim.OUT_OF_RANGE: Color(0.95, 0.25, 0.2),
	Cannon.Aim.TOO_CLOSE: Color(1.0, 0.55, 0.15),
	Cannon.Aim.OUT_OF_ARC: Color(0.7, 0.7, 0.7),
}

## A lead marker (aim assist) uses one fixed pale colour instead of the aim-state colours.
@export var lead: bool = false

@onready var _ring: MeshInstance3D = $Ring
@onready var _dot: MeshInstance3D = $Dot

var _material: StandardMaterial3D


func _ready() -> void:
	_material = StandardMaterial3D.new()
	_material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	_material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	_material.no_depth_test = true
	_material.render_priority = 10
	_ring.material_override = _material
	_dot.material_override = _material
	visible = false


func show_at(point: Vector3, state: Cannon.Aim, camera: Camera3D, loaded_fraction: float) -> void:
	visible = true
	global_position = point + Vector3(0.0, 0.2, 0.0)
	var distance := camera.global_position.distance_to(point)
	scale = Vector3.ONE * clampf(distance * 0.01 * camera.fov / 55.0, 0.5, 40.0)
	var color: Color = Color(0.6, 0.92, 1.0) if lead else COLORS.get(state, Color.WHITE)
	color.a = 0.55 if lead else lerpf(0.3, 0.95, loaded_fraction)
	_material.albedo_color = color


func hide_marker() -> void:
	visible = false

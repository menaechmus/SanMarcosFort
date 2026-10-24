class_name CameraRig
extends Camera3D
## Gun-crew camera. Sits at the active gun's camera anchor, pans within the gun's field of
## fire, zooms like a spyglass and shakes when the gun fires.

@export var normal_fov: float = 55.0
@export var spyglass_fov: float = 14.0
## Radians of pan per pixel dragged at normal zoom.
@export var pan_sensitivity: float = 0.004
## Radians per second for keyboard panning at normal zoom.
@export var key_pan_speed: float = 0.9
@export var pitch_min_deg: float = -35.0
@export var pitch_max_deg: float = 12.0
@export var move_time: float = 0.6

var yaw_offset: float = 0.0
var pitch_offset: float = 0.0

var _anchor: Node3D
var _yaw_limit: float = PI
var _from: Transform3D
var _blend: float = 1.0
var _shake: float = 0.0
var _target_fov: float = 55.0


func _ready() -> void:
	_target_fov = normal_fov
	fov = normal_fov


## Moves the camera to `anchor`; it may then pan `yaw_limit` radians either way.
func follow(anchor: Node3D, yaw_limit: float, instant: bool = false) -> void:
	_from = global_transform
	_blend = 1.0 if instant else 0.0
	_anchor = anchor
	_yaw_limit = yaw_limit
	yaw_offset = 0.0
	pitch_offset = 0.0
	if instant:
		global_transform = _target_transform()


func pan(pixels: Vector2, keys: Vector2, delta: float) -> void:
	var zoom := fov / normal_fov
	yaw_offset -= (pixels.x * pan_sensitivity + keys.x * key_pan_speed * delta) * zoom
	pitch_offset -= (pixels.y * pan_sensitivity + keys.y * key_pan_speed * delta) * zoom
	yaw_offset = clampf(yaw_offset, -_yaw_limit, _yaw_limit)


func zoom(steps: float) -> void:
	_target_fov = clampf(_target_fov * pow(0.85, steps), spyglass_fov, normal_fov)


func toggle_spyglass() -> void:
	var zoomed := _target_fov < (spyglass_fov + normal_fov) * 0.5
	_target_fov = normal_fov if zoomed else spyglass_fov


func add_shake(amount: float) -> void:
	_shake = minf(_shake + amount, 1.0)


func _process(delta: float) -> void:
	if _anchor == null:
		return
	var target := _target_transform()
	if _blend < 1.0:
		_blend = minf(_blend + delta / move_time, 1.0)
		global_transform = _from.interpolate_with(target, smoothstep(0.0, 1.0, _blend))
	else:
		global_transform = target
	if _shake > 0.0:
		var jolt := _shake * _shake * 0.02
		rotate_object_local(Vector3.RIGHT, randf_range(-jolt, jolt))
		rotate_object_local(Vector3.UP, randf_range(-jolt, jolt))
		_shake = maxf(_shake - delta * 2.5, 0.0)
	fov = lerpf(fov, _target_fov, 1.0 - exp(-8.0 * delta))


func _target_transform() -> Transform3D:
	var anchor_xf := _anchor.global_transform
	var fwd := -anchor_xf.basis.z.normalized()
	var yaw := atan2(-fwd.x, -fwd.z) + yaw_offset
	var pitch := asin(clampf(fwd.y, -1.0, 1.0)) + pitch_offset
	var pitch_limit := clampf(pitch, deg_to_rad(pitch_min_deg), deg_to_rad(pitch_max_deg))
	pitch_offset += pitch_limit - pitch
	return Transform3D(Basis.from_euler(Vector3(pitch_limit, yaw, 0.0)), anchor_xf.origin)

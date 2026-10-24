@tool
class_name ShipLane
extends Path3D
## A sailing lane through the bay, from where ships appear to where they escape. Curve handles
## are smoothed automatically, so a lane is laid out by placing its points only.

@export var auto_smooth: bool = true


func _ready() -> void:
	if curve == null:
		return
	if auto_smooth:
		smooth()
	curve.bake_interval = 2.0


## Catmull-Rom style handles through the curve's points.
func smooth() -> void:
	var count := curve.point_count
	for i in count:
		var prev := curve.get_point_position(maxi(i - 1, 0))
		var next := curve.get_point_position(mini(i + 1, count - 1))
		var handle := (next - prev) / 6.0
		curve.set_point_in(i, -handle)
		curve.set_point_out(i, handle)


func length() -> float:
	return curve.get_baked_length()


## Pose on the lane `distance` metres from its start, shifted `offset` metres to starboard.
## The basis is level (yaw only) with -Z pointing along the lane.
func sample(distance: float, offset: float) -> Transform3D:
	var total := length()
	var d := clampf(distance, 0.0, total)
	var here := to_global(curve.sample_baked(d, true))
	var dir := Vector3.ZERO
	if d + 1.0 <= total:
		dir = to_global(curve.sample_baked(d + 1.0, true)) - here
	else:
		dir = here - to_global(curve.sample_baked(maxf(d - 1.0, 0.0), true))
	dir.y = 0.0
	if dir.length_squared() < 0.000001:
		dir = Vector3.FORWARD
	var basis := Basis.looking_at(dir.normalized(), Vector3.UP)
	var pos := here + basis.x * offset
	pos.y = 0.0
	return Transform3D(basis, pos)

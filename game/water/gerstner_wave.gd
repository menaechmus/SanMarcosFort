@tool
class_name GerstnerWave
extends Resource
## One Gerstner wave train. `direction_deg` is the direction the wave travels, in degrees
## from +X (east) toward +Z (south).

@export_range(0.0, 360.0) var direction_deg: float = 0.0:
	set(value):
		direction_deg = value
		emit_changed()
@export_range(2.0, 400.0, 0.1, "suffix:m") var wavelength: float = 30.0:
	set(value):
		wavelength = value
		emit_changed()
## 0 = flat, 1 = sharp crests. Keep the sum over all waves below 1.
@export_range(0.0, 1.0) var steepness: float = 0.1:
	set(value):
		steepness = value
		emit_changed()

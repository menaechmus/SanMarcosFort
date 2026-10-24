@tool
class_name WaveSet
extends Resource
## The bay's wave trains. Shared by water.gdshader (as uniforms) and WaveMath (on the CPU),
## so floating objects ride exactly on the rendered surface.

const MAX_WAVES := 6
## Values per wave in the CPU cache: direction x, direction z, wavenumber k, angular speed, steepness.
const STRIDE := 5

@export var waves: Array[GerstnerWave] = []:
	set(value):
		waves = value
		_dirty = true
		emit_changed()
@export var gravity: float = 9.81
## Waves fade out between fade_start and fade_end metres from fade_center, so far water is flat.
@export var fade_center: Vector2 = Vector2.ZERO
@export var fade_start: float = 1300.0
@export var fade_end: float = 2200.0

var _cache: PackedFloat32Array = PackedFloat32Array()
var _dirty: bool = true


func get_cache() -> PackedFloat32Array:
	if _dirty or Engine.is_editor_hint():
		_rebuild()
	return _cache


func fade_at(x: float, z: float) -> float:
	return 1.0 - smoothstep(fade_start, fade_end, Vector2(x, z).distance_to(fade_center))


func apply_to(material: ShaderMaterial) -> void:
	for i in MAX_WAVES:
		var packed := Vector4(1.0, 0.0, 1.0, 0.0)
		if i < waves.size() and waves[i] != null:
			var wave := waves[i]
			var dir := Vector2.from_angle(deg_to_rad(wave.direction_deg))
			packed = Vector4(dir.x, dir.y, TAU / wave.wavelength, wave.steepness)
		material.set_shader_parameter("wave_%d" % i, packed)
	material.set_shader_parameter("gravity", gravity)
	material.set_shader_parameter("fade_center", fade_center)
	material.set_shader_parameter("fade_start", fade_start)
	material.set_shader_parameter("fade_end", fade_end)


func _rebuild() -> void:
	_cache = PackedFloat32Array()
	for i in mini(waves.size(), MAX_WAVES):
		var wave := waves[i]
		if wave == null or wave.steepness <= 0.0:
			continue
		var dir := Vector2.from_angle(deg_to_rad(wave.direction_deg))
		var k := TAU / wave.wavelength
		_cache.append(dir.x)
		_cache.append(dir.y)
		_cache.append(k)
		_cache.append(sqrt(gravity * k))
		_cache.append(wave.steepness)
	_dirty = false

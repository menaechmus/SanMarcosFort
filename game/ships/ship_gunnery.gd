class_name ShipGunnery
extends Node
## Broadsides at the fort. When an armed ship has the Castillo in range and off its beam, the
## guns on that side fire, slightly staggered, from the gunport markers in the ship's model.
## Their aim tightens in later waves.

## The fort is engaged when it lies within this angle of the ship's beam.
const ARC_DEG := 30.0
const SHOT_SPEED := 115.0
## What the gunners aim at: the middle of the fort's bay-side walls (world).
const TARGET := Vector3(18.0, 8.5, 0.0)
const TARGET_HALF_SIZE := Vector3(30.0, 2.5, 34.0)
## Fort and terrain layers.
const SHOT_MASK := 0b011

var ammo: AmmoDef
var flash_fx: PackedScene

var _ship: Ship
var _ports := {1: [], -1: []}
var _reload := {1: 0.0, -1: 0.0}
var _spread: float = 1.0
var _gravity: float = 9.81


func setup(ship: Ship, model: Node3D, shot: AmmoDef, flash: PackedScene) -> void:
	_ship = ship
	ammo = shot
	flash_fx = flash
	_gravity = ProjectSettings.get_setting("physics/3d/default_gravity", 9.81)
	for node in model.find_children("Port_*", "Node3D", true, false):
		var side := 1 if String(node.name).begins_with("Port_S") else -1
		_ports[side].append(node)
	# Gunners find the range as the waves go on.
	_spread = clampf(1.0 - 0.07 * (GameState.wave - 1), 0.35, 1.0)
	_reload[1] = randf_range(2.0, 6.0)
	_reload[-1] = randf_range(2.0, 6.0)


func _process(delta: float) -> void:
	if _ship == null or not _ship.is_sailing() or not GameState.is_playing():
		return
	_reload[1] -= delta
	_reload[-1] -= delta
	var to_fort := TARGET - _ship.global_position
	var flat := Vector2(to_fort.x, to_fort.z)
	if flat.length() > _ship.def.gun_range:
		return
	var right := _ship.global_basis.x
	var side := 1 if right.x * flat.x + right.z * flat.y > 0.0 else -1
	var fwd := -_ship.global_basis.z
	var off_beam := absf(Vector2(fwd.x, fwd.z).normalized().dot(flat.normalized()))
	if off_beam > sin(deg_to_rad(ARC_DEG)) or _reload[side] > 0.0:
		return
	_reload[side] = _ship.def.gun_reload * randf_range(0.9, 1.25)
	_broadside(side)


func _broadside(side: int) -> void:
	var guns: Array = _ports[side]
	for i in guns.size():
		var delay := i * 0.08 + randf() * 0.12
		get_tree().create_timer(delay, false).timeout.connect(_fire.bind(guns[i], i % 2 == 0))


## Fires one gun; `sound` is off for every other gun so a broadside doesn't swamp the mix.
func _fire(port: Node3D, sound: bool) -> void:
	if not is_instance_valid(port) or not _ship.is_sailing() or not GameState.is_playing():
		return
	var origin := port.global_position
	var jitter := Vector3(randf_range(-1, 1), randf_range(-1, 1), randf_range(-1, 1)) * TARGET_HALF_SIZE * _spread
	var target := TARGET + jitter
	var flat := Vector2(target.x - origin.x, target.z - origin.z)
	var elevation := Ballistics.solve_elevation(flat.length(), target.y - origin.y, SHOT_SPEED, _gravity)
	if is_nan(elevation):
		return
	var dir := Vector3(flat.x, 0.0, flat.y).normalized() * cos(elevation) + Vector3.UP * sin(elevation)
	ProjectilePool.instance.fire(origin, dir * SHOT_SPEED, ammo, SHOT_MASK, false)
	Fx.spawn(flash_fx, origin, dir, 0.7)
	if sound:
		Audio.play_3d(&"cannon_far", origin, -2.0, 0.12)

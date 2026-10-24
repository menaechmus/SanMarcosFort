class_name Cannon
extends Node3D
## A muzzle-loading gun. Lays itself (traverse and elevation, at limited speed) toward an aim
## point and fires once loaded and laid. Local -Z is the centre of its field of fire.

signal fired(cannon: Cannon)

enum Aim { NONE, READY, OUT_OF_RANGE, TOO_CLOSE, OUT_OF_ARC }

## The gun snaps the last fraction of a degree (0.8°, in radians) when it fires.
const LAY_TOLERANCE := 0.014
## A fire request waits this long for the gun to be loaded and laid.
const FIRE_REQUEST_TIME := 1.5

@export var ammo: AmmoDef
@export var reload_time: float = 3.5
@export var traverse_speed_deg: float = 28.0
@export var elevation_speed_deg: float = 10.0
@export var min_elevation_deg: float = -7.0
@export var max_elevation_deg: float = 12.0
@export var yaw_limit_deg: float = 40.0
@export var dispersion_deg: float = 0.1
## Physics layers the shot can strike.
@export_flags_3d_physics var shot_mask: int = 0b101
@export var from_player: bool = true
@export var muzzle_flash_fx: PackedScene
@export var recoil_distance: float = 0.8

var aim_state: Aim = Aim.NONE
var reload_left: float = 0.0
## Seconds the crew stays knocked out after a near hit.
var suppressed_left: float = 0.0

var _yaw: float = 0.0
var _pitch: float = 0.0
var _target_yaw: float = 0.0
var _target_pitch: float = 0.0
var _fire_request: float = 0.0
var _gravity: float = 9.81
var _carriage_home: Vector3

@onready var _yaw_pivot: Node3D = $Yaw
@onready var _pitch_pivot: Node3D = $Yaw/Pitch
@onready var _muzzle: Node3D = $Yaw/Pitch/Muzzle


func _ready() -> void:
	_gravity = ProjectSettings.get_setting("physics/3d/default_gravity", 9.81)
	_carriage_home = _yaw_pivot.position


func is_loaded() -> bool:
	return reload_left <= 0.0 and suppressed_left <= 0.0


func reload_fraction() -> float:
	return 1.0 - clampf(reload_left / _reload_duration(), 0.0, 1.0)


## Muzzle speed including the player's powder upgrade; aiming and firing both use it.
func effective_speed() -> float:
	return ammo.muzzle_speed * (GameState.upgrades.speed_factor() if from_player else 1.0)


func _reload_duration() -> float:
	return reload_time * (GameState.upgrades.reload_factor() if from_player else 1.0)


func is_laid() -> bool:
	return absf(_yaw - _target_yaw) < LAY_TOLERANCE and absf(_pitch - _target_pitch) < LAY_TOLERANCE


## World position the ballistic solution is computed from (the trunnions).
func pivot_position() -> Vector3:
	return _pitch_pivot.global_position


## Lays the gun toward a world point and returns whether it can hit it.
func aim_at(point: Vector3) -> Aim:
	var local := global_transform.affine_inverse() * point
	var flat := Vector2(local.x, local.z).length()
	var yaw := atan2(-local.x, -local.z)
	var limit := deg_to_rad(yaw_limit_deg)
	aim_state = Aim.READY
	if absf(yaw) > limit:
		yaw = clampf(yaw, -limit, limit)
		aim_state = Aim.OUT_OF_ARC
	var elevation := Ballistics.solve_elevation(flat, point.y - pivot_position().y, effective_speed(), _gravity)
	var max_el := deg_to_rad(max_elevation_deg)
	var min_el := deg_to_rad(min_elevation_deg)
	if is_nan(elevation) or elevation > max_el:
		elevation = max_el
		if aim_state == Aim.READY:
			aim_state = Aim.OUT_OF_RANGE
	elif elevation < min_el:
		elevation = min_el
		if aim_state == Aim.READY:
			aim_state = Aim.TOO_CLOSE
	_target_yaw = yaw
	_target_pitch = elevation
	return aim_state


## Fires as soon as the gun is loaded and laid on a reachable point.
func request_fire() -> void:
	_fire_request = FIRE_REQUEST_TIME


func _process(delta: float) -> void:
	reload_left = maxf(reload_left - delta, 0.0)
	suppressed_left = maxf(suppressed_left - delta, 0.0)
	_yaw = move_toward(_yaw, _target_yaw, deg_to_rad(traverse_speed_deg) * delta)
	_pitch = move_toward(_pitch, _target_pitch, deg_to_rad(elevation_speed_deg) * delta)
	_apply_pose()
	if _fire_request > 0.0:
		_fire_request -= delta
		if is_loaded() and is_laid() and aim_state == Aim.READY:
			_fire_request = 0.0
			_fire()


func _apply_pose() -> void:
	_yaw_pivot.rotation.y = _yaw
	_pitch_pivot.rotation.x = _pitch


func _fire() -> void:
	_yaw = _target_yaw
	_pitch = _target_pitch
	_apply_pose()
	var dir := -_muzzle.global_basis.z.normalized()
	var spread := deg_to_rad(dispersion_deg) * (GameState.upgrades.dispersion_factor() if from_player else 1.0)
	var side := dir.cross(Vector3.UP).normalized()
	dir = dir.rotated(Vector3.UP, randfn(0.0, spread)).rotated(side, randfn(0.0, spread))
	ProjectilePool.instance.fire(_muzzle.global_position, dir * effective_speed(), ammo, shot_mask, from_player)
	reload_left = _reload_duration()
	Fx.spawn(muzzle_flash_fx, _muzzle.global_position, dir)
	Audio.play_3d(&"cannon", _muzzle.global_position)
	_recoil()
	fired.emit(self)


func _recoil() -> void:
	var back := _carriage_home + Basis(Vector3.UP, _yaw) * Vector3(0.0, 0.0, recoil_distance)
	var tween := create_tween()
	tween.tween_property(_yaw_pivot, "position", back, 0.08).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	tween.tween_property(_yaw_pivot, "position", _carriage_home, 1.4).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)

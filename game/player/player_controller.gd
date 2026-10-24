class_name PlayerController
extends Node
## Connects input, camera, aim marker and the fort's guns. The active gun lays itself on the
## point of water under the pointer and fires on request; the player picks the ammunition.
## With `--autoplay` a bot aims instead.

signal ammo_changed(ammo: AmmoDef)

## Physics layers the pointer can rest on before reaching the water: terrain only. The fort's
## own parapet stands in front of every gun and would otherwise catch the pointer.
const POINTER_BLOCK_MASK := 0b01
## How far the camera can look either side of the active gun's line, wider than the gun can be
## laid, so ships can be watched coming before any gun bears on them.
const LOOK_AROUND_DEG := 55.0
const AMMO: Array[AmmoDef] = [
	preload("res://game/weapons/round_shot.tres"),
	preload("res://game/weapons/chain_shot.tres"),
	preload("res://game/weapons/heated_shot.tres"),
]
## Upgrade that unlocks each entry of AMMO (empty: always available).
const AMMO_UPGRADE: Array[StringName] = [&"", &"chain", &"heated"]

@export var guns_root: Node3D
@export var initial_gun: int = 1
@export var ships_root: Node3D

var guns: Array[GunPosition] = []
var active_index: int = 0
var ammo_index: int = 0
var aim_point: Vector3 = Vector3.ZERO
var aim_valid: bool = false
## When set (e.g. a debug camera bookmark), switching guns no longer moves the camera.
var camera_locked: bool = false

var _gravity: float = 9.81
var _extra_guns_manned: bool = false

## Aim assist looks for a ship this close to the aim point.
const ASSIST_RADIUS := 140.0

@onready var input: AimInput = $AimInput
@onready var rig: CameraRig = $CameraRig
@onready var marker: AimMarker = $AimMarker
@onready var lead_marker: AimMarker = $LeadMarker


func _ready() -> void:
	_gravity = ProjectSettings.get_setting("physics/3d/default_gravity", 9.81)
	_collect_guns()
	input.fire_requested.connect(fire)
	input.gun_cycled.connect(cycle_gun)
	input.gun_selected.connect(select_gun)
	input.spyglass_toggled.connect(rig.toggle_spyglass)
	input.ammo_cycled.connect(cycle_ammo)
	GameState.changed.connect(_check_unlocks)
	active_index = clampi(initial_gun, 0, guns.size() - 1)


func active_gun() -> GunPosition:
	return guns[active_index]


func current_ammo() -> AmmoDef:
	return AMMO[ammo_index]


func select_gun(index: int, instant: bool = false) -> void:
	if index < 0 or index >= guns.size():
		return
	active_index = index
	var gun := guns[index]
	if not camera_locked:
		rig.follow(gun.camera_anchor, deg_to_rad(LOOK_AROUND_DEG), instant)


## Index of the first manned gun whose field of fire takes in `point`, or -1 if none does.
func gun_that_bears(point: Vector3) -> int:
	for i in guns.size():
		if guns[i].cannon.in_arc(point):
			return i
	return -1


func cycle_gun(step: int) -> void:
	if GameState.is_playing():
		select_gun(wrapi(active_index + step, 0, guns.size()))


func fire() -> void:
	if aim_valid and GameState.is_playing():
		active_gun().cannon.request_fire()


func available_ammo() -> Array[int]:
	var out: Array[int] = []
	for i in AMMO.size():
		if AMMO_UPGRADE[i] == &"" or GameState.upgrades.has(AMMO_UPGRADE[i]):
			out.append(i)
	return out


func cycle_ammo() -> void:
	var available := available_ammo()
	ammo_index = available[(available.find(ammo_index) + 1) % available.size()]
	_apply_ammo()


func _apply_ammo() -> void:
	for gun in guns:
		gun.cannon.ammo = AMMO[ammo_index]
	ammo_changed.emit(AMMO[ammo_index])


func _collect_guns() -> void:
	var current: GunPosition = guns[active_index] if active_index < guns.size() else null
	guns.clear()
	for child in guns_root.get_children():
		var gun := child as GunPosition
		if gun == null or not gun.unlocked:
			continue
		guns.append(gun)
		if not gun.cannon.fired.is_connected(_on_cannon_fired):
			gun.cannon.fired.connect(_on_cannon_fired)
		gun.cannon.ammo = AMMO[ammo_index]
	if current != null:
		active_index = maxi(guns.find(current), 0)


func _check_unlocks() -> void:
	if not _extra_guns_manned and GameState.upgrades.has(&"gun"):
		_extra_guns_manned = true
		var fort := guns_root.get_parent() as Fort
		if fort != null:
			fort.unlock_guns()
		_collect_guns()


func _process(delta: float) -> void:
	var keys := Input.get_vector(&"pan_left", &"pan_right", &"pan_up", &"pan_down")
	rig.pan(input.pan_pixels, keys, delta)
	input.pan_pixels = Vector2.ZERO
	if input.zoom_steps != 0.0:
		rig.zoom(input.zoom_steps)
		input.zoom_steps = 0.0
	if not GameState.is_playing():
		aim_valid = false
		marker.hide_marker()
		lead_marker.hide_marker()
		return
	if DebugCli.autoplay:
		_bot_aim()
	else:
		aim_valid = input.has_pointer and _pointer_target(input.pointer)
	var cannon := active_gun().cannon
	if aim_valid:
		var state := cannon.aim_at(aim_point)
		marker.show_at(aim_point, state, rig, cannon.reload_fraction())
	else:
		marker.hide_marker()
	_update_lead_marker(cannon)


## Aim assist: a pale ring where to aim so a ball fired now meets the ship nearest the pointer.
func _update_lead_marker(cannon: Cannon) -> void:
	var target: Ship = _ship_near(aim_point, ASSIST_RADIUS) if aim_valid and Settings.aim_assist else null
	if target == null:
		lead_marker.hide_marker()
		return
	var lead := Ballistics.lead_point(cannon.pivot_position(), target.global_position + Vector3(0.0, 1.0, 0.0),
			target.velocity, cannon.effective_speed(), _gravity)
	lead.y = WaveMath.height(lead.x, lead.z)
	lead_marker.show_at(lead, Cannon.Aim.READY, rig, 1.0)


func _ship_near(point: Vector3, radius: float) -> Ship:
	var nearest: Ship = null
	var best := radius * radius
	for child in ships_root.get_children():
		var ship := child as Ship
		if ship == null or not ship.is_sailing():
			continue
		var d := Vector2(ship.global_position.x - point.x, ship.global_position.z - point.z).length_squared()
		if d < best:
			best = d
			nearest = ship
	return nearest


## Finds where the pointer's ray meets the water (or the land/fort in front of it).
func _pointer_target(screen: Vector2) -> bool:
	var from := rig.project_ray_origin(screen)
	var dir := rig.project_ray_normal(screen)
	var water_point := Vector3.INF
	if dir.y < -0.0001:
		var t := -from.y / dir.y
		var flat := from + dir * t
		t = (WaveMath.height(flat.x, flat.z) - from.y) / dir.y
		water_point = from + dir * t
	var reach := 6000.0 if water_point == Vector3.INF else from.distance_to(water_point)
	var space := rig.get_world_3d().direct_space_state
	var hit := space.intersect_ray(PhysicsRayQueryParameters3D.create(from, from + dir * reach, POINTER_BLOCK_MASK))
	if not hit.is_empty():
		aim_point = hit.position
		return true
	if water_point == Vector3.INF:
		return false
	aim_point = water_point
	return true


## Autoplay: lay the best-placed gun on the nearest ship a gun can bear on, leading its motion.
func _bot_aim() -> void:
	var target := _bot_target()
	if target == null:
		aim_valid = false
		return
	var best := active_index
	var best_angle := INF
	for i in guns.size():
		var to_target := target.global_position - guns[i].global_position
		var facing := -guns[i].global_basis.z
		var angle := absf(Vector2(facing.x, facing.z).angle_to(Vector2(to_target.x, to_target.z)))
		if angle < best_angle:
			best_angle = angle
			best = i
	if best != active_index:
		select_gun(best, true)
	var cannon := active_gun().cannon
	var aim_at := target.global_position + Vector3(0.0, 1.0, 0.0)
	aim_point = Ballistics.lead_point(cannon.pivot_position(), aim_at, target.velocity, cannon.effective_speed(), _gravity)
	aim_valid = true
	if cannon.is_loaded():
		cannon.request_fire()


## The nearest sailing ship inside some gun's field of fire; failing that, the nearest one (the
## guns lay toward it while it comes). Waiting on a ship no gun can reach would let others pass.
func _bot_target() -> Ship:
	var nearest: Ship = null
	var nearest_in_reach: Ship = null
	var best := INF
	var best_in_reach := INF
	var origin := active_gun().global_position
	for child in ships_root.get_children():
		var ship := child as Ship
		if ship == null or not ship.is_sailing():
			continue
		var d := origin.distance_squared_to(ship.global_position)
		if d < best:
			best = d
			nearest = ship
		if d < best_in_reach and gun_that_bears(ship.global_position) >= 0:
			best_in_reach = d
			nearest_in_reach = ship
	return nearest_in_reach if nearest_in_reach != null else nearest


func _on_cannon_fired(cannon: Cannon) -> void:
	GameState.record_shot()
	if cannon == active_gun().cannon:
		rig.add_shake(0.6)

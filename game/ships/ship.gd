class_name Ship
extends Node3D
## An enemy ship: sails its lane, rides the waves, fires broadsides when armed, takes hits,
## burns, loses masts and sinks.

signal sunk(ship: Ship)
signal escaped(ship: Ship)
## Emitted once when the ship leaves play, whether sunk or escaped.
signal removed(ship: Ship)

enum State { SAILING, SINKING, GONE }

const SHIP_LAYER := 4
## Hits on the hull below this height (metres above the waterline) count as waterline hits.
const WATERLINE_BAND := 0.6
const HOLE_SIZE := 0.7
## Rigging damage at which successive masts come down; full damage halves the speed.
const MAST_THRESHOLDS := [2.0, 4.0, 6.0]
const RIG_DAMAGE_FULL := 5.0

@export var def: ShipDef
@export var splinter_fx: PackedScene
@export var splash_fx: PackedScene
@export var fire_fx: PackedScene
@export var gun_flash_fx: PackedScene
@export var gun_ammo: AmmoDef

var lane: ShipLane
var lateral_offset: float = 0.0
var speed_multiplier: float = 1.0
var armed: bool = true
var state: State = State.SAILING
var health: ShipHealth
## Distance sailed along the lane.
var distance: float = 0.0
var velocity: Vector3 = Vector3.ZERO

var _speed: float = 0.0
var _heave: float = 0.0
var _pitch: float = 0.0
var _roll: float = 0.0
var _list_side: float = 0.0
var _sink_elapsed: float = 0.0
var _sink_roll: float = 0.0
var _sink_pitch: float = 0.0
var _rig_damage: float = 0.0
var _masts_down: int = 0
var _fire: Node3D
var _hitbox: AnimatableBody3D
var _model: Node3D

static var _hole_material: StandardMaterial3D


func setup(ship_def: ShipDef, ship_lane: ShipLane, offset: float, speed_mult: float, is_armed: bool = true) -> void:
	def = ship_def
	lane = ship_lane
	lateral_offset = offset
	speed_multiplier = speed_mult
	armed = is_armed


func _ready() -> void:
	health = ShipHealth.new(def.max_hp)
	health.destroyed.connect(_start_sinking)
	_speed = def.speed * speed_multiplier
	_model = def.model_scene.instantiate() as Node3D if def.model_scene else _build_greybox()
	add_child(_model)
	if not Settings.SHIP_SHADOWS[Settings.quality]:
		for mesh: GeometryInstance3D in _model.find_children("*", "GeometryInstance3D", true, false):
			mesh.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	_build_hitbox()
	if armed and def.guns_per_side > 0 and gun_ammo != null:
		var gunnery := ShipGunnery.new()
		gunnery.name = "Gunnery"
		add_child(gunnery)
		gunnery.setup(self, _model, gun_ammo, gun_flash_fx)
	_place(0.0, true)


func is_sailing() -> bool:
	return state == State.SAILING


func apply_hit(ammo: AmmoDef, zone: StringName, point: Vector3, normal: Vector3, from_player: bool) -> void:
	if state != State.SAILING:
		return
	var local := to_local(point)
	if zone == &"hull" and local.y < WATERLINE_BAND:
		zone = &"waterline"
	if _list_side == 0.0:
		_list_side = -1.0 if local.x < 0.0 else 1.0
	if from_player:
		GameState.record_hit()
	Fx.spawn(splinter_fx, point, normal)
	Audio.play_3d(&"wood_hit", point)
	if zone == &"rig":
		_rig_damage += ammo.rig_multiplier
		while _masts_down < MAST_THRESHOLDS.size() and _rig_damage >= MAST_THRESHOLDS[_masts_down]:
			_topple_mast()
	else:
		_add_hole(local, global_basis.inverse() * normal)
	if ammo.fire_damage > 0.0:
		health.burning += ammo.fire_damage
		_ignite(local)
	var damage := ammo.damage * (ammo.rig_multiplier if zone == &"rig" else 1.0)
	health.apply(damage, zone)


func _process(delta: float) -> void:
	match state:
		State.SAILING:
			health.tick(delta)
			if state != State.SAILING:
				return
			var rigging := lerpf(1.0, 0.5, clampf(_rig_damage / RIG_DAMAGE_FULL, 0.0, 1.0))
			var target_speed := def.speed * speed_multiplier * lerpf(0.7, 1.0, health.fraction()) * rigging
			_speed = move_toward(_speed, target_speed, 0.5 * delta)
			distance += _speed * delta
			if distance >= lane.length():
				_escape()
				return
		State.SINKING:
			_sink_elapsed += delta
			_speed = move_toward(_speed, 0.0, 0.35 * delta)
			distance = minf(distance + _speed * delta, lane.length())
			if _sink_elapsed >= def.sink_time:
				state = State.GONE
				removed.emit(self)
				queue_free()
				return
		State.GONE:
			return
	_place(delta, false)


## Puts the ship on its lane and on the waves: four hull points sample the water, and the
## ship eases toward their average height, pitch and roll.
func _place(delta: float, snap: bool) -> void:
	var on_lane := lane.sample(distance, lateral_offset)
	var center := on_lane.origin
	var fwd := -on_lane.basis.z
	var right := on_lane.basis.x
	var half_l := def.length * 0.4
	var half_b := def.beam * 0.5
	var bow := WaveMath.height(center.x + fwd.x * half_l, center.z + fwd.z * half_l)
	var stern := WaveMath.height(center.x - fwd.x * half_l, center.z - fwd.z * half_l)
	var port := WaveMath.height(center.x - right.x * half_b, center.z - right.z * half_b)
	var starboard := WaveMath.height(center.x + right.x * half_b, center.z + right.z * half_b)
	var damage := 1.0 - health.fraction()
	var target_heave := (bow + stern + port + starboard) * 0.25 - damage * def.draft * 0.35
	var target_pitch := atan2(bow - stern, half_l * 2.0)
	var target_roll := atan2(starboard - port, half_b * 2.0) - _list_side * damage * deg_to_rad(8.0)
	if state == State.SINKING:
		var k := clampf(_sink_elapsed / def.sink_time, 0.0, 1.0)
		# Deep enough that the listing masts go under too.
		target_heave -= (def.freeboard + def.draft + def.mast_height * 0.5 + 2.0) * smoothstep(0.1, 1.0, k)
		target_pitch += _sink_pitch * smoothstep(0.0, 0.8, k)
		target_roll += _sink_roll * smoothstep(0.0, 0.7, k)
	if snap:
		_heave = target_heave
		_pitch = target_pitch
		_roll = target_roll
	else:
		var w := 1.0 - exp(-delta * def.wave_response)
		_heave = lerpf(_heave, target_heave, w)
		_pitch = lerp_angle(_pitch, target_pitch, w * 0.8)
		_roll = lerp_angle(_roll, target_roll, w * 0.6)
	var previous := global_position
	var pose := on_lane.basis * Basis(Vector3.RIGHT, _pitch) * Basis(Vector3.BACK, _roll)
	global_transform = Transform3D(pose, Vector3(center.x, _heave, center.z))
	if delta > 0.0:
		velocity = (global_position - previous) / delta


func _start_sinking() -> void:
	if state != State.SAILING:
		return
	state = State.SINKING
	_sink_elapsed = 0.0
	var side := _list_side if _list_side != 0.0 else 1.0
	_sink_roll = -side * deg_to_rad(randf_range(35.0, 70.0))
	_sink_pitch = deg_to_rad(randf_range(-18.0, 18.0))
	_hitbox.collision_layer = 0
	Audio.play_3d(&"creak", global_position, 2.0, 0.15)
	GameState.ship_sunk(def)
	sunk.emit(self)


func _escape() -> void:
	state = State.GONE
	GameState.ship_escaped(def)
	escaped.emit(self)
	removed.emit(self)
	queue_free()


## Brings down the next standing mast: it swings over the side and splashes into the bay.
func _topple_mast() -> void:
	_masts_down += 1
	var masts := _model.find_children("Mast_*", "Node3D", true, false).filter(
			func(m: Node) -> bool: return not String(m.name).ends_with("Bowsprit") and not m.has_meta(&"down"))
	if masts.is_empty():
		return
	var mast := masts[randi() % masts.size()] as Node3D
	mast.set_meta(&"down", true)
	var side := -1.0 if randf() < 0.5 else 1.0
	var tween := create_tween()
	tween.tween_property(mast, "rotation:z", side * deg_to_rad(randf_range(70.0, 85.0)), 1.8) \
			.set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)
	tween.tween_callback(_mast_splash.bind(mast, side))


func _mast_splash(mast: Node3D, side: float) -> void:
	if is_instance_valid(mast):
		Fx.spawn(splash_fx, mast.global_position + global_basis.x * side * def.mast_height * 0.6, Vector3.UP, 1.6)


func _ignite(local_point: Vector3) -> void:
	if _fire != null or fire_fx == null:
		return
	_fire = fire_fx.instantiate() as Node3D
	_model.add_child(_fire)
	_fire.position = Vector3(clampf(local_point.x, -def.beam * 0.3, def.beam * 0.3), def.freeboard * 0.8,
			clampf(local_point.z, -def.length * 0.35, def.length * 0.35))


func _build_hitbox() -> void:
	_hitbox = AnimatableBody3D.new()
	_hitbox.sync_to_physics = false
	_hitbox.collision_layer = SHIP_LAYER
	_hitbox.collision_mask = 0
	add_child(_hitbox)
	var hull_height := def.freeboard + def.draft
	_hitbox.add_child(_box_shape(&"hull", Vector3(def.beam, hull_height, def.length),
			Vector3(0.0, (def.freeboard - def.draft) * 0.5, 0.0)))
	_hitbox.add_child(_box_shape(&"rig", Vector3(def.beam * 1.4, def.mast_height * 0.8, def.length * 0.6),
			Vector3(0.0, def.freeboard + def.mast_height * 0.5, 0.0)))


func _box_shape(zone: StringName, size: Vector3, offset: Vector3) -> CollisionShape3D:
	var box := BoxShape3D.new()
	box.size = size
	var shape := CollisionShape3D.new()
	shape.shape = box
	shape.position = offset
	shape.set_meta(&"zone", zone)
	return shape


## Placeholder model used when a ShipDef has no model: hull, mast and one sail.
func _build_greybox() -> Node3D:
	var root := Node3D.new()
	var hull_height := def.freeboard + def.draft
	_add_box(root, Vector3(def.beam, hull_height, def.length), Vector3(0.0, (def.freeboard - def.draft) * 0.5, 0.0), Color(0.3, 0.19, 0.1))
	var mast := MeshInstance3D.new()
	var cylinder := CylinderMesh.new()
	cylinder.top_radius = 0.12
	cylinder.bottom_radius = 0.22
	cylinder.height = def.mast_height
	mast.mesh = cylinder
	mast.position = Vector3(0.0, def.freeboard + def.mast_height * 0.5, 0.0)
	root.add_child(mast)
	_add_box(root, Vector3(def.beam * 1.7, def.mast_height * 0.55, 0.12), Vector3(0.0, def.freeboard + def.mast_height * 0.55, -0.35), Color(0.86, 0.82, 0.7))
	return root


func _add_box(parent: Node3D, size: Vector3, pos: Vector3, color: Color) -> void:
	var instance := MeshInstance3D.new()
	var box := BoxMesh.new()
	box.size = size
	var material := StandardMaterial3D.new()
	material.albedo_color = color
	box.material = material
	instance.mesh = box
	instance.position = pos
	parent.add_child(instance)


## A dark hole where a ball struck (quads stand in for decals, which Compatibility lacks).
func _add_hole(local_pos: Vector3, local_normal: Vector3) -> void:
	if _hole_material == null:
		_hole_material = StandardMaterial3D.new()
		_hole_material.albedo_color = Color(0.05, 0.035, 0.02)
		_hole_material.roughness = 1.0
	var quad := QuadMesh.new()
	quad.size = Vector2(HOLE_SIZE, HOLE_SIZE)
	quad.material = _hole_material
	var hole := MeshInstance3D.new()
	hole.mesh = quad
	hole.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	var n := local_normal.normalized()
	var up := Vector3.FORWARD if absf(n.y) > 0.95 else Vector3.UP
	hole.transform = Transform3D(Basis.looking_at(-n, up), local_pos + n * 0.03)
	_model.add_child(hole)

class_name ProjectilePool
extends Node3D
## Simulates every cannonball in flight. Balls follow the exact drag-free parabola and are
## ray-tested from their previous to their current position each physics tick, so fast
## shots can't pass through targets. Ball meshes are pooled.

signal impact(kind: StringName, position: Vector3)

const MAX_FLIGHT_TIME := 25.0
## Enemy balls passing this close to the listener whistle.
const WHISTLE_DISTANCE := 80.0
## Anything on this layer is ground: hits raise dust and damage nothing.
const TERRAIN_LAYER := 1
## A ball that strikes a hull this far below the waves still counts ("between wind and water").
const UNDERWATER_HIT_DEPTH := 1.0

class Shot:
	var origin: Vector3
	var velocity: Vector3
	var t: float = 0.0
	var prev: Vector3
	var ammo: AmmoDef
	var mask: int
	var from_player: bool
	var whistled: bool = false
	var node: MeshInstance3D

## The pool of the running level.
static var instance: ProjectilePool

@export var splash_fx: PackedScene
@export var dust_fx: PackedScene

var _active: Array[Shot] = []
var _idle_nodes: Array[MeshInstance3D] = []
var _gravity: float = 9.81
var _ball_mesh: SphereMesh


func _enter_tree() -> void:
	instance = self


func _exit_tree() -> void:
	if instance == self:
		instance = null


func _ready() -> void:
	_gravity = ProjectSettings.get_setting("physics/3d/default_gravity", 9.81)
	_ball_mesh = SphereMesh.new()
	_ball_mesh.radius = 0.18
	_ball_mesh.height = 0.36
	_ball_mesh.radial_segments = 12
	_ball_mesh.rings = 6
	var material := StandardMaterial3D.new()
	material.albedo_color = Color(0.07, 0.07, 0.07)
	material.metallic = 0.6
	material.roughness = 0.45
	_ball_mesh.material = material


func fire(origin: Vector3, velocity: Vector3, ammo: AmmoDef, mask: int, from_player: bool) -> void:
	var shot := Shot.new()
	shot.origin = origin
	shot.velocity = velocity
	shot.prev = origin
	shot.ammo = ammo
	shot.mask = mask
	shot.from_player = from_player
	shot.node = _take_node()
	shot.node.global_position = origin
	_active.append(shot)


func active_count() -> int:
	return _active.size()


func _physics_process(delta: float) -> void:
	if _active.is_empty():
		return
	var space := get_world_3d().direct_space_state
	var camera := get_viewport().get_camera_3d()
	for i in range(_active.size() - 1, -1, -1):
		var shot := _active[i]
		shot.t += delta
		var pos := Ballistics.position_at(shot.origin, shot.velocity, _gravity, shot.t)
		if not shot.from_player and not shot.whistled and camera != null \
				and pos.distance_to(camera.global_position) < WHISTLE_DISTANCE:
			shot.whistled = true
			Audio.play_3d(&"whistle", pos, -4.0, 0.1)
		if _step(space, shot, pos) or shot.t > MAX_FLIGHT_TIME:
			_release(i)
		else:
			shot.prev = pos


func _process(_delta: float) -> void:
	# Draw balls at their exact render-time position; physics ticks are coarser than frames.
	var ahead := Engine.get_physics_interpolation_fraction() * get_physics_process_delta_time()
	for shot in _active:
		shot.node.global_position = Ballistics.position_at(shot.origin, shot.velocity, _gravity, shot.t + ahead)


## Moves a shot to `pos`; returns true when it struck something and is finished.
func _step(space: PhysicsDirectSpaceState3D, shot: Shot, pos: Vector3) -> bool:
	var hit := space.intersect_ray(PhysicsRayQueryParameters3D.create(shot.prev, pos, shot.mask))
	if not hit.is_empty():
		var hit_pos: Vector3 = hit.position
		if hit_pos.y > WaveMath.height(hit_pos.x, hit_pos.z) - UNDERWATER_HIT_DEPTH:
			_on_hit(shot, hit)
			return true
	var below := pos.y - WaveMath.height(pos.x, pos.z)
	if below < 0.0:
		var entry := _water_entry(shot.prev, pos, below)
		Fx.spawn(splash_fx, entry, Vector3.UP, shot.ammo.splash_scale)
		Audio.play_3d(&"splash", entry, -3.0)
		impact.emit(&"water", entry)
		return true
	return false


func _water_entry(prev: Vector3, pos: Vector3, below: float) -> Vector3:
	var above := prev.y - WaveMath.height(prev.x, prev.z)
	var f := clampf(above / maxf(above - below, 0.0001), 0.0, 1.0)
	var entry := prev.lerp(pos, f)
	entry.y = WaveMath.height(entry.x, entry.z)
	return entry


func _on_hit(shot: Shot, hit: Dictionary) -> void:
	var collider := hit.collider as CollisionObject3D
	var pos: Vector3 = hit.position
	var normal: Vector3 = hit.normal
	var zone := &"hull"
	var shape_node := collider.shape_owner_get_owner(collider.shape_find_owner(hit.shape)) as Node
	if shape_node != null and shape_node.has_meta(&"zone"):
		zone = shape_node.get_meta(&"zone")
	var target: Node = null
	if not (collider.collision_layer & TERRAIN_LAYER):
		target = _damageable(collider)
	if target != null:
		target.apply_hit(shot.ammo, zone, pos, normal, shot.from_player)
		impact.emit(&"target", pos)
	else:
		Fx.spawn(dust_fx, pos, normal)
		Audio.play_3d(&"stone_hit", pos, -6.0)
		impact.emit(&"ground", pos)


func _damageable(node: Node) -> Node:
	while node != null:
		if node.has_method(&"apply_hit"):
			return node
		node = node.get_parent()
	return null


func _take_node() -> MeshInstance3D:
	var node: MeshInstance3D
	if _idle_nodes.is_empty():
		node = MeshInstance3D.new()
		node.mesh = _ball_mesh
		node.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		add_child(node)
	else:
		node = _idle_nodes.pop_back()
	node.visible = true
	return node


func _release(index: int) -> void:
	var shot := _active[index]
	shot.node.visible = false
	_idle_nodes.append(shot.node)
	_active.remove_at(index)

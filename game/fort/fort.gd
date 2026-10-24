class_name Fort
extends Node3D
## The Castillo: the generated model (tools/blender/build_fort.py) with game materials,
## collision layers, a gun emplacement at every Gun_* marker, and the damage enemy shot does.

signal gun_suppressed(gun: GunPosition)

const FORT_LAYER := 2
const TERRAIN_LAYER := 1
const GUN_NAMES := {
	"SanCarlos": "San Carlos bastion",
	"EastCurtainNorth": "East curtain, north",
	"EastCurtainSouth": "East curtain, south",
	"SanAgustin": "San Agustín bastion",
}
## Guns that start without a crew; the "gun" upgrade mans them.
const LOCKED_GUNS := ["EastCurtainSouth"]
## Fort hit points lost per enemy ball that strikes the walls.
const HIT_DAMAGE := 1.2
## A ball landing this close to a gun sends its crew to cover for SUPPRESS_TIME seconds.
const SUPPRESS_RADIUS := 7.0
const SUPPRESS_TIME := 5.0

@export var gun_scene: PackedScene
@export var dust_fx: PackedScene
## Material slot name in the model -> game material.
@export var materials: Dictionary = {}

@onready var _model: Node3D = $Model
@onready var _guns: Node3D = $GunPositions


func _ready() -> void:
	MaterialMapper.apply(_model, materials)
	_setup_collision()
	_spawn_guns()


func apply_hit(ammo: AmmoDef, _zone: StringName, point: Vector3, normal: Vector3, from_player: bool) -> void:
	if from_player:
		# Our own ball on our own walls: chips the stone, no harm done.
		Fx.spawn(dust_fx, point, normal)
		Audio.play_3d(&"stone_hit", point, -6.0)
		return
	GameState.damage_fort(HIT_DAMAGE * ammo.damage)
	Fx.spawn(dust_fx, point, normal, 1.5)
	Audio.play_3d(&"stone_hit", point, 2.0)
	for child in _guns.get_children():
		var gun := child as GunPosition
		if gun != null and gun.unlocked and gun.global_position.distance_to(point) < SUPPRESS_RADIUS:
			gun.cannon.suppressed_left = SUPPRESS_TIME
			gun_suppressed.emit(gun)


## Mans the locked guns (the "gun" upgrade).
func unlock_guns() -> void:
	for child in _guns.get_children():
		(child as GunPosition).unlocked = true


## Walls are on the fort layer (enemy hits damage the fort); moat and grounds are terrain.
func _setup_collision() -> void:
	for node in _model.find_children("*", "StaticBody3D", true, false):
		var body := node as StaticBody3D
		body.collision_layer = FORT_LAYER if String(body.name).begins_with("FortCollision") else TERRAIN_LAYER
		body.collision_mask = 0


func _spawn_guns() -> void:
	var markers := _model.find_children("Gun_*", "Node3D", true, false)
	markers.sort_custom(func(a: Node, b: Node) -> bool: return String(a.name) < String(b.name))
	for marker in markers:
		var gun := gun_scene.instantiate() as GunPosition
		var key := String(marker.name).get_slice("_", 2)
		gun.display_name = GUN_NAMES.get(key, key)
		gun.unlocked = not LOCKED_GUNS.has(key)
		_guns.add_child(gun)
		gun.global_transform = (marker as Node3D).global_transform

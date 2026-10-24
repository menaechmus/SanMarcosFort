class_name ShipDef
extends Resource
## Tuning for one type of ship. The origin of a ship's model is the waterline at mid-ship.

@export var display_name: String = "Pinnace"
## Optional model scene; a grey-box hull is built from the dimensions below when empty.
@export var model_scene: PackedScene

@export_group("Hull")
@export var length: float = 18.0
@export var beam: float = 5.0
@export var draft: float = 1.6
@export var freeboard: float = 2.0
@export var mast_height: float = 13.0

@export_group("Handling")
## Sailing speed in metres per second.
@export var speed: float = 7.0
@export var max_hp: float = 3.0
@export var sink_time: float = 9.0
## How quickly the hull follows the waves (bigger ships respond more slowly).
@export var wave_response: float = 3.5

@export_group("Rewards")
@export var score: int = 100
@export var bounty: int = 20
## Town damage when this ship gets past the fort.
@export var town_damage: float = 12.0

@export_group("Guns")
@export var guns_per_side: int = 0
@export var gun_range: float = 450.0
@export var gun_reload: float = 12.0

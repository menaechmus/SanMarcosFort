class_name AmmoDef
extends Resource
## A kind of shot: how fast it leaves the muzzle and what it does on impact.

@export var display_name: String = "Round shot"
@export var muzzle_speed: float = 140.0
@export var damage: float = 1.0
## Damage multiplier against masts and sails (chain shot high, round shot low).
@export var rig_multiplier: float = 0.35
## Damage per second a hit adds to a ship's fire (heated shot).
@export var fire_damage: float = 0.0
@export var splash_scale: float = 1.0

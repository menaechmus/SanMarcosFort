class_name WaveEntry
extends Resource
## One group of ships within a wave.

@export var ship: ShipDef
@export var count: int = 3
@export var start_delay: float = 0.0
## Seconds between ships of this group.
@export var interval: float = 8.0
## Lanes (by index) this group may sail; empty means any lane.
@export var lanes: PackedInt32Array = PackedInt32Array()
@export var speed_multiplier: float = 1.0
## Whether ships of this group fire back (if their type carries guns).
@export var armed: bool = true

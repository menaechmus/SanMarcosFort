class_name ShipHealth
extends RefCounted
## Hit points of one ship. Kept free of nodes so the damage rules can be unit-tested.

signal destroyed

## Damage multiplier per hit zone. Waterline hits also open a leak.
const ZONE_MULTIPLIER := {&"hull": 1.0, &"waterline": 1.5, &"rig": 1.0}
## Hit points lost per second for each hole at the waterline.
const LEAK_PER_HOLE := 0.03

var max_hp: float
var hp: float
var leaks: int = 0
## Hit points lost per second to fire (heated shot).
var burning: float = 0.0
var dead: bool = false


func _init(max_hit_points: float) -> void:
	max_hp = max_hit_points
	hp = max_hit_points


func apply(damage: float, zone: StringName) -> void:
	if dead:
		return
	hp -= damage * ZONE_MULTIPLIER.get(zone, 1.0)
	if zone == &"waterline":
		leaks += 1
	_check()


func tick(delta: float) -> void:
	if dead:
		return
	var drain := leaks * LEAK_PER_HOLE + burning
	if drain > 0.0:
		hp -= drain * delta
		_check()


func fraction() -> float:
	return clampf(hp / max_hp, 0.0, 1.0)


func _check() -> void:
	if hp <= 0.0 and not dead:
		hp = 0.0
		dead = true
		destroyed.emit()

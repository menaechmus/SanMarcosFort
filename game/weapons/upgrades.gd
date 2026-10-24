class_name Upgrades
extends RefCounted
## Fort improvements bought between waves: what each level costs and what it does.
## Kept free of nodes so the shop rules can be unit-tested.

const CATALOG := {
	&"reload": {"name": "Drilled gun crews", "costs": [80, 170, 320],
			"desc": "The crews reload faster."},
	&"range": {"name": "Heavier charges", "costs": [100, 230],
			"desc": "More powder: shots fly faster and reach farther."},
	&"accuracy": {"name": "Better gun laying", "costs": [90, 210],
			"desc": "Sights and quoins: shots group tighter."},
	&"chain": {"name": "Chain shot", "costs": [150],
			"desc": "Two balls chained together. Shreds sails and masts and slows ships."},
	&"heated": {"name": "Heated shot", "costs": [260],
			"desc": "Red-hot balls set ships on fire."},
	&"gun": {"name": "Man another gun", "costs": [180],
			"desc": "Crew the south gun on the east curtain."},
}
const REPAIR_COST := 60
const REPAIR_AMOUNT := 20.0

const RELOAD_FACTOR := [1.0, 0.85, 0.72, 0.6]
const SPEED_FACTOR := [1.0, 1.1, 1.2]
const DISPERSION_FACTOR := [1.0, 0.65, 0.4]

var levels: Dictionary = {}


func level(id: StringName) -> int:
	return levels.get(id, 0)


func max_level(id: StringName) -> int:
	return CATALOG[id]["costs"].size()


## Cost of the next level, or -1 when the upgrade is maxed out.
func next_cost(id: StringName) -> int:
	var lv := level(id)
	return -1 if lv >= max_level(id) else CATALOG[id]["costs"][lv]


## Buys the next level if `gold` covers it. Returns the gold left, or -1 if not bought.
func buy(id: StringName, gold: int) -> int:
	var cost := next_cost(id)
	if cost < 0 or cost > gold:
		return -1
	levels[id] = level(id) + 1
	return gold - cost


func reload_factor() -> float:
	return RELOAD_FACTOR[level(&"reload")]


func speed_factor() -> float:
	return SPEED_FACTOR[level(&"range")]


func dispersion_factor() -> float:
	return DISPERSION_FACTOR[level(&"accuracy")]


func has(id: StringName) -> bool:
	return level(id) > 0

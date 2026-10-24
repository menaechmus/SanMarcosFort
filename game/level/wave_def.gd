class_name WaveDef
extends Resource
## One authored wave of ships.

@export var title: String = ""
@export var entries: Array[WaveEntry] = []


## Spawn events sorted by time: {time, ship, lanes, speed, armed}. `extra` adds that many
## ships to every group (used when waves repeat after the authored ones).
func schedule(extra: int = 0) -> Array[Dictionary]:
	var events: Array[Dictionary] = []
	for entry in entries:
		if entry == null or entry.ship == null:
			continue
		for i in entry.count + extra:
			events.append({
				"time": entry.start_delay + i * entry.interval,
				"ship": entry.ship,
				"lanes": entry.lanes,
				"speed": entry.speed_multiplier,
				"armed": entry.armed,
			})
	events.sort_custom(func(a: Dictionary, b: Dictionary) -> bool: return a.time < b.time)
	return events


func ship_count() -> int:
	var total := 0
	for entry in entries:
		if entry != null and entry.ship != null:
			total += entry.count
	return total

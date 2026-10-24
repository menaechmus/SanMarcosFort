extends GutTest


func _entry(ship: ShipDef, count: int, delay: float, interval: float) -> WaveEntry:
	var entry := WaveEntry.new()
	entry.ship = ship
	entry.count = count
	entry.start_delay = delay
	entry.interval = interval
	return entry


func test_schedule_is_sorted_and_complete() -> void:
	var ship := ShipDef.new()
	var wave := WaveDef.new()
	var entries: Array[WaveEntry] = [_entry(ship, 3, 10.0, 5.0), _entry(ship, 2, 0.0, 12.0)]
	wave.entries = entries
	var events := wave.schedule()
	assert_eq(events.size(), 5)
	assert_eq(wave.ship_count(), 5)
	var times := []
	for event in events:
		times.append(event.time)
	assert_eq(times, [0.0, 10.0, 12.0, 15.0, 20.0])


func test_entries_without_ship_are_skipped() -> void:
	var wave := WaveDef.new()
	var entries: Array[WaveEntry] = [_entry(null, 4, 0.0, 1.0)]
	wave.entries = entries
	assert_eq(wave.schedule().size(), 0)
	assert_eq(wave.ship_count(), 0)


func test_authored_waves_load() -> void:
	for path in ["res://game/level/waves/wave_01.tres", "res://game/level/waves/wave_02.tres", "res://game/level/waves/wave_03.tres"]:
		var wave := load(path) as WaveDef
		assert_not_null(wave, path)
		assert_gt(wave.ship_count(), 0, path)

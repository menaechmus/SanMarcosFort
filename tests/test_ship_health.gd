extends GutTest


func test_hull_hits_sink_after_max_hp() -> void:
	var health := ShipHealth.new(3.0)
	watch_signals(health)
	health.apply(1.0, &"hull")
	health.apply(1.0, &"hull")
	assert_false(health.dead)
	health.apply(1.0, &"hull")
	assert_true(health.dead)
	assert_signal_emit_count(health, "destroyed", 1)


func test_destroyed_fires_only_once() -> void:
	var health := ShipHealth.new(1.0)
	watch_signals(health)
	health.apply(5.0, &"hull")
	health.apply(5.0, &"hull")
	health.tick(10.0)
	assert_signal_emit_count(health, "destroyed", 1)


func test_waterline_hits_hurt_more_and_leak() -> void:
	var health := ShipHealth.new(10.0)
	health.apply(1.0, &"waterline")
	assert_almost_eq(health.hp, 8.5, 0.0001)
	assert_eq(health.leaks, 1)
	health.tick(10.0)
	assert_almost_eq(health.hp, 8.5 - 10.0 * ShipHealth.LEAK_PER_HOLE, 0.0001)


func test_leaks_can_sink_a_ship() -> void:
	var health := ShipHealth.new(1.0)
	health.apply(0.5, &"waterline")
	assert_false(health.dead)
	health.tick(60.0)
	assert_true(health.dead)


func test_fire_burns() -> void:
	var health := ShipHealth.new(4.0)
	health.burning = 0.5
	health.tick(2.0)
	assert_almost_eq(health.hp, 3.0, 0.0001)


func test_fraction() -> void:
	var health := ShipHealth.new(4.0)
	health.apply(1.0, &"hull")
	assert_almost_eq(health.fraction(), 0.75, 0.0001)

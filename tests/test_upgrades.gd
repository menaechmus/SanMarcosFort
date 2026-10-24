extends GutTest


func test_buy_spends_gold_and_raises_level() -> void:
	var upgrades := Upgrades.new()
	var cost := upgrades.next_cost(&"reload")
	assert_eq(upgrades.buy(&"reload", cost + 5), 5)
	assert_eq(upgrades.level(&"reload"), 1)


func test_cannot_buy_without_gold() -> void:
	var upgrades := Upgrades.new()
	assert_eq(upgrades.buy(&"heated", 10), -1)
	assert_eq(upgrades.level(&"heated"), 0)


func test_levels_cap_out() -> void:
	var upgrades := Upgrades.new()
	for i in upgrades.max_level(&"range"):
		assert_gt(upgrades.buy(&"range", 100000), -1)
	assert_eq(upgrades.next_cost(&"range"), -1)
	assert_eq(upgrades.buy(&"range", 100000), -1)


func test_factors_improve_with_levels() -> void:
	var upgrades := Upgrades.new()
	var reload0 := upgrades.reload_factor()
	var speed0 := upgrades.speed_factor()
	var spread0 := upgrades.dispersion_factor()
	upgrades.buy(&"reload", 100000)
	upgrades.buy(&"range", 100000)
	upgrades.buy(&"accuracy", 100000)
	assert_lt(upgrades.reload_factor(), reload0)
	assert_gt(upgrades.speed_factor(), speed0)
	assert_lt(upgrades.dispersion_factor(), spread0)


func test_game_state_shop_flow() -> void:
	GameState.start_run()
	GameState.gold = 500
	assert_true(GameState.buy_upgrade(&"chain"))
	assert_eq(GameState.gold, 500 - Upgrades.CATALOG[&"chain"]["costs"][0])
	assert_true(GameState.upgrades.has(&"chain"))
	GameState.fort_hp = 50.0
	assert_true(GameState.repair_fort())
	assert_almost_eq(GameState.fort_hp, 50.0 + Upgrades.REPAIR_AMOUNT, 0.001)
	GameState.reset()

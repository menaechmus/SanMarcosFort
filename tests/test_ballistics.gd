extends GutTest

const G := 9.81
const SPEED := 140.0


func _height_at_distance(x: float, elevation: float) -> float:
	var t := Ballistics.time_of_flight(x, elevation, SPEED)
	return SPEED * sin(elevation) * t - 0.5 * G * t * t


func test_solution_lands_on_target() -> void:
	for x in [80.0, 200.0, 450.0, 700.0]:
		for y in [-12.0, -8.0, 0.0, 3.0]:
			var elevation := Ballistics.solve_elevation(x, y, SPEED, G)
			assert_false(is_nan(elevation), "solvable at %s m, height %s" % [x, y])
			assert_almost_eq(_height_at_distance(x, elevation), y, 0.5)


func test_unreachable_target_is_nan() -> void:
	assert_true(is_nan(Ballistics.solve_elevation(5000.0, 0.0, SPEED, G)))
	assert_true(is_nan(Ballistics.solve_elevation(0.0, 0.0, SPEED, G)))


func test_low_arc_is_chosen() -> void:
	var elevation := Ballistics.solve_elevation(400.0, -10.0, SPEED, G)
	assert_lt(elevation, deg_to_rad(10.0))


func test_range_at_matches_solver() -> void:
	var elevation := deg_to_rad(6.0)
	var drop := 10.0
	var x := Ballistics.range_at(elevation, SPEED, G, drop)
	assert_almost_eq(Ballistics.solve_elevation(x, -drop, SPEED, G), elevation, 0.0005)


func test_position_at_follows_parabola() -> void:
	var p := Ballistics.position_at(Vector3(1, 2, 3), Vector3(10, 20, 0), G, 2.0)
	assert_almost_eq(p.x, 21.0, 0.0001)
	assert_almost_eq(p.y, 2.0 + 40.0 - 0.5 * G * 4.0, 0.0001)
	assert_almost_eq(p.z, 3.0, 0.0001)


func test_lead_point_intercepts_moving_target() -> void:
	var origin := Vector3(0, 12, 0)
	var target := Vector3(350, 1, -60)
	var velocity := Vector3(0, 0, 6)
	var aim := Ballistics.lead_point(origin, target, velocity, SPEED, G)
	var flat := Vector2(aim.x - origin.x, aim.z - origin.z).length()
	var elevation := Ballistics.solve_elevation(flat, aim.y - origin.y, SPEED, G)
	var t := Ballistics.time_of_flight(flat, elevation, SPEED)
	var target_then := target + velocity * t
	assert_almost_eq(aim.distance_to(target_then), 0.0, 1.0)

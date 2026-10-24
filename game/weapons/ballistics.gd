class_name Ballistics
extends RefCounted
## Drag-free projectile math shared by gun laying, the aim marker and the autoplay bot.
## Without drag the parabola is exact, so the marker shows where a ball really lands.


## Low-arc launch elevation (radians) to hit a point at horizontal distance `x` and height
## `y` relative to the launch point, at muzzle speed `v`. Returns NAN when out of reach.
static func solve_elevation(x: float, y: float, v: float, g: float) -> float:
	if x < 0.01:
		return NAN
	var v2 := v * v
	var disc := v2 * v2 - g * (g * x * x + 2.0 * y * v2)
	if disc < 0.0:
		return NAN
	return atan((v2 - sqrt(disc)) / (g * x))


static func time_of_flight(x: float, elevation: float, v: float) -> float:
	return x / maxf(v * cos(elevation), 0.001)


## Horizontal distance covered by the time the ball has dropped `drop` metres below the
## launch point.
static func range_at(elevation: float, v: float, g: float, drop: float) -> float:
	var vx := v * cos(elevation)
	var vy := v * sin(elevation)
	var t := (vy + sqrt(maxf(vy * vy + 2.0 * g * drop, 0.0))) / g
	return vx * t


static func position_at(origin: Vector3, velocity: Vector3, g: float, t: float) -> Vector3:
	return origin + velocity * t + Vector3(0.0, -0.5 * g * t * t, 0.0)


## Aim point that intercepts a target moving at constant velocity, refined a few times.
static func lead_point(origin: Vector3, target: Vector3, target_velocity: Vector3, v: float, g: float, iterations: int = 4) -> Vector3:
	var aim := target
	for _i in iterations:
		var flat := Vector2(aim.x - origin.x, aim.z - origin.z).length()
		var elevation := solve_elevation(flat, aim.y - origin.y, v, g)
		if is_nan(elevation):
			return aim
		aim = target + target_velocity * time_of_flight(flat, elevation, v)
	return aim

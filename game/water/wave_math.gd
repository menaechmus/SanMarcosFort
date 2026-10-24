class_name WaveMath
extends RefCounted
## CPU mirror of the Gerstner displacement in water.gdshader. Keep the two in sync.

## Wave set of the running level (assigned by WaterSurface).
static var current: WaveSet


## Displacement of the surface point whose rest (undisplaced) position is (x, z).
static func displace(ws: WaveSet, x: float, z: float, t: float) -> Vector3:
	var c := ws.get_cache()
	var fade := ws.fade_at(x, z)
	var out := Vector3.ZERO
	var i := 0
	while i < c.size():
		var k := c[i + 2]
		var a := c[i + 4] * fade / k
		var f := k * (c[i] * x + c[i + 1] * z) - c[i + 3] * t
		var cf := cos(f)
		out.x += c[i] * a * cf
		out.y += a * sin(f)
		out.z += c[i + 1] * a * cf
		i += WaveSet.STRIDE
	return out


## Rest position whose displaced position lands on (x, z). Inverts the sideways Gerstner
## motion by fixed-point iteration, which converges while total steepness is below 1.
static func rest_point(ws: WaveSet, x: float, z: float, t: float, iterations: int = 4) -> Vector2:
	var p := Vector2(x, z)
	for _i in iterations:
		var d := displace(ws, p.x, p.y, t)
		p = Vector2(x - d.x, z - d.z)
	return p


## Water surface height at world position (x, z) at time t.
static func height_at(ws: WaveSet, x: float, z: float, t: float) -> float:
	var p := rest_point(ws, x, z, t)
	return displace(ws, p.x, p.y, t).y


## Height of the running level's water at (x, z), at the current game time.
static func height(x: float, z: float) -> float:
	if current == null:
		return 0.0
	return height_at(current, x, z, GameClock.time)

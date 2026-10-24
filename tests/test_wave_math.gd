extends GutTest

var waves: WaveSet


func _wave(direction: float, wavelength: float, steepness: float) -> GerstnerWave:
	var wave := GerstnerWave.new()
	wave.direction_deg = direction
	wave.wavelength = wavelength
	wave.steepness = steepness
	return wave


func before_each() -> void:
	waves = WaveSet.new()
	var list: Array[GerstnerWave] = [
		_wave(195.0, 55.0, 0.06),
		_wave(222.0, 31.0, 0.07),
		_wave(168.0, 19.0, 0.06),
		_wave(246.0, 13.0, 0.05),
	]
	waves.waves = list


func test_rest_point_maps_back_onto_the_query() -> void:
	var rng := RandomNumberGenerator.new()
	rng.seed = 42
	for i in 50:
		var x := rng.randf_range(-800.0, 800.0)
		var z := rng.randf_range(-800.0, 800.0)
		var t := rng.randf_range(0.0, 600.0)
		var rest := WaveMath.rest_point(waves, x, z, t)
		var d := WaveMath.displace(waves, rest.x, rest.y, t)
		assert_almost_eq(rest.x + d.x, x, 0.05, "x at sample %d" % i)
		assert_almost_eq(rest.y + d.z, z, 0.05, "z at sample %d" % i)


func test_height_stays_within_total_amplitude() -> void:
	var amplitude := 0.0
	for wave in waves.waves:
		amplitude += wave.steepness * wave.wavelength / TAU
	for i in 40:
		var h := WaveMath.height_at(waves, i * 37.0, i * -23.0, i * 1.7)
		assert_lt(absf(h), amplitude + 0.001)


func test_waves_move_over_time() -> void:
	var a := WaveMath.height_at(waves, 120.0, 40.0, 0.0)
	var b := WaveMath.height_at(waves, 120.0, 40.0, 1.3)
	assert_ne(a, b)


func test_far_water_is_flat() -> void:
	assert_almost_eq(WaveMath.height_at(waves, waves.fade_end + 50.0, 0.0, 12.0), 0.0, 0.0001)


func test_no_waves_means_flat() -> void:
	var empty := WaveSet.new()
	assert_eq(WaveMath.height_at(empty, 10.0, 10.0, 5.0), 0.0)

shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_disabled;

// Period flags drawn from UV (u along the fly, v down from the head), waving in the wind.
// pattern: 0 St George's cross (England), 1 Burgundy cross (Spain), 2 black (pirates),
// 3 red ("no quarter"), 4 Prince's flag (Dutch: orange, white, blue).
uniform int pattern = 0;
uniform float wave_amount = 0.35;

void vertex() {
	float w = sin(TIME * 5.0 - UV.x * 7.0) * 0.6 + sin(TIME * 7.3 - UV.x * 11.0 + UV.y * 2.0) * 0.4;
	VERTEX.x += w * wave_amount * UV.x;
}

vec3 flag_color(vec2 uv) {
	vec3 white = vec3(0.92, 0.9, 0.86);
	vec3 red = vec3(0.7, 0.08, 0.08);
	if (pattern == 0) {
		bool cross = abs(uv.x - 0.5) < 0.09 || abs(uv.y - 0.5) < 0.14;
		return cross ? red : white;
	} else if (pattern == 1) {
		// Ragged saltire: two diagonals with a knotted (raguly) edge.
		float d1 = abs(uv.y - uv.x);
		float d2 = abs(uv.y - (1.0 - uv.x));
		float knots = 0.02 * step(0.5, fract((uv.x + uv.y) * 9.0));
		return (min(d1, d2) < 0.065 + knots) ? red : white;
	} else if (pattern == 2) {
		return vec3(0.05, 0.05, 0.05);
	} else if (pattern == 3) {
		return red;
	}
	if (uv.y < 0.333) {
		return vec3(0.9, 0.45, 0.08);
	}
	return uv.y < 0.666 ? white : vec3(0.1, 0.2, 0.55);
}

void fragment() {
	ALBEDO = flag_color(UV);
	ROUGHNESS = 0.9;
	SPECULAR = 0.15;
}

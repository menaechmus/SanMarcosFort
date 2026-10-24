shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_disabled;

// Canvas sails: woven texture, vertical panel seams, weathering toward the foot, and a gentle
// flutter. UV is in sail metres / 1.5 (from tools/blender/build_ships.py).
uniform sampler2D canvas_albedo : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D canvas_normal : hint_normal, filter_linear_mipmap, repeat_enable;
uniform vec3 tint : source_color = vec3(0.93, 0.88, 0.76);
uniform float seam_spacing = 0.5;
uniform float flutter = 0.05;

void vertex() {
	float wave = sin(TIME * 2.3 + UV.x * 2.1 + UV.y * 1.3) + 0.5 * sin(TIME * 3.7 + UV.y * 3.0);
	VERTEX += NORMAL * wave * flutter * clamp(UV.y * 0.6, 0.0, 1.0);
}

void fragment() {
	vec3 cloth = texture(canvas_albedo, UV * 0.6).rgb;
	float seam = smoothstep(0.92, 0.98, fract(UV.x / seam_spacing));
	float weather = mix(1.0, 0.82, clamp(UV.y * 0.25, 0.0, 1.0));
	ALBEDO = tint * mix(0.9, 1.1, cloth.r) * (1.0 - seam * 0.25) * weather;
	NORMAL_MAP = texture(canvas_normal, UV * 0.6).rgb;
	NORMAL_MAP_DEPTH = 0.5;
	ROUGHNESS = 0.9;
	SPECULAR = 0.2;
}

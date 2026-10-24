shader_type spatial;
render_mode blend_mix, depth_draw_always, cull_back, specular_schlick_ggx;

// Gerstner waves. The CPU mirror is game/water/wave_math.gd: keep the two in sync.
// Each wave is vec4(direction x, direction z, wavenumber k, steepness).
global uniform float water_time;

uniform vec4 wave_0 = vec4(1.0, 0.0, 1.0, 0.0);
uniform vec4 wave_1 = vec4(1.0, 0.0, 1.0, 0.0);
uniform vec4 wave_2 = vec4(1.0, 0.0, 1.0, 0.0);
uniform vec4 wave_3 = vec4(1.0, 0.0, 1.0, 0.0);
uniform vec4 wave_4 = vec4(1.0, 0.0, 1.0, 0.0);
uniform vec4 wave_5 = vec4(1.0, 0.0, 1.0, 0.0);
uniform float gravity = 9.81;
uniform vec2 fade_center = vec2(0.0);
uniform float fade_start = 1300.0;
uniform float fade_end = 2200.0;

group_uniforms color;
uniform vec3 deep_color : source_color = vec3(0.02, 0.10, 0.12);
uniform vec3 shallow_color : source_color = vec3(0.09, 0.33, 0.31);
uniform vec3 foam_color : source_color = vec3(0.90, 0.93, 0.92);
// Metres of water that absorb most light: smaller = murkier.
uniform float absorption_depth = 4.0;
uniform float min_alpha : hint_range(0.0, 1.0) = 0.6;
uniform float roughness_value : hint_range(0.0, 1.0) = 0.06;

group_uniforms ripples;
uniform sampler2D ripple_a : hint_normal, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D ripple_b : hint_normal, filter_linear_mipmap_anisotropic, repeat_enable;
uniform float ripple_scale_a = 0.035;
uniform float ripple_scale_b = 0.09;
uniform vec2 ripple_speed_a = vec2(0.010, 0.006);
uniform vec2 ripple_speed_b = vec2(-0.007, 0.011);
uniform float ripple_strength = 0.35;

group_uniforms foam;
uniform sampler2D foam_noise : filter_linear_mipmap, repeat_enable;
uniform float foam_scale = 0.08;
uniform float shore_foam_depth = 1.5;
uniform float crest_foam = 0.55;

group_uniforms;
uniform sampler2D depth_tex : hint_depth_texture, filter_linear;

varying vec3 world_pos;
varying vec3 world_normal;
varying float crest;

void add_wave(vec4 w, vec2 xz, float fade, inout vec3 disp, inout vec3 tangent, inout vec3 binormal, inout float amp_sum) {
	float k = max(w.z, 0.0001);
	float s = w.w * fade;
	float a = s / k;
	float f = k * dot(w.xy, xz) - sqrt(gravity * k) * water_time;
	float sf = sin(f);
	float cf = cos(f);
	disp += vec3(w.x * a * cf, a * sf, w.y * a * cf);
	tangent += vec3(-w.x * w.x * s * sf, w.x * s * cf, -w.x * w.y * s * sf);
	binormal += vec3(-w.x * w.y * s * sf, w.y * s * cf, -w.y * w.y * s * sf);
	amp_sum += a;
}

void vertex() {
	// The water mesh is placed with an identity basis, so model space is world space shifted.
	vec3 p = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	float fade = 1.0 - smoothstep(fade_start, fade_end, length(p.xz - fade_center));
	vec3 disp = vec3(0.0);
	vec3 tangent = vec3(1.0, 0.0, 0.0);
	vec3 binormal = vec3(0.0, 0.0, 1.0);
	float amp_sum = 0.0001;
	add_wave(wave_0, p.xz, fade, disp, tangent, binormal, amp_sum);
	add_wave(wave_1, p.xz, fade, disp, tangent, binormal, amp_sum);
	add_wave(wave_2, p.xz, fade, disp, tangent, binormal, amp_sum);
	add_wave(wave_3, p.xz, fade, disp, tangent, binormal, amp_sum);
	add_wave(wave_4, p.xz, fade, disp, tangent, binormal, amp_sum);
	add_wave(wave_5, p.xz, fade, disp, tangent, binormal, amp_sum);
	VERTEX += disp;
	world_pos = p + disp;
	world_normal = normalize(cross(binormal, tangent));
	NORMAL = world_normal;
	crest = clamp(disp.y / amp_sum, -1.0, 1.0);
}

void fragment() {
	// Fine ripples from two scrolling normal maps, faded with distance to avoid shimmer.
	float view_dist = length(VERTEX);
	float ripple_fade = 1.0 - smoothstep(150.0, 1400.0, view_dist);
	vec2 ra = texture(ripple_a, world_pos.xz * ripple_scale_a + ripple_speed_a * water_time).xy * 2.0 - 1.0;
	vec2 rb = texture(ripple_b, world_pos.xz * ripple_scale_b + ripple_speed_b * water_time).xy * 2.0 - 1.0;
	vec2 ripple = (ra + rb) * ripple_strength * ripple_fade;
	vec3 n = normalize(world_normal + vec3(ripple.x, 0.0, ripple.y));
	NORMAL = normalize((VIEW_MATRIX * vec4(n, 0.0)).xyz);

	// Water thickness behind this pixel, from the depth buffer: drives colour and shore foam.
	float raw_depth = texture(depth_tex, SCREEN_UV).r;
#if CURRENT_RENDERER == RENDERER_COMPATIBILITY
	vec3 ndc = vec3(SCREEN_UV * 2.0 - 1.0, raw_depth * 2.0 - 1.0);
#else
	vec3 ndc = vec3(SCREEN_UV * 2.0 - 1.0, raw_depth);
#endif
	vec4 scene_view = INV_PROJECTION_MATRIX * vec4(ndc, 1.0);
	float scene_depth = -scene_view.z / scene_view.w;
	float thickness = max(scene_depth + VERTEX.z, 0.0);
	float absorb = 1.0 - exp(-thickness / absorption_depth);

	float foam_tex = texture(foam_noise, world_pos.xz * foam_scale + vec2(water_time * 0.01)).r;
	float shore = (1.0 - smoothstep(0.0, shore_foam_depth, thickness)) * foam_tex;
	float crest_mask = smoothstep(0.6, 1.0, crest) * crest_foam * foam_tex;
	float foam = clamp(max(shore, crest_mask), 0.0, 1.0);

	vec3 body = mix(shallow_color, deep_color, absorb);
	ALBEDO = mix(body, foam_color, foam);
	ROUGHNESS = mix(roughness_value, 0.7, foam);
	METALLIC = 0.0;
	SPECULAR = 0.5;
	ALPHA = clamp(mix(min_alpha, 1.0, absorb) + foam, 0.0, 1.0);
}

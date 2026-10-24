shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_back;

// Fort masonry: weathered coquina blocks (today's look) or lime plaster (the Spanish look),
// switched by the global `fort_plaster` (Settings). Vertex colour from the generator:
// R = grime / occlusion, G = old plaster that survives in today's look.
global uniform float fort_plaster;

group_uniforms stone;
uniform sampler2D stone_albedo : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D stone_normal : hint_normal, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D stone_roughness : hint_default_white, filter_linear_mipmap, repeat_enable;
uniform vec3 stone_tint : source_color = vec3(0.86, 0.84, 0.80);
uniform float stone_uv_scale = 1.0;

group_uniforms plaster;
uniform sampler2D plaster_albedo : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D plaster_normal : hint_normal, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D plaster_roughness : hint_default_white, filter_linear_mipmap, repeat_enable;
// White lime wash on walls; dark red on the sentry boxes.
uniform vec3 plaster_tint : source_color = vec3(0.96, 0.95, 0.91);
uniform float plaster_uv_scale = 0.7;
// How much of the remnant-plaster mask shows in today's look.
uniform float remnant_strength : hint_range(0.0, 1.0) = 0.8;

group_uniforms;
uniform float grime_strength : hint_range(0.0, 1.0) = 0.5;

void fragment() {
	vec2 suv = UV * stone_uv_scale;
	vec2 puv = UV * plaster_uv_scale;
	float remnant = COLOR.g * remnant_strength;
	float plastered = clamp(max(fort_plaster, remnant), 0.0, 1.0);

	vec3 stone = texture(stone_albedo, suv).rgb * stone_tint;
	vec3 plaster = texture(plaster_albedo, puv).rgb * plaster_tint;
	float grime = mix(1.0 - grime_strength, 1.0, COLOR.r);
	ALBEDO = mix(stone, plaster, plastered) * grime;

	NORMAL_MAP = mix(texture(stone_normal, suv).rgb, texture(plaster_normal, puv).rgb, plastered);
	ROUGHNESS = mix(texture(stone_roughness, suv).r, texture(plaster_roughness, puv).r * 0.9, plastered);
	SPECULAR = 0.35;
	AO = mix(0.75, 1.0, COLOR.r);
	AO_LIGHT_AFFECT = 0.3;
}

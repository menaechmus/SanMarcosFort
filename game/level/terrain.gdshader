shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_back;

// Land around the bay: sand and grass blended by vertex colour from the generator
// (R sand, G grass, B wet), with a large-scale variation that hides texture tiling.
uniform sampler2D sand_albedo : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D sand_normal : hint_normal, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D grass_albedo : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D grass_normal : hint_normal, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D macro_noise : filter_linear_mipmap, repeat_enable;
uniform float sand_scale = 0.8;
uniform float grass_scale = 1.0;
uniform float macro_scale = 0.004;
uniform vec3 wet_tint : source_color = vec3(0.55, 0.5, 0.42);
// The grass texture is dry turf; tint it toward the green of a Florida summer.
uniform vec3 grass_tint : source_color = vec3(0.74, 0.92, 0.56);
// Models whose vertex colours mean something else (the fort's grounds and moat) set a fixed
// (sand, grass, wet) mix here instead; negative x means "use the vertex colour".
uniform vec3 fixed_mix = vec3(-1.0, 0.0, 0.0);
uniform float brightness = 1.0;

varying vec3 world_pos;

void vertex() {
	world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	vec3 mixw = fixed_mix.x < 0.0 ? COLOR.rgb : fixed_mix;
	float macro = texture(macro_noise, world_pos.xz * macro_scale).r;
	vec3 sand = texture(sand_albedo, UV * sand_scale).rgb;
	vec3 grass = texture(grass_albedo, UV * grass_scale).rgb * grass_tint;
	float g = clamp(mixw.g + (macro - 0.5) * 0.25, 0.0, 1.0);
	vec3 albedo = mix(sand, grass, g) * mix(0.85, 1.12, macro) * brightness;
	albedo = mix(albedo, albedo * wet_tint, mixw.b);
	ALBEDO = albedo;
	NORMAL_MAP = mix(texture(sand_normal, UV * sand_scale).rgb, texture(grass_normal, UV * grass_scale).rgb, g);
	ROUGHNESS = mix(0.95, 0.55, mixw.b);
	SPECULAR = 0.3;
}

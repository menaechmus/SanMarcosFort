shader_type sky;

// Florida sky: gradient, sun disk and glow, and a static layer of fair-weather cumulus.
// Static on purpose: a sky that uses TIME re-renders the reflection probe every frame.
uniform vec3 zenith_color : source_color = vec3(0.16, 0.36, 0.72);
uniform vec3 horizon_color : source_color = vec3(0.64, 0.75, 0.88);
// Below the horizon: stands in for light bounced off the sunlit ground and water. Walls in
// shade and surfaces seen at grazing angles take much of their light from it.
uniform vec3 ground_color : source_color = vec3(0.42, 0.42, 0.38);
uniform vec3 cloud_color : source_color = vec3(1.0, 0.98, 0.95);
uniform vec3 cloud_shade : source_color = vec3(0.62, 0.66, 0.74);
uniform sampler2D cloud_noise : filter_linear_mipmap, repeat_enable;
uniform float cloud_coverage : hint_range(0.0, 1.0) = 0.52;
uniform float cloud_scale = 0.12;
uniform float sun_size = 0.9994;

void sky() {
	vec3 dir = EYEDIR;
	float h = dir.y;
	vec3 color = mix(horizon_color, zenith_color, pow(clamp(h, 0.0, 1.0), 0.45));
	if (h < 0.0) {
		color = mix(horizon_color, ground_color, clamp(-h * 6.0, 0.0, 1.0));
	}
	float sun_dot = dot(dir, LIGHT0_DIRECTION);
	color += LIGHT0_COLOR * pow(max(sun_dot, 0.0), 300.0) * 0.6;
	if (!AT_CUBEMAP_PASS && h > 0.0) {
		vec2 uv = dir.xz / (h + 0.08) * cloud_scale;
		float n = texture(cloud_noise, uv).r * 0.65 + texture(cloud_noise, uv * 2.7 + vec2(0.31, 0.17)).r * 0.35;
		float cover = smoothstep(cloud_coverage, cloud_coverage + 0.22, n) * smoothstep(0.0, 0.12, h);
		float lit = clamp(0.55 + 0.45 * sun_dot, 0.0, 1.0);
		vec3 cloud = mix(cloud_shade, cloud_color, lit * smoothstep(cloud_coverage, cloud_coverage + 0.4, n));
		color = mix(color, cloud, cover * 0.92);
	}
	if (sun_dot > sun_size) {
		color = mix(color, LIGHT0_COLOR * 4.0, smoothstep(sun_size, sun_size + 0.0003, sun_dot));
	}
	COLOR = color;
}

extends Node
## Player settings (graphics quality, fort look, aim assist), saved to user://settings.cfg.
## Also defines the input actions, so the whole input map lives in one place.

signal changed

enum Quality { LOW, MEDIUM, HIGH }

const SAVE_PATH := "user://settings.cfg"
const WATER_GRID := [128, 200, 280]
const MSAA := [Viewport.MSAA_DISABLED, Viewport.MSAA_2X, Viewport.MSAA_4X]
const RENDER_SCALE := [0.75, 0.9, 1.0]
const SHADOW_SIZE := [2048, 4096, 4096]
## Ships are far off and small, so their shadows are the first thing to go on phones.
const SHIP_SHADOWS := [false, true, true]

var quality: Quality = Quality.MEDIUM
## Original Spanish look (white plaster, red sentry boxes) instead of today's bare coquina.
var fort_plaster: bool = false
var aim_assist: bool = true
var master_volume: float = 0.8


func _ready() -> void:
	_register_actions()
	quality = default_quality()
	load_settings()
	apply()


static func default_quality() -> Quality:
	if OS.has_feature("mobile") or OS.has_feature("web_android") or OS.has_feature("web_ios"):
		return Quality.LOW
	if OS.has_feature("web"):
		return Quality.MEDIUM
	return Quality.HIGH


func water_grid_resolution() -> int:
	return WATER_GRID[quality]


func apply() -> void:
	RenderingServer.global_shader_parameter_set(&"fort_plaster", 1.0 if fort_plaster else 0.0)
	var viewport := get_viewport()
	viewport.msaa_3d = MSAA[quality]
	viewport.scaling_3d_scale = RENDER_SCALE[quality]
	RenderingServer.directional_shadow_atlas_set_size(SHADOW_SIZE[quality], true)
	AudioServer.set_bus_volume_db(0, linear_to_db(maxf(master_volume, 0.0001)))
	changed.emit()


func load_settings() -> void:
	var cfg := ConfigFile.new()
	if cfg.load(SAVE_PATH) != OK:
		return
	quality = clampi(cfg.get_value("graphics", "quality", quality), 0, 2) as Quality
	fort_plaster = cfg.get_value("graphics", "fort_plaster", fort_plaster)
	aim_assist = cfg.get_value("gameplay", "aim_assist", aim_assist)
	master_volume = cfg.get_value("audio", "master_volume", master_volume)


func save_settings() -> void:
	var cfg := ConfigFile.new()
	cfg.set_value("graphics", "quality", quality)
	cfg.set_value("graphics", "fort_plaster", fort_plaster)
	cfg.set_value("gameplay", "aim_assist", aim_assist)
	cfg.set_value("audio", "master_volume", master_volume)
	cfg.save(SAVE_PATH)


func _register_actions() -> void:
	_action(&"fire", [_mouse(MOUSE_BUTTON_LEFT), _key(KEY_F), _key(KEY_ENTER)])
	_action(&"next_gun", [_key(KEY_TAB), _key(KEY_E)])
	_action(&"prev_gun", [_key(KEY_Q)])
	for i in 6:
		_action(StringName("gun_%d" % (i + 1)), [_key((KEY_1 + i) as Key)])
	_action(&"spyglass", [_key(KEY_SPACE)])
	_action(&"ammo_next", [_key(KEY_R)])
	_action(&"zoom_in", [_mouse(MOUSE_BUTTON_WHEEL_UP), _key(KEY_EQUAL)])
	_action(&"zoom_out", [_mouse(MOUSE_BUTTON_WHEEL_DOWN), _key(KEY_MINUS)])
	_action(&"pan_left", [_key(KEY_A), _key(KEY_LEFT)])
	_action(&"pan_right", [_key(KEY_D), _key(KEY_RIGHT)])
	_action(&"pan_up", [_key(KEY_W), _key(KEY_UP)])
	_action(&"pan_down", [_key(KEY_S), _key(KEY_DOWN)])
	_action(&"pause", [_key(KEY_ESCAPE), _key(KEY_P)])


func _action(action: StringName, events: Array) -> void:
	if InputMap.has_action(action):
		return
	InputMap.add_action(action)
	for event: InputEvent in events:
		InputMap.action_add_event(action, event)


func _key(code: Key) -> InputEventKey:
	var event := InputEventKey.new()
	event.physical_keycode = code
	return event


func _mouse(button: MouseButton) -> InputEventMouseButton:
	var event := InputEventMouseButton.new()
	event.button_index = button
	return event

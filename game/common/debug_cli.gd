extends Node
## Command-line hooks for automated checks. Pass them after `--`, for example:
##   godot --path . -- --capture=build/shots/gun2.png --frames=240 --cam=gun:1
##   godot --headless --fixed-fps 60 --path . -- --autoplay --quit-after-sec=300
## --capture=<png>       save a screenshot after --frames rendered frames (default 180), print
##                       frame rate and rendering counts, then quit (add --disable-vsync before
##                       `--` to measure the frame rate)
## --cam=<name>          view from a CameraBookmarks marker, or gun:<n> for gun position n
## --autoplay            a bot aims at the nearest ship and fires
## --quit-after-sec=<s>  quit after s seconds of game time, printing a report
## --timescale=<x>       Engine.time_scale
## --shop                start a run with the shop open (with some gold), for screenshots
## --start               skip the title screen (without the autoplay bot)
## --wave=<n>            the first wave started is wave n
## --quality=<preset>    low, medium or high for this run (not saved)

## Frames rendered before the frame-rate measurement starts (shader compiles, loading).
const WARMUP_FRAMES := 60

var options: Dictionary = {}
var autoplay: bool = false

var _frames: int = 0
var _timing_start_usec: int = 0
var _capture_frames: int = 180
var _done: bool = false


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	for arg in OS.get_cmdline_user_args():
		if not arg.begins_with("--"):
			continue
		var parts := arg.substr(2).split("=", true, 1)
		options[parts[0]] = parts[1] if parts.size() > 1 else "true"
	autoplay = options.has("autoplay")
	_capture_frames = int(options.get("frames", "180"))
	if options.has("timescale"):
		Engine.time_scale = float(options["timescale"])
	if options.has("quality"):
		var preset := Settings.Quality.keys().find(String(options["quality"]).to_upper())
		if preset < 0:
			push_error("--quality must be low, medium or high")
		else:
			Settings.quality = preset as Settings.Quality
			Settings.apply()
	if autoplay:
		GameState.phase_changed.connect(_autoplay_shop)


## Autoplay in the shop: buy what the gold allows (cheapest useful first), repair, sail on.
func _autoplay_shop(phase: GameState.Phase) -> void:
	if phase != GameState.Phase.SHOP:
		return
	if GameState.fort_hp < 70.0:
		GameState.repair_fort()
	for id: StringName in [&"reload", &"range", &"accuracy", &"gun", &"reload", &"range", &"accuracy", &"reload"]:
		GameState.buy_upgrade(id)
	GameState.close_shop.call_deferred()


func camera_bookmark() -> String:
	return options.get("cam", "")


func _process(_delta: float) -> void:
	if _done:
		return
	_frames += 1
	if _frames == WARMUP_FRAMES:
		_timing_start_usec = Time.get_ticks_usec()
	if options.has("capture") and _frames >= _capture_frames:
		_done = true
		_capture(options["capture"])
		_print_stats()
		_quit()
	elif options.has("quit-after-sec") and GameClock.time >= float(options["quit-after-sec"]):
		_done = true
		_quit()


func _capture(path: String) -> void:
	var image := get_viewport().get_texture().get_image()
	var target := path if path.is_absolute_path() else ProjectSettings.globalize_path("res://").path_join(path)
	DirAccess.make_dir_recursive_absolute(target.get_base_dir())
	# Screenshots usually land in build/; keep Godot from importing them as assets.
	var build_dir := ProjectSettings.globalize_path("res://build")
	if target.begins_with(build_dir) and not FileAccess.file_exists(build_dir.path_join(".gdignore")):
		FileAccess.open(build_dir.path_join(".gdignore"), FileAccess.WRITE)
	var err := image.save_png(target)
	print("[capture] %s -> %s" % [target, error_string(err)])


## Frame rate since the warm-up, and what the last frame drew (shadow passes included).
func _print_stats() -> void:
	var seconds := (Time.get_ticks_usec() - _timing_start_usec) / 1000000.0
	var fps := (_frames - WARMUP_FRAMES) / seconds if _frames > WARMUP_FRAMES else 0.0
	print("[stats] quality=%s fps=%.0f draw_calls=%d triangles=%d objects=%d video_mem=%.0fMB textures=%.0fMB" % [
		Settings.Quality.keys()[Settings.quality].to_lower(), fps,
		RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_DRAW_CALLS_IN_FRAME),
		RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_PRIMITIVES_IN_FRAME),
		RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_OBJECTS_IN_FRAME),
		RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_VIDEO_MEM_USED) / 1048576.0,
		RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TEXTURE_MEM_USED) / 1048576.0])


func _quit() -> void:
	print("[report] time=%.1fs wave=%d score=%d sunk=%d escaped=%d shots=%d hits=%d town=%.0f fort=%.0f" % [
		GameClock.time, GameState.wave, GameState.score, GameState.ships_sunk, GameState.ships_escaped,
		GameState.shots_fired, GameState.shots_hit, GameState.town_damage, GameState.fort_hp])
	# The mixer drops stopped playbacks on its next pass (on the audio thread, so wait in real
	# time) and the main loop frees them a frame later; quitting sooner reports them as leaked.
	get_tree().paused = true
	Audio.stop_all()
	OS.delay_msec(60)
	await get_tree().process_frame
	await get_tree().process_frame
	get_tree().quit()

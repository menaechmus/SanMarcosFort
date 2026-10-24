extends Node
## Plays the game's sounds (synthesized by tools/synth_audio.py): positional one-shots from a
## pool of 3D players, non-positional cues, and the sea ambience with the odd gull overhead.

const SOUNDS := {
	&"cannon": preload("res://assets/audio/cannon.wav"),
	&"cannon_far": preload("res://assets/audio/cannon_far.wav"),
	&"splash": preload("res://assets/audio/splash.wav"),
	&"wood_hit": preload("res://assets/audio/wood_hit.wav"),
	&"stone_hit": preload("res://assets/audio/stone_hit.wav"),
	&"whistle": preload("res://assets/audio/whistle.wav"),
	&"bell": preload("res://assets/audio/bell.wav"),
	&"gull": preload("res://assets/audio/gull.wav"),
	&"creak": preload("res://assets/audio/creak.wav"),
	&"click": preload("res://assets/audio/click.wav"),
}
const SEA := preload("res://assets/audio/sea_loop.wav")
const POOL_SIZE := 24

var _pool: Array[AudioStreamPlayer3D] = []
var _next: int = 0
var _ui: AudioStreamPlayer
var _gull_left: float = 6.0


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	for i in POOL_SIZE:
		var player := AudioStreamPlayer3D.new()
		player.unit_size = 28.0
		player.max_distance = 4000.0
		player.max_db = 4.0
		add_child(player)
		_pool.append(player)
	_ui = AudioStreamPlayer.new()
	add_child(_ui)
	var sea := AudioStreamPlayer.new()
	sea.stream = SEA
	sea.volume_db = -13.0
	add_child(sea)
	sea.play()


## Plays `sound` at a world position. Pitch varies a little so repeats don't sound identical.
func play_3d(sound: StringName, position: Vector3, volume_db: float = 0.0, pitch_jitter: float = 0.06) -> void:
	var player := _pool[_next]
	_next = (_next + 1) % POOL_SIZE
	player.stream = SOUNDS[sound]
	player.global_position = position
	player.volume_db = volume_db
	player.pitch_scale = 1.0 + randf_range(-pitch_jitter, pitch_jitter)
	player.play()


## Silences everything and stops the gulls (before quitting, so no playback is left at exit).
func stop_all() -> void:
	set_process(false)
	for node in get_tree().root.find_children("*", "", true, false):
		if node is AudioStreamPlayer or node is AudioStreamPlayer3D:
			node.stop()


func play_ui(sound: StringName, volume_db: float = -8.0) -> void:
	_ui.stream = SOUNDS[sound]
	_ui.volume_db = volume_db
	_ui.play()


func _process(delta: float) -> void:
	_gull_left -= delta
	if _gull_left > 0.0:
		return
	_gull_left = randf_range(7.0, 18.0)
	var camera := get_viewport().get_camera_3d()
	if camera != null:
		var offset := Vector3(randf_range(40.0, 260.0), randf_range(20.0, 60.0), randf_range(-200.0, 200.0))
		play_3d(&"gull", camera.global_position + offset, -6.0, 0.12)

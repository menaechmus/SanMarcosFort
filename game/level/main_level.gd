extends Node3D
## The bay in front of the Castillo. Wires the level's systems together and runs the camera
## for the title screen (a slow sweep over the bay and the fort).

## Offset of the `--cam=ship` debug camera from the ship it follows (toward the fort, raised).
const SHIP_CAM_OFFSET := Vector3(-45.0, 9.0, 20.0)
## Title camera: distance and height from the fort, and how far it sweeps either way.
const MENU_RADIUS := 230.0
const MENU_HEIGHT := 48.0
const MENU_SWEEP := 0.55
## The bell in the San Carlos watch tower rings each wave in.
const BELL_POSITION := Vector3(45.0, 15.5, -44.5)
const BELL_STRIKES := 3

var _ship_cam: Node3D
## `--cam=ship:<type>` follows the first ship of that type (e.g. galleon).
var _ship_kind: String = ""
var _menu_cam: Node3D
var _menu_time: float = 0.0
var _debug_camera: bool = false

@onready var _fx_root: Node3D = $Fx
@onready var _player: PlayerController = $Player
@onready var _bookmarks: Node3D = $CameraBookmarks
@onready var _ships: Node3D = $Ships
@onready var _hud: Hud = $Hud
@onready var _menus: Menus = $Menus


func _ready() -> void:
	Fx.root = _fx_root
	_menu_cam = Node3D.new()
	add_child(_menu_cam)
	_hud.pause_requested.connect(_menus.pause)
	$WaveDirector.wave_started.connect(_ring_bell.unbind(2))
	GameState.phase_changed.connect(_on_phase)
	GameState.reset()
	_on_phase(GameState.phase)
	if GameState.autostart or DebugCli.autoplay or DebugCli.options.has("start"):
		GameState.autostart = false
		GameState.start_run.call_deferred()
	if DebugCli.options.has("shop"):
		_debug_shop.call_deferred()
	if DebugCli.options.has("wave"):
		# The next wave started is the one asked for.
		$WaveDirector.wave_index = int(DebugCli.options["wave"]) - 2
	_apply_debug_camera.call_deferred()


func _debug_shop() -> void:
	GameState.start_run()
	GameState.gold = 420
	GameState.wave = 3
	GameState.fort_hp = 72.0
	GameState.open_shop()


func _process(delta: float) -> void:
	if _ship_cam != null:
		_track_ship()
	if GameState.phase == GameState.Phase.MENU:
		_menu_time += delta
		_place_menu_camera()


func _on_phase(phase: GameState.Phase) -> void:
	if _debug_camera:
		return
	match phase:
		GameState.Phase.MENU:
			_place_menu_camera()
			_player.camera_locked = false
			_player.rig.follow(_menu_cam, PI, true)
			_player.camera_locked = true
		GameState.Phase.PLAYING:
			if _player.camera_locked:
				_player.camera_locked = false
				_player.select_gun(_player.active_index)


func _ring_bell() -> void:
	for strike in BELL_STRIKES:
		get_tree().create_timer(strike * 1.15, false).timeout.connect(
				Audio.play_3d.bind(&"bell", BELL_POSITION, 4.0, 0.0))


func _place_menu_camera() -> void:
	var angle := MENU_SWEEP * sin(_menu_time * 0.06) - 0.25
	var eye := Vector3(cos(angle) * MENU_RADIUS, MENU_HEIGHT, sin(angle) * MENU_RADIUS)
	var focus := Vector3(0.0, 4.0, 0.0)
	_menu_cam.global_transform = Transform3D(Basis.looking_at(focus - eye, Vector3.UP), eye)


## `--cam=<bookmark>`, `--cam=gun:<n>` or `--cam=ship` on the command line picks the view.
func _apply_debug_camera() -> void:
	var bookmark := DebugCli.camera_bookmark()
	if bookmark.is_empty():
		return
	_debug_camera = true
	_player.camera_locked = false
	if bookmark.begins_with("gun:"):
		_player.select_gun(int(bookmark.substr(4)), true)
		return
	var marker: Node3D = null
	if bookmark.begins_with("ship"):
		_ship_kind = bookmark.get_slice(":", 1) if bookmark.contains(":") else ""
		_ship_cam = Node3D.new()
		add_child(_ship_cam)
		_track_ship()
		marker = _ship_cam
	else:
		marker = _bookmarks.get_node_or_null(bookmark) as Node3D
	if marker != null:
		_player.rig.follow(marker, PI, true)
		_player.camera_locked = true


func _track_ship() -> void:
	var target: Ship = null
	for child in _ships.get_children():
		var ship := child as Ship
		if ship != null and (_ship_kind.is_empty() or ship.def.display_name.to_lower() == _ship_kind):
			target = ship
			break
	if target == null:
		return
	var focus := target.global_position + Vector3(0.0, 3.0, 0.0)
	var eye := target.global_position + SHIP_CAM_OFFSET
	_ship_cam.global_transform = Transform3D(Basis.looking_at(focus - eye, Vector3.UP), eye)

class_name WaveDirector
extends Node
## Runs the waves. During play it spawns each wave's ships on the lanes; when every ship of the
## wave is sunk or gone, it opens the shop, and the next wave starts once the shop closes.
## After the authored waves, the last few repeat with more ships, sailing faster each time.

signal wave_started(number: int, title: String)
signal wave_cleared(number: int)

@export var waves: Array[WaveDef] = []
@export var ship_scene: PackedScene
@export var lanes_root: Node3D
@export var ships_root: Node3D
@export var first_delay: float = 3.0
@export var next_delay: float = 2.5
## Ships keep within this many metres either side of their lane.
@export var lateral_spread: float = 25.0
## How many of the last authored waves repeat after the end, and how much faster each loop.
@export var repeat_count: int = 4
@export var repeat_speedup: float = 0.1

var wave_index: int = -1
var alive: int = 0

var _lanes: Array[ShipLane] = []
var _events: Array[Dictionary] = []
var _clock: float = 0.0
var _running: bool = false
var _break_left: float = 0.0
var _speed_bonus: float = 1.0


func _ready() -> void:
	for child in lanes_root.get_children():
		if child is ShipLane:
			_lanes.append(child)
	GameState.phase_changed.connect(_on_phase_changed)


func is_running() -> bool:
	return _running


func _on_phase_changed(phase: GameState.Phase) -> void:
	if phase == GameState.Phase.PLAYING and not _running:
		_break_left = first_delay if wave_index < 0 else next_delay


func _process(delta: float) -> void:
	if not GameState.is_playing() or waves.is_empty():
		return
	if not _running:
		_break_left -= delta
		if _break_left <= 0.0:
			_start_next()
		return
	_clock += delta
	while not _events.is_empty() and _events[0].time <= _clock:
		_spawn(_events.pop_front())
	if _events.is_empty() and alive == 0:
		_running = false
		wave_cleared.emit(wave_index + 1)
		GameState.open_shop()


func _start_next() -> void:
	wave_index += 1
	var wave: WaveDef
	var loop := 0
	if wave_index < waves.size():
		wave = waves[wave_index]
	else:
		var first_repeat := maxi(waves.size() - repeat_count, 0)
		var span := waves.size() - first_repeat
		var k := wave_index - waves.size()
		wave = waves[first_repeat + k % span]
		loop = 1 + floori(float(k) / span)
	_speed_bonus = 1.0 + repeat_speedup * loop
	_events = wave.schedule(loop)
	_clock = 0.0
	_running = true
	GameState.wave = wave_index + 1
	GameState.changed.emit()
	var title := wave.title if loop == 0 else "%s, reinforced" % wave.title
	wave_started.emit(wave_index + 1, title)


func _spawn(event: Dictionary) -> void:
	var allowed: PackedInt32Array = event.lanes
	var lane_index := allowed[randi() % allowed.size()] if allowed.size() > 0 else randi() % _lanes.size()
	var ship := ship_scene.instantiate() as Ship
	ship.setup(event.ship, _lanes[lane_index], randf_range(-lateral_spread, lateral_spread),
			event.speed * _speed_bonus, event.armed)
	ship.removed.connect(_on_ship_removed)
	ships_root.add_child(ship)
	alive += 1


func _on_ship_removed(_ship: Ship) -> void:
	alive -= 1

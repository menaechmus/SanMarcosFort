class_name Hud
extends CanvasLayer
## In-game display: run stats, fort and town bars, the active gun and its ammunition, wave
## banners, and on-screen buttons for touch devices. Shown only while a run is on.

signal pause_requested

## Out of arc gets its own hint, naming a gun that can reach (see _out_of_arc_hint).
const AIM_TEXT := {
	Cannon.Aim.READY: "",
	Cannon.Aim.OUT_OF_RANGE: "Out of range",
	Cannon.Aim.TOO_CLOSE: "Too close: the gun can't depress that far",
}
const BANNER_TIME := 3.5

@export var player: PlayerController
@export var director: WaveDirector

var _banner_left: float = 0.0

@onready var _root: Control = $Root
@onready var _wave: Label = $Root/Stats/Wave
@onready var _score: Label = $Root/Stats/Score
@onready var _ships: Label = $Root/Stats/Ships
@onready var _fort_bar: ProgressBar = $Root/Bars/FortBar
@onready var _town_bar: ProgressBar = $Root/Bars/TownBar
@onready var _gun_name: Label = $Root/GunPanel/GunName
@onready var _ammo: Label = $Root/GunPanel/Ammo
@onready var _reload: ProgressBar = $Root/GunPanel/Reload
@onready var _aim_hint: Label = $Root/GunPanel/AimHint
@onready var _banner: Label = $Root/Banner
@onready var _pause_button: Button = $Root/Pause
@onready var _touch: Control = $Root/Touch
@onready var _fire_button: Button = $Root/Touch/Fire
@onready var _prev_button: Button = $Root/Touch/PrevGun
@onready var _next_button: Button = $Root/Touch/NextGun
@onready var _spyglass_button: Button = $Root/Touch/Spyglass
@onready var _ammo_button: Button = $Root/Touch/Ammo


func _ready() -> void:
	GameState.changed.connect(_refresh)
	GameState.phase_changed.connect(_on_phase)
	director.wave_started.connect(_on_wave_started)
	player.ammo_changed.connect(_on_ammo_changed)
	_touch.visible = DisplayServer.is_touchscreen_available()
	_fire_button.pressed.connect(player.fire)
	_prev_button.pressed.connect(player.cycle_gun.bind(-1))
	_next_button.pressed.connect(player.cycle_gun.bind(1))
	_spyglass_button.pressed.connect(player.rig.toggle_spyglass)
	_ammo_button.pressed.connect(player.cycle_ammo)
	_pause_button.pressed.connect(pause_requested.emit)
	player.input.ui_hit_test = _touch_on_buttons
	_banner.modulate.a = 0.0
	_on_ammo_changed(player.current_ammo())
	_on_phase(GameState.phase)
	_refresh()


func _process(delta: float) -> void:
	if not _root.visible or player.guns.is_empty():
		return
	var cannon := player.active_gun().cannon
	_gun_name.text = player.active_gun().display_name
	_reload.value = cannon.reload_fraction() * 100.0
	if cannon.suppressed_left > 0.0:
		_aim_hint.text = "The crew is taking cover!"
	elif not player.aim_valid:
		_aim_hint.text = ""
	elif cannon.aim_state == Cannon.Aim.OUT_OF_ARC:
		_aim_hint.text = _out_of_arc_hint()
	else:
		_aim_hint.text = AIM_TEXT.get(cannon.aim_state, "")
	if _banner_left > 0.0:
		_banner_left -= delta
		_banner.modulate.a = clampf(_banner_left / 0.6, 0.0, 1.0)


## Each gun fires only through its own embrasure, so point the player at one that bears
## (the number in brackets is its key).
func _out_of_arc_hint() -> String:
	var index := player.gun_that_bears(player.aim_point)
	if index < 0:
		return "Outside every gun's field of fire"
	return "Outside this gun's field of fire: %s (%d) can reach it" % [player.guns[index].display_name, index + 1]


func _on_phase(phase: GameState.Phase) -> void:
	_root.visible = phase == GameState.Phase.PLAYING or phase == GameState.Phase.SHOP


func _refresh() -> void:
	_wave.text = "Wave %d" % maxi(GameState.wave, 1)
	_score.text = "Score %d    Gold %d" % [GameState.score, GameState.gold]
	_ships.text = "Sunk %d    Escaped %d" % [GameState.ships_sunk, GameState.ships_escaped]
	_fort_bar.value = GameState.fort_hp / GameState.FORT_HP_MAX * 100.0
	_town_bar.value = GameState.town_damage / GameState.TOWN_DAMAGE_MAX * 100.0
	_ammo_button.visible = player.available_ammo().size() > 1


func _on_wave_started(number: int, title: String) -> void:
	_show_banner("Wave %d\n%s" % [number, title], BANNER_TIME)


func _on_ammo_changed(ammo: AmmoDef) -> void:
	_ammo.text = ammo.display_name
	_ammo_button.visible = player.available_ammo().size() > 1


## Shows `text` in the banner for `duration` seconds; 0 keeps it up until replaced.
func _show_banner(text: String, duration: float) -> void:
	_banner.text = text
	_banner.modulate.a = 1.0
	_banner_left = duration


func _touch_on_buttons(position: Vector2) -> bool:
	if not _touch.visible:
		return false
	for button: Button in [_fire_button, _prev_button, _next_button, _spyglass_button, _ammo_button, _pause_button]:
		if button.visible and button.get_global_rect().has_point(position):
			return true
	return false

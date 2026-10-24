extends Node
## State of the current run: phase (menu, playing, shop, game over), score, gold, upgrades,
## fort health, town damage and shot counters. The high score is saved between sessions.

signal changed
signal phase_changed(phase: Phase)
signal game_over(reason: String)

enum Phase { MENU, PLAYING, SHOP, GAME_OVER }

const FORT_HP_MAX := 100.0
const TOWN_DAMAGE_MAX := 100.0
const SAVE_PATH := "user://save.cfg"

var phase: Phase = Phase.MENU
var score: int = 0
var gold: int = 0
var wave: int = 0
var fort_hp: float = FORT_HP_MAX
var town_damage: float = 0.0
var ships_sunk: int = 0
var ships_escaped: int = 0
var shots_fired: int = 0
var shots_hit: int = 0
var high_score: int = 0
var new_high_score: bool = false
## Set before reloading the level to skip the title screen ("Play again").
var autostart: bool = false
## Why the last run ended.
var end_reason: String = ""
## Whether the high score is written to disk (debug runs turn it off).
var persist: bool = true
var upgrades: Upgrades = Upgrades.new()
var is_over: bool:
	get:
		return phase == Phase.GAME_OVER


func _ready() -> void:
	_load()


## Back to a fresh run, waiting in the menu.
func reset() -> void:
	score = 0
	gold = 0
	wave = 0
	fort_hp = FORT_HP_MAX
	town_damage = 0.0
	ships_sunk = 0
	ships_escaped = 0
	shots_fired = 0
	shots_hit = 0
	new_high_score = false
	upgrades = Upgrades.new()
	_set_phase(Phase.MENU)
	changed.emit()


func start_run() -> void:
	reset()
	_set_phase(Phase.PLAYING)


func open_shop() -> void:
	if phase == Phase.PLAYING:
		_set_phase(Phase.SHOP)


func close_shop() -> void:
	if phase == Phase.SHOP:
		_set_phase(Phase.PLAYING)


func is_playing() -> bool:
	return phase == Phase.PLAYING


func record_shot() -> void:
	shots_fired += 1
	changed.emit()


func record_hit() -> void:
	shots_hit += 1
	changed.emit()


func ship_sunk(def: ShipDef) -> void:
	ships_sunk += 1
	score += def.score
	gold += def.bounty
	changed.emit()


func ship_escaped(def: ShipDef) -> void:
	ships_escaped += 1
	town_damage = minf(town_damage + def.town_damage, TOWN_DAMAGE_MAX)
	changed.emit()
	if town_damage >= TOWN_DAMAGE_MAX:
		_end("Too many ships got past to the town.")


func damage_fort(amount: float) -> void:
	if phase != Phase.PLAYING:
		return
	fort_hp = maxf(fort_hp - amount, 0.0)
	changed.emit()
	if fort_hp <= 0.0:
		_end("The Castillo has fallen.")


func buy_upgrade(id: StringName) -> bool:
	var left := upgrades.buy(id, gold)
	if left < 0:
		return false
	gold = left
	changed.emit()
	return true


func can_repair() -> bool:
	return gold >= Upgrades.REPAIR_COST and fort_hp < FORT_HP_MAX


func repair_fort() -> bool:
	if not can_repair():
		return false
	gold -= Upgrades.REPAIR_COST
	fort_hp = minf(fort_hp + Upgrades.REPAIR_AMOUNT, FORT_HP_MAX)
	changed.emit()
	return true


func accuracy() -> float:
	return 0.0 if shots_fired == 0 else float(shots_hit) / shots_fired


func _end(reason: String) -> void:
	if phase == Phase.GAME_OVER:
		return
	end_reason = reason
	if score > high_score:
		high_score = score
		new_high_score = true
		_save()
	_set_phase(Phase.GAME_OVER)
	game_over.emit(reason)


func _set_phase(value: Phase) -> void:
	if phase == value:
		return
	phase = value
	phase_changed.emit(value)


func _load() -> void:
	var cfg := ConfigFile.new()
	if cfg.load(SAVE_PATH) == OK:
		high_score = cfg.get_value("records", "high_score", 0)


func _save() -> void:
	if not persist:
		return
	var cfg := ConfigFile.new()
	cfg.load(SAVE_PATH)
	cfg.set_value("records", "high_score", high_score)
	cfg.save(SAVE_PATH)

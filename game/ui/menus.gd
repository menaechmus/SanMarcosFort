class_name Menus
extends CanvasLayer
## Title, pause, settings, shop, game-over and credits screens, built in code and styled by
## the UI theme. Follows GameState's phase and handles pausing.

const THEME := preload("res://game/ui/theme.tres")
## The font's license has to travel with it (the exports include this file).
const FONT_LICENSE := "res://assets/fonts/im_fell_english/OFL.txt"
const CREDITS := """[center][b]San Marcos[/b]
Defend the Castillo de San Marcos, St. Augustine, Florida[/center]

[b]The fort[/b]
Modelled from the Historic American Buildings Survey drawings HABS FL-17 (Library of Congress), a U.S. Government work with no known restrictions, and facts published by the National Park Service.

[b]Textures[/b]
Poly Haven (polyhaven.com), CC0: large_sandstone_blocks_01, painted_plaster_wall, brown_planks_03, cotton_jersey, grass_ground, coast_sand_01.

[b]Font[/b]
IM Fell English by Igino Marini, SIL Open Font License 1.1.

[b]Sounds[/b]
Synthesized for this game.

[b]Made with[/b]
Godot Engine, Blender, GUT.
"""

@export var player: PlayerController
@export var director: WaveDirector

var _root: Control
var _dim: ColorRect
var _screens: Dictionary = {}
var _current: String = ""
var _back_to: String = ""
## Refreshers for the open shop's rows, run after every purchase.
var _shop_updaters: Array[Callable] = []


func _ready() -> void:
	layer = 10
	process_mode = Node.PROCESS_MODE_ALWAYS
	# The dim covers the whole screen; the screens keep clear of phone notches.
	_dim = ColorRect.new()
	_dim.color = Color(0.0, 0.0, 0.0, 0.4)
	_dim.set_anchors_preset(Control.PRESET_FULL_RECT)
	_dim.mouse_filter = Control.MOUSE_FILTER_STOP
	add_child(_dim)
	_root = SafeArea.new()
	_root.theme = THEME
	_root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_root)
	_build_title()
	_build_pause()
	_build_settings()
	_build_credits()
	GameState.phase_changed.connect(_on_phase)
	_on_phase(GameState.phase)


func pause() -> void:
	if _current == "" and GameState.is_playing():
		get_tree().paused = true
		_show("pause")


func _unhandled_input(event: InputEvent) -> void:
	if not event.is_action_pressed(&"pause"):
		return
	if _current == "" and GameState.is_playing():
		pause()
	elif _current == "pause":
		_resume()
	elif _current == "settings" or _current == "credits":
		_show(_back_to)
	else:
		return
	get_viewport().set_input_as_handled()


func _on_phase(phase: GameState.Phase) -> void:
	match phase:
		GameState.Phase.MENU:
			_show("title")
		GameState.Phase.PLAYING:
			_show("")
		GameState.Phase.SHOP:
			_build_shop()
			_show("shop")
		GameState.Phase.GAME_OVER:
			get_tree().paused = true
			_build_game_over()
			_show("game_over")


func _show(screen: String) -> void:
	_current = screen
	for key in _screens:
		_screens[key].visible = key == screen
	_dim.visible = screen != "" and screen != "title"


# --- Screen building -----------------------------------------------------------------------

func _screen(key: String, title: String, width: float = 460.0, title_size: int = 34, at_left: bool = false) -> VBoxContainer:
	if _screens.has(key):
		_screens[key].queue_free()
	var center: Container
	if at_left:
		# Keep the left side for the panel so the fort stays in view behind the title.
		center = MarginContainer.new()
		center.add_theme_constant_override("margin_left", 56)
		center.add_theme_constant_override("margin_top", 40)
		center.add_theme_constant_override("margin_bottom", 40)
	else:
		center = CenterContainer.new()
	center.set_anchors_preset(Control.PRESET_FULL_RECT)
	center.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_root.add_child(center)
	var panel := PanelContainer.new()
	panel.custom_minimum_size = Vector2(width, 0.0)
	if at_left:
		panel.size_flags_horizontal = Control.SIZE_SHRINK_BEGIN
		panel.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	center.add_child(panel)
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 12)
	panel.add_child(box)
	_label(box, title, title_size, HORIZONTAL_ALIGNMENT_CENTER).theme_type_variation = &"TitleLabel"
	center.visible = false
	_screens[key] = center
	return box


func _label(parent: Control, text: String, size: int = 20, align := HORIZONTAL_ALIGNMENT_LEFT) -> Label:
	var label := Label.new()
	label.text = text
	label.horizontal_alignment = align
	label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	label.add_theme_font_size_override("font_size", size)
	parent.add_child(label)
	return label


func _button(parent: Control, text: String, action: Callable) -> Button:
	var button := Button.new()
	button.text = text
	button.custom_minimum_size = Vector2(0.0, 52.0)
	button.pressed.connect(Audio.play_ui.bind(&"click"))
	button.pressed.connect(action)
	parent.add_child(button)
	return button


func _build_title() -> void:
	var box := _screen("title", "San Marcos", 440.0, 52, true)
	_label(box, "Defend the Castillo de San Marcos\nSt. Augustine, Florida", 20, HORIZONTAL_ALIGNMENT_CENTER)
	if GameState.high_score > 0:
		_label(box, "High score: %d" % GameState.high_score, 18, HORIZONTAL_ALIGNMENT_CENTER)
	_button(box, "Play", GameState.start_run)
	_button(box, "Settings", _open_settings.bind("title"))
	_button(box, "Credits", _open_credits.bind("title"))
	if not OS.has_feature("web") and not OS.has_feature("mobile"):
		_button(box, "Quit", get_tree().quit)


func _build_pause() -> void:
	var box := _screen("pause", "Paused")
	_button(box, "Resume", _resume)
	_button(box, "Settings", _open_settings.bind("pause"))
	_button(box, "Quit to title", _to_title)


func _build_settings() -> void:
	var box := _screen("settings", "Settings", 560.0)
	var quality := OptionButton.new()
	for item in ["Graphics: low", "Graphics: medium", "Graphics: high"]:
		quality.add_item(item)
	quality.selected = Settings.quality
	quality.item_selected.connect(func(index: int) -> void:
		Settings.quality = index as Settings.Quality
		_save_settings())
	box.add_child(quality)
	var look := CheckButton.new()
	look.text = "Spanish colonial look (white plaster, red sentry boxes)"
	look.button_pressed = Settings.fort_plaster
	look.toggled.connect(func(on: bool) -> void:
		Settings.fort_plaster = on
		_save_settings())
	box.add_child(look)
	var assist := CheckButton.new()
	assist.text = "Aim assist (shows where a ship will be)"
	assist.button_pressed = Settings.aim_assist
	assist.toggled.connect(func(on: bool) -> void:
		Settings.aim_assist = on
		_save_settings())
	box.add_child(assist)
	_label(box, "Volume", 18)
	var volume := HSlider.new()
	volume.min_value = 0.0
	volume.max_value = 1.0
	volume.step = 0.05
	volume.value = Settings.master_volume
	volume.value_changed.connect(func(v: float) -> void:
		Settings.master_volume = v
		_save_settings())
	box.add_child(volume)
	_label(box, "Vegetation detail changes on the next game.", 15)
	_button(box, "Back", func() -> void: _show(_back_to))


func _build_credits() -> void:
	var box := _screen("credits", "Credits", 720.0)
	var text := RichTextLabel.new()
	text.bbcode_enabled = true
	text.custom_minimum_size = Vector2(660.0, 360.0)
	text.text = CREDITS + "\n[b]Godot Engine license[/b]\n" + Engine.get_license_text() \
			+ "\n\n[b]IM Fell English font license[/b]\n" + FileAccess.get_file_as_string(FONT_LICENSE)
	box.add_child(text)
	_button(box, "Back", func() -> void: _show(_back_to))


func _build_shop() -> void:
	_shop_updaters.clear()
	var box := _screen("shop", "Wave %d cleared" % GameState.wave, 640.0)
	var gold := _label(box, "", 22, HORIZONTAL_ALIGNMENT_CENTER)
	_shop_updaters.append(func() -> void:
		gold.text = "Gold: %d    Castillo: %d%%" % [GameState.gold, roundi(GameState.fort_hp)])
	var rows := VBoxContainer.new()
	rows.add_theme_constant_override("separation", 8)
	box.add_child(rows)
	for id: StringName in Upgrades.CATALOG:
		_shop_row(rows, id)
	var repair := Button.new()
	repair.custom_minimum_size = Vector2(0.0, 48.0)
	repair.text = "Repair the walls (+%d%%) for %d gold" % [Upgrades.REPAIR_AMOUNT, Upgrades.REPAIR_COST]
	repair.pressed.connect(func() -> void:
		GameState.repair_fort()
		_refresh_shop())
	_shop_updaters.append(func() -> void: repair.disabled = not GameState.can_repair())
	box.add_child(repair)
	_button(box, "Next wave", GameState.close_shop)
	_refresh_shop()


func _shop_row(parent: Control, id: StringName) -> void:
	var info: Dictionary = Upgrades.CATALOG[id]
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 14)
	parent.add_child(row)
	var text := VBoxContainer.new()
	text.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row.add_child(text)
	var name_label := _label(text, "", 20)
	_label(text, info["desc"], 15)
	var buy := Button.new()
	buy.custom_minimum_size = Vector2(150.0, 48.0)
	buy.pressed.connect(func() -> void:
		GameState.buy_upgrade(id)
		_refresh_shop())
	row.add_child(buy)
	_shop_updaters.append(func() -> void:
		var top := GameState.upgrades.max_level(id)
		name_label.text = info["name"] + ("" if top == 1 else "  (%d/%d)" % [GameState.upgrades.level(id), top])
		var cost := GameState.upgrades.next_cost(id)
		buy.text = "Done" if cost < 0 else "%d gold" % cost
		buy.disabled = cost < 0 or cost > GameState.gold)


func _refresh_shop() -> void:
	for updater in _shop_updaters:
		updater.call()


func _build_game_over() -> void:
	var box := _screen("game_over", "The siege is over", 540.0)
	_label(box, GameState.end_reason, 20, HORIZONTAL_ALIGNMENT_CENTER)
	_label(box, "Score %d%s" % [GameState.score, "  (new high score!)" if GameState.new_high_score else ""], 26,
			HORIZONTAL_ALIGNMENT_CENTER)
	_label(box, "Wave %d. Ships sunk: %d. Accuracy: %d%%." % [GameState.wave, GameState.ships_sunk,
			roundi(GameState.accuracy() * 100.0)], 18, HORIZONTAL_ALIGNMENT_CENTER)
	_button(box, "Play again", func() -> void:
		GameState.autostart = true
		_reload())
	_button(box, "Quit to title", _to_title)


# --- Actions -------------------------------------------------------------------------------

func _open_settings(from: String) -> void:
	_back_to = from
	_show("settings")


func _open_credits(from: String) -> void:
	_back_to = from
	_show("credits")


func _resume() -> void:
	get_tree().paused = false
	_show("")


func _to_title() -> void:
	GameState.autostart = false
	_reload()


func _reload() -> void:
	get_tree().paused = false
	get_tree().reload_current_scene()


func _save_settings() -> void:
	Settings.apply()
	Settings.save_settings()

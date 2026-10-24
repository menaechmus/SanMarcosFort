class_name AimInput
extends Node
## Turns mouse, touch and keyboard input into aiming intents: a pointer position on screen,
## fire requests, gun switching, camera pan and zoom. Mouse and touch behave the same way.

signal fire_requested
signal gun_selected(index: int)
signal gun_cycled(step: int)
signal spyglass_toggled
signal ammo_cycled

## Touch aiming keeps the marker this far above the finger so it stays visible.
const TOUCH_AIM_OFFSET := Vector2(0.0, -90.0)
## Pixels of pinch-distance change per zoom step.
const PINCH_PIXELS_PER_STEP := 60.0

## Screen position the player is aiming at.
var pointer: Vector2 = Vector2.ZERO
var has_pointer: bool = false
## Camera pan (pixels) and zoom (steps) gathered since the controller last read them.
var pan_pixels: Vector2 = Vector2.ZERO
var zoom_steps: float = 0.0
## Optional check (Vector2 -> bool): is this touch on on-screen controls?
var ui_hit_test: Callable

var _touches: Dictionary = {}
var _pinch_distance: float = 0.0


func _unhandled_input(event: InputEvent) -> void:
	# Touches arrive as screen events; ignore the mouse events Godot emulates from them.
	if event.device == InputEvent.DEVICE_ID_EMULATION and event is InputEventMouse:
		return
	if event is InputEventScreenTouch:
		_on_touch(event)
	elif event is InputEventScreenDrag:
		_on_drag(event)
	elif event is InputEventMouseMotion:
		var motion := event as InputEventMouseMotion
		if motion.button_mask & (MOUSE_BUTTON_MASK_RIGHT | MOUSE_BUTTON_MASK_MIDDLE):
			pan_pixels += motion.relative
		else:
			pointer = motion.position
			has_pointer = true
	else:
		if event is InputEventMouseButton:
			pointer = (event as InputEventMouseButton).position
			has_pointer = true
		_on_action(event)


func _on_action(event: InputEvent) -> void:
	if event.is_action_pressed(&"fire"):
		fire_requested.emit()
	elif event.is_action_pressed(&"zoom_in"):
		zoom_steps += 1.0
	elif event.is_action_pressed(&"zoom_out"):
		zoom_steps -= 1.0
	elif event.is_action_pressed(&"next_gun"):
		gun_cycled.emit(1)
	elif event.is_action_pressed(&"prev_gun"):
		gun_cycled.emit(-1)
	elif event.is_action_pressed(&"spyglass"):
		spyglass_toggled.emit()
	elif event.is_action_pressed(&"ammo_next"):
		ammo_cycled.emit()
	else:
		for i in 6:
			if event.is_action_pressed(StringName("gun_%d" % (i + 1))):
				gun_selected.emit(i)
				return


func _on_touch(event: InputEventScreenTouch) -> void:
	if not event.pressed:
		_touches.erase(event.index)
		return
	if ui_hit_test.is_valid() and ui_hit_test.call(event.position):
		return
	_touches[event.index] = event.position
	if _touches.size() == 1:
		pointer = event.position + TOUCH_AIM_OFFSET
		has_pointer = true
	elif _touches.size() == 2:
		_pinch_distance = _two_finger_distance()


func _on_drag(event: InputEventScreenDrag) -> void:
	if not _touches.has(event.index):
		return
	_touches[event.index] = event.position
	if _touches.size() == 1:
		pointer = event.position + TOUCH_AIM_OFFSET
	else:
		pan_pixels += event.relative * 0.5
		var distance := _two_finger_distance()
		if _pinch_distance > 0.0:
			zoom_steps += (distance - _pinch_distance) / PINCH_PIXELS_PER_STEP
		_pinch_distance = distance


func _two_finger_distance() -> float:
	var points := _touches.values()
	if points.size() < 2:
		return 0.0
	return (points[0] as Vector2).distance_to(points[1])

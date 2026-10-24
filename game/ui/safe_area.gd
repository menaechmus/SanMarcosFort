class_name SafeArea
extends Control
## A full-screen control whose edges keep clear of phone notches and rounded corners: on
## mobile they're pulled in to the display's safe area. Elsewhere it simply fills the screen.

## How often to re-check the safe area. Turning the phone around moves the notch to the other
## side without resizing the window, so there's no signal for it.
const CHECK_INTERVAL := 0.5

var _safe: Rect2i
var _check_left: float = 0.0


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	set_process(OS.has_feature("mobile"))
	get_viewport().size_changed.connect(_fit, CONNECT_DEFERRED)
	_fit()


func _process(delta: float) -> void:
	_check_left -= delta
	if _check_left <= 0.0:
		_check_left = CHECK_INTERVAL
		if DisplayServer.get_display_safe_area() != _safe:
			_fit()


func _fit() -> void:
	if not OS.has_feature("mobile"):
		return
	_safe = DisplayServer.get_display_safe_area()
	var window := Rect2(DisplayServer.window_get_position(), DisplayServer.window_get_size())
	var safe := Rect2(_safe)
	if not window.has_area() or not safe.has_area():
		return
	# Window pixels to canvas units: the stretch mode scales the whole UI.
	var to_canvas := get_viewport_rect().size / window.size
	offset_left = maxf(safe.position.x - window.position.x, 0.0) * to_canvas.x
	offset_top = maxf(safe.position.y - window.position.y, 0.0) * to_canvas.y
	offset_right = -maxf(window.end.x - safe.end.x, 0.0) * to_canvas.x
	offset_bottom = -maxf(window.end.y - safe.end.y, 0.0) * to_canvas.y

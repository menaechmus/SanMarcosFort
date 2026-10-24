extends Node
## The one clock shared by the water shader (global uniform `water_time`) and the CPU wave
## math, so floating objects stay on the rendered waves. Pauses with the scene tree.

var time: float = 0.0


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_PAUSABLE
	process_priority = -100
	_push()


func _process(delta: float) -> void:
	time += delta
	_push()


func _push() -> void:
	RenderingServer.global_shader_parameter_set(&"water_time", time)

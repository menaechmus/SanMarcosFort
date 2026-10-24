extends Node3D
## Fires every particle emitter under this node once, fades any lights, then frees itself.

@export var lifetime: float = 3.0
## Seconds for OmniLight3D children to fade to dark (muzzle flashes).
@export var flash_time: float = 0.12


func _ready() -> void:
	for node in find_children("*", "CPUParticles3D", true, false):
		(node as CPUParticles3D).restart()
	for node in find_children("*", "OmniLight3D", true, false):
		create_tween().tween_property(node, "light_energy", 0.0, flash_time)
	get_tree().create_timer(lifetime, false).timeout.connect(queue_free)

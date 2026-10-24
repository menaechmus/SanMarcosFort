class_name MaterialSetter
extends Node
## Child node that swaps the placeholder materials of its parent's imported model for game
## materials, by material name (see MaterialMapper). Lets scenes inherited from a .glb keep
## their own root script.

## Material slot name in the model -> game material.
@export var materials: Dictionary = {}


func _ready() -> void:
	MaterialMapper.apply(get_parent(), materials)

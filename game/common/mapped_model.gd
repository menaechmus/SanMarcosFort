class_name MappedModel
extends Node3D
## An imported model whose placeholder materials are swapped for game materials by name
## (see MaterialMapper), and whose collision bodies are put on one physics layer.

## Material slot name in the model -> game material.
@export var materials: Dictionary = {}
@export_flags_3d_physics var collision_layer: int = 1


func _ready() -> void:
	MaterialMapper.apply(self, materials)
	for node in find_children("*", "StaticBody3D", true, false):
		var body := node as StaticBody3D
		body.collision_layer = collision_layer
		body.collision_mask = 0

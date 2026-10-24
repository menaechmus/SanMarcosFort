class_name MaterialMapper
extends RefCounted
## Swaps the placeholder materials of an imported model for game materials, by material
## name. The asset generators name their material slots; the game owns the real materials,
## so textures and shaders can be tuned without re-exporting models.


static func apply(root: Node, materials: Dictionary) -> void:
	var meshes := root.find_children("*", "MeshInstance3D", true, false)
	if root is MeshInstance3D:
		meshes.append(root)
	for node in meshes:
		var instance := node as MeshInstance3D
		if instance.mesh == null:
			continue
		for i in instance.mesh.get_surface_count():
			var source := instance.mesh.surface_get_material(i)
			if source != null and materials.has(source.resource_name):
				instance.set_surface_override_material(i, materials[source.resource_name])

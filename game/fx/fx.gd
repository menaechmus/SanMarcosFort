class_name Fx
extends RefCounted
## Spawns one-shot effect scenes into the level's effects container.

## Set by the level; effects are parented here so they outlive the node that caused them.
static var root: Node3D


## Spawns `scene` at `position` with its local +Y pointing along `up`.
static func spawn(scene: PackedScene, position: Vector3, up: Vector3 = Vector3.UP, size: float = 1.0) -> Node3D:
	if scene == null or root == null or not is_instance_valid(root):
		return null
	var node := scene.instantiate() as Node3D
	root.add_child(node)
	node.global_position = position
	node.global_basis = basis_with_up(up).scaled(Vector3.ONE * size)
	return node


static func basis_with_up(up: Vector3) -> Basis:
	if up.length_squared() < 0.0001:
		return Basis.IDENTITY
	up = up.normalized()
	if up.dot(Vector3.UP) < -0.999:
		return Basis(Vector3.RIGHT, PI)
	return Basis(Quaternion(Vector3.UP, up))

class_name ScatterData
extends Resource
## Prop placements written by tools/blender/build_props.py. For each prop name in `names`, the
## matching entry of `data` is a flat PackedFloat32Array of [x, y, z, yaw, scale] per instance.

@export var names: PackedStringArray = PackedStringArray()
@export var data: Array = []

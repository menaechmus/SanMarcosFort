class_name GunPosition
extends Node3D
## A gun emplacement at an embrasure. The node sits at the embrasure's throat, the point the
## gun turns about; local -Z is the centre of its field of fire.

@export var display_name: String = "Gun"
@export var unlocked: bool = true
## How far the gun can be laid either side of its embrasure's axis. The embrasures keep their
## HABS size (4 ft at the throat, 6.5 ft at the mouth, 9 ft deep): beyond about 14.6 degrees the
## ball would strike a cheek (tools/blender/build_fort.py prints the figure;
## tests/test_gun_clearance.gd checks it).
@export var yaw_limit_deg: float = 14.0

@onready var cannon: Cannon = $Cannon
@onready var camera_anchor: Marker3D = $CameraAnchor


func _ready() -> void:
	cannon.yaw_limit_deg = yaw_limit_deg

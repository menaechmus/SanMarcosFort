class_name GunPosition
extends Node3D
## A gun emplacement at an embrasure. Local -Z is the centre of its field of fire.

@export var display_name: String = "Gun"
@export var unlocked: bool = true
## How far the gun can swing either side of its embrasure.
@export var yaw_limit_deg: float = 40.0

@onready var cannon: Cannon = $Cannon
@onready var camera_anchor: Marker3D = $CameraAnchor


func _ready() -> void:
	cannon.yaw_limit_deg = yaw_limit_deg

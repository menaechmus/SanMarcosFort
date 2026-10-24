extends GutTest
## Every gun fires out through its own embrasure over its whole field of fire: neither the
## barrel nor the ball may touch the fort's masonry.

const FORT_SCENE := preload("res://game/fort/fort.tscn")
const BALL_RADIUS := 0.18
## Thickest part of the barrel between the trunnions and the muzzle (the muzzle swell).
const BARREL_RADIUS := 0.2
## How far along the bore the ball's path is checked, metres.
const SHOT_CHECK_DISTANCE := 40.0
const WALLS := Fort.FORT_LAYER | Fort.TERRAIN_LAYER


func test_lines_of_fire_clear_the_walls() -> void:
	var guns := await _spawn_guns()
	assert_eq(guns.size(), 4, "gun positions")
	for gun in guns:
		var cannon := gun.cannon
		for yaw_deg: float in [-gun.yaw_limit_deg, 0.0, gun.yaw_limit_deg]:
			for pitch_deg: float in [cannon.min_elevation_deg, 0.0, cannon.max_elevation_deg]:
				cannon.lay_now(deg_to_rad(yaw_deg), deg_to_rad(pitch_deg))
				var pose := "%s at yaw %.1f, elevation %.1f" % [gun.display_name, yaw_deg, pitch_deg]
				assert_true(_ball_path_clear(cannon), "ball clears the masonry: " + pose)
				assert_true(_barrel_clear(cannon), "barrel clears the masonry: " + pose)


## The check has teeth: laid well outside its field of fire, a gun's shot meets its own wall.
func test_shot_outside_the_field_of_fire_hits_the_wall() -> void:
	var guns := await _spawn_guns()
	for gun in guns:
		gun.cannon.lay_now(deg_to_rad(25.0), 0.0)
		assert_false(_ball_path_clear(gun.cannon), "%s laid 25 degrees off hits its wall" % gun.display_name)


func _spawn_guns() -> Array[GunPosition]:
	var fort: Fort = FORT_SCENE.instantiate()
	add_child_autofree(fort)
	await wait_physics_frames(3)
	var guns: Array[GunPosition] = []
	for child in fort.get_node("GunPositions").get_children():
		guns.append(child as GunPosition)
	return guns


## A ball-sized sphere swept from the muzzle along the bore meets nothing.
func _ball_path_clear(cannon: Cannon) -> bool:
	var muzzle := cannon.get_node("Yaw/Pitch/Muzzle") as Node3D
	var query := PhysicsShapeQueryParameters3D.new()
	var ball := SphereShape3D.new()
	ball.radius = BALL_RADIUS
	query.shape = ball
	query.transform = Transform3D(Basis.IDENTITY, muzzle.global_position)
	query.motion = -muzzle.global_basis.z.normalized() * SHOT_CHECK_DISTANCE
	query.collision_mask = WALLS
	var space := cannon.get_world_3d().direct_space_state
	return space.intersect_shape(query, 1).is_empty() and space.cast_motion(query)[0] >= 1.0


## Lines along the top, bottom and sides of the barrel, trunnions to muzzle, meet nothing.
func _barrel_clear(cannon: Cannon) -> bool:
	var trunnions := cannon.get_node("Yaw/Pitch") as Node3D
	var muzzle := cannon.get_node("Yaw/Pitch/Muzzle") as Node3D
	var basis := trunnions.global_basis.orthonormalized()
	var space := cannon.get_world_3d().direct_space_state
	for offset: Vector3 in [basis.x, -basis.x, basis.y, -basis.y]:
		var from := trunnions.global_position + offset * BARREL_RADIUS
		var to := muzzle.global_position + offset * BARREL_RADIUS
		if not space.intersect_ray(PhysicsRayQueryParameters3D.create(from, to, WALLS)).is_empty():
			return false
	return true

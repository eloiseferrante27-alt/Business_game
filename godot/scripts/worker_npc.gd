extends CharacterBody3D
class_name WorkerNPC

@export var walk_speed: float = 2.0

var _agent: NavigationAgent3D
var _visual: MeshInstance3D
var _rng := RandomNumberGenerator.new()


func _ready() -> void:
    _rng.randomize()
    _agent = NavigationAgent3D.new()
    _agent.path_desired_distance = 0.4
    _agent.target_desired_distance = 0.5
    add_child(_agent)

    var capsule := CapsuleMesh.new()
    capsule.radius = 0.28
    capsule.height = 1.25
    _visual = MeshInstance3D.new()
    _visual.mesh = capsule
    _visual.position.y = 0.65
    var material := StandardMaterial3D.new()
    material.albedo_color = Color(0.2, 0.75, 0.35)
    _visual.material_override = material
    add_child(_visual)
    call_deferred("_choose_destination")


func set_kpis(otif: float, trs: float, stockouts: int) -> void:
    if not is_instance_valid(_visual):
        return

    var material := _visual.material_override as StandardMaterial3D
    if otif >= 90.0 and trs >= 80.0 and stockouts == 0:
        material.albedo_color = Color(0.2, 0.75, 0.35)
        walk_speed = 2.2
    elif otif >= 75.0 and trs >= 65.0:
        material.albedo_color = Color(0.95, 0.68, 0.15)
        walk_speed = 1.5
    else:
        material.albedo_color = Color(0.85, 0.2, 0.18)
        walk_speed = 0.8


func _physics_process(_delta: float) -> void:
    if not is_instance_valid(_agent):
        return

    if _agent.is_navigation_finished():
        _choose_destination()
        velocity = Vector3.ZERO
    else:
        var next_position := _agent.get_next_path_position()
        var direction := global_position.direction_to(next_position)
        velocity = direction * walk_speed
        velocity.y = 0.0
    move_and_slide()


func _choose_destination() -> void:
    if not is_instance_valid(_agent):
        return
    var x := _rng.randf_range(-8.0, 8.0)
    var z := _rng.randf_range(-5.0, 5.0)
    _agent.target_position = Vector3(x, 0.0, z)

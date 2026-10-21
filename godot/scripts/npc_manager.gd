extends Node3D

@export_range(1, 12) var npc_count: int = 4

var _workers: Array[WorkerNPC] = []


func _ready() -> void:
    _create_navigation_region()
    for index in range(npc_count):
        var worker := WorkerNPC.new()
        worker.name = "Ouvrier_%02d" % (index + 1)
        add_child(worker)
        worker.position = Vector3(-4.5 + float(index) * 3.0, 0.0, 0.0)
        _workers.append(worker)


func apply_state(game_state: Dictionary) -> void:
    var kpis: Dictionary = game_state.get("kpis", {})
    var otif := float(kpis.get("otif", 0.0))
    var trs := float(kpis.get("trs", 0.0))
    var stockouts := int(kpis.get("stockouts", 0))
    for worker in _workers:
        worker.set_kpis(otif, trs, stockouts)


func _create_navigation_region() -> void:
    var navigation_mesh := NavigationMesh.new()
    navigation_mesh.agent_radius = 0.25
    navigation_mesh.vertices = PackedVector3Array([
        Vector3(-10.0, 0.0, -7.0),
        Vector3(10.0, 0.0, -7.0),
        Vector3(10.0, 0.0, 7.0),
        Vector3(-10.0, 0.0, 7.0),
    ])
    navigation_mesh.add_polygon(PackedInt32Array([0, 1, 2, 3]))

    var region := NavigationRegion3D.new()
    region.navigation_mesh = navigation_mesh
    add_child(region)

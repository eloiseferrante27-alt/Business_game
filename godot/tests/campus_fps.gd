extends Node
## Mesure de QA (critère de T5 : 45 images/s) : campus de la fixture --fixture=<nom> (défaut campus3), caméra libre
## en vue d'ensemble, tout le campus visible. Fenêtre et GPU requis (pas --headless).
##   Godot.exe --path godot res://tests/campus_fps.tscn -- --fixture=campus3 [--height=70] [--back=62]

const WORLD := preload("res://scenes/world/world.tscn")


func _ready() -> void:
	var args := {}
	for arg in OS.get_cmdline_user_args():
		var pair := arg.trim_prefix("--").split("=", true, 1)
		args[pair[0]] = pair[1] if pair.size() > 1 else ""
	var name := str(args.get("fixture", "campus3"))
	var loaded := {}
	for kind in ["spec", "state"]:
		loaded[kind] = JSON.parse_string(FileAccess.get_file_as_string("res://scenes/tools/fixtures/%s_%s.json" % [name, kind]))
	var spec: Dictionary = loaded["spec"]
	Session.open({"id": "fixture-%s" % name, "name": name, "status": "running", "join_code": "EXEMPLE", "is_manager": true,
		"my_role": null, "members": [], "spec": spec, "state": loaded["state"], "game_title": spec["meta"]["title"]})
	var world := WORLD.instantiate() as GmixWorld
	add_child(world)
	for connection in Presence.status_changed.get_connections():
		Presence.status_changed.disconnect(connection["callable"])
	get_tree().create_timer(120.0).timeout.connect(func() -> void: get_tree().quit(1))
	while not world.is_navigation_ready():
		await get_tree().process_frame
	for i in 240:
		await get_tree().process_frame
	var camera := Camera3D.new()
	add_child(camera)
	camera.make_current()
	camera.far = 250.0
	camera.position = Vector3(0, float(args.get("height", 70)), -float(args.get("back", 62)))
	camera.look_at(Vector3(0, 0, 4))
	for i in 60:
		await get_tree().process_frame
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	var viewport := get_viewport().get_viewport_rid()
	RenderingServer.viewport_set_measure_render_time(viewport, true)
	var started := Time.get_ticks_msec()
	var frames := 0
	var worst := 0.0
	var gpu_ms := 0.0
	var last := started
	while Time.get_ticks_msec() - started < 5000:
		await get_tree().process_frame
		var now := Time.get_ticks_msec()
		worst = maxf(worst, float(now - last))
		gpu_ms += RenderingServer.viewport_get_measured_render_time_gpu(viewport)
		last = now
		frames += 1
	print("CAMPUS_FPS %s : %.1f im/s, pire image %.0f ms, GPU %.1f ms, %d appels, %d objets" % [name,
		frames / ((last - started) / 1000.0), worst, gpu_ms / maxf(frames, 1.0),
		Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME), Performance.get_monitor(Performance.RENDER_TOTAL_OBJECTS_IN_FRAME)])
	get_tree().quit(0)

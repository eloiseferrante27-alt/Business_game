class_name GmixWorldMap
extends Control
## Carte du monde vue de dessus (outil de base de la tablette) : sites de `spec.world.sites` (usine, fournisseurs,
## client), bâtiments du campus et routes `spec.world.links`, mis à l'échelle de la zone. Lecture seule.

const PAD := 24.0

var world: Dictionary = {}


func _ready() -> void:
	custom_minimum_size = Vector2(0, 480)
	size_flags_horizontal = Control.SIZE_EXPAND_FILL
	resized.connect(queue_redraw)


func _draw() -> void:
	var sites: Array = world.get("sites", [])
	if sites.is_empty():
		draw_string(get_theme_default_font(), Vector2(PAD, PAD * 2), "Carte indisponible pour ce jeu.", HORIZONTAL_ALIGNMENT_LEFT, -1, 16, Ui.TEXT)
		return
	var bounds := Rect2(_rect(sites[0]["area"]))
	for site: Dictionary in sites:
		bounds = bounds.merge(_rect(site["area"]))
	var scale := minf((size.x - 2 * PAD) / maxf(bounds.size.x, 1.0), (size.y - 2 * PAD) / maxf(bounds.size.y, 1.0))
	var origin := Vector2(PAD, PAD) - bounds.position * scale
	var to_screen := func(p: Vector2) -> Vector2: return origin + p * scale
	var font := get_theme_default_font()
	for link: Dictionary in world.get("links", []):
		var points := PackedVector2Array()
		for p: Array in link["points"]:
			points.append(to_screen.call(Vector2(p[0], p[1])))
		draw_polyline(points, Ui.MUTED, 3.0)
	for building: Dictionary in world.get("buildings", []):
		var r := _rect(building["area"])
		draw_rect(Rect2(to_screen.call(r.position), r.size * scale), Color(Ui.ACCENT, 0.25))
	for site: Dictionary in sites:
		var r := _rect(site["area"])
		var box := Rect2(to_screen.call(r.position), r.size * scale)
		var color: Color = Ui.ACCENT if site["kind"] == "usine" else (Ui.WARN if site["kind"] == "fournisseur" else Ui.OK)
		draw_rect(box, Color(color, 0.18))
		draw_rect(box, color, false, 2.0)
		var caption := str(site["label"])
		if site.get("km") != null:
			caption += "\n%s km · %s j" % [GameText.number(site["km"]), GameText.number(site.get("transit_days"))]
		draw_multiline_string(font, box.position + Vector2(6, 20), caption, HORIZONTAL_ALIGNMENT_LEFT, maxf(box.size.x - 12, 60), 15, 4, Ui.TEXT)


static func _rect(area: Array) -> Rect2:
	return Rect2(Vector2(area[0], area[1]), Vector2(area[2] - area[0], area[3] - area[1]))

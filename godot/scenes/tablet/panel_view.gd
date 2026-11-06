class_name GmixPanelView
extends RefCounted
## Rendu générique des panneaux d'une spec (`spec.panels`, modèle Panel de backend/gmix/game/spec.py) : kpis, table,
## gauge, chart, flow. Fonctions pures : une carte (PanelContainer) construite depuis le panneau et l'état public, sans
## règle de jeu. Une source absente ou d'un autre type donne « Donnée absente. » (contrat 0007 annexe §2).
## Les textes sont des Label (pas de BBCode) ; couleurs et polices viennent du thème commun et de UiTokens.

const ABSENT := "Donnée absente."
const CARD_WIDTH := 200  # largeur d'un indicateur : plusieurs par ligne, la rangée passe à la ligne
static var CHART_COLORS: Array = [UiTokens.LIME, UiTokens.INFO, UiTokens.WARN, UiTokens.OK]


## Panneaux de `spec.panels` d'un emplacement et d'un public (`formateur` ou `joueur` ; `tous` convient aux deux).
static func panels_for(spec: Dictionary, placement: String, audience: String) -> Array:
	return (spec.get("panels", []) as Array).filter(
		func(panel: Dictionary) -> bool:
			return panel.get("placement") == placement and panel.get("audience", "joueur") in [audience, "tous"]
	)


## Valeur au bout d'un chemin « a.b.c » de l'état public (null si elle manque).
static func resolve(root: Variant, path: String) -> Variant:
	var node: Variant = root
	for key in path.split("."):
		if node is Dictionary and (node as Dictionary).has(key):
			node = node[key]
		else:
			return null
	return node


static func build(panel: Dictionary, state: Dictionary) -> PanelContainer:
	var card := PanelContainer.new()
	card.size_flags_vertical = Control.SIZE_SHRINK_BEGIN
	var box := Ui.vbox(card, 10)
	box.add_child(Ui.label(str(panel.get("title", "")), 20, Ui.ACCENT, true))
	var data: Variant = resolve(state, str(panel.get("source", "")))
	match panel.get("type"):
		"kpis":
			_kpis(box, panel, data, state)
		"table":
			_table(box, panel, data)
		"gauge":
			_gauge(box, panel, data)
		"chart":
			_chart(box, panel, data, state)
		"flow":
			_flow(box, data)
		_:
			box.add_child(Ui.label(ABSENT, 0, Ui.MUTED, true))
	return card


# --- mise en forme ---------------------------------------------------------------------------------------


static func format_value(value: Variant, column: Dictionary) -> String:
	if value == null:
		return "-"
	match column.get("format", "text"):
		"int":
			return GameText.number(roundi(float(value)))
		"dec1":
			return ("%.1f" % float(value)).replace(".", ",")
		"pct":
			return "%s %%" % GameText.number(value)
		"money":
			return GameText.money(value)
		"minutes":
			return "%s min" % GameText.number(value)
		"state":
			return str((column.get("labels", {}) as Dictionary).get(str(value), value))
	return str(value)


## [couleur, mot] de l'écart à la cible d'une colonne, null sans cible ni valeur. Le mot double la couleur (daltonisme).
static func verdict(column: Dictionary, value: Variant, state: Dictionary) -> Variant:
	var target: Variant = resolve(state, str(column["target"])) if column.get("target") != null else null
	if target == null or value == null:
		return null
	var lower: bool = column.get("better", "higher") == "lower"
	var v := float(value)
	if (v <= float(target)) if lower else (v >= float(target)):
		return [Ui.OK, "cible atteinte"]
	var warn: Variant = column.get("warn")
	if warn != null and not lower and v >= float(warn):
		return [Ui.WARN, "à surveiller"]
	return [Ui.ERROR, "sous la cible" if not lower else "au-dessus de la cible"]


# --- types de panneau ------------------------------------------------------------------------------------


static func _kpis(box: VBoxContainer, panel: Dictionary, data: Variant, state: Dictionary) -> void:
	if not data is Dictionary:
		box.add_child(Ui.label(ABSENT, 0, Ui.MUTED, true))
		return
	var row := Ui.flow(box, 10)
	for column: Dictionary in panel.get("columns", []):
		var value: Variant = (data as Dictionary).get(column["key"])
		var tile := Ui.panel(row)
		tile.custom_minimum_size.x = CARD_WIDTH
		var inner := Ui.vbox(tile, 4)
		inner.add_child(Ui.label(str(column["label"]), 0, Ui.MUTED, true))
		var big := Ui.label(format_value(value, column), 28, Ui.TEXT, true)
		inner.add_child(big)
		var result: Variant = verdict(column, value, state)
		if result != null:
			var target: Variant = resolve(state, str(column["target"]))
			var goal := format_value(target, column)
			inner.add_child(Ui.label("%s · cible %s" % [(result as Array)[1], goal], 0, (result as Array)[0], true))


static func _table(box: VBoxContainer, panel: Dictionary, data: Variant) -> void:
	if not data is Array:
		box.add_child(Ui.label(ABSENT, 0, Ui.MUTED, true))
		return
	var columns: Array = panel.get("columns", [])
	if (data as Array).is_empty() or columns.is_empty():
		box.add_child(Ui.label("Aucune ligne pour l'instant.", 0, Ui.MUTED, true))
		return
	var grid := GridContainer.new()
	grid.columns = columns.size()
	grid.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	grid.add_theme_constant_override("h_separation", 14)
	grid.add_theme_constant_override("v_separation", 6)
	box.add_child(grid)
	for column: Dictionary in columns:
		grid.add_child(_cell(str(column["label"]), Ui.MUTED))
	for item: Variant in data:
		for column: Dictionary in columns:
			var value: Variant = (item as Dictionary).get(column["key"]) if item is Dictionary else null
			grid.add_child(_cell(format_value(value, column), Ui.TEXT))


## Cellule : largeur proportionnelle (les colonnes se partagent la place), texte à la ligne.
static func _cell(text: String, color: Color) -> Label:
	var cell := Ui.label(text, 0, color, true)
	cell.custom_minimum_size.x = 40
	cell.size_flags_stretch_ratio = 1.0
	return cell


static func _gauge(box: VBoxContainer, panel: Dictionary, data: Variant) -> void:
	var columns: Array = panel.get("columns", [])
	if not data is Dictionary or columns.is_empty() or (data as Dictionary).get(columns[0]["key"]) == null:
		box.add_child(Ui.label(ABSENT, 0, Ui.MUTED, true))
		return
	var column: Dictionary = columns[0]
	var value: float = float((data as Dictionary)[column["key"]])
	var bar := ProgressBar.new()
	bar.min_value = float(panel.get("min", 0))
	bar.max_value = float(panel.get("max", 100))
	bar.value = value
	bar.show_percentage = false
	bar.custom_minimum_size = Vector2(0, 20)
	var back := StyleBoxFlat.new()
	back.bg_color = UiTokens.FIELD
	back.set_corner_radius_all(UiTokens.RADIUS_CONTROL)
	var fill := StyleBoxFlat.new()
	fill.bg_color = UiTokens.LIME
	fill.set_corner_radius_all(UiTokens.RADIUS_CONTROL)
	bar.add_theme_stylebox_override("background", back)
	bar.add_theme_stylebox_override("fill", fill)
	box.add_child(Ui.label("%s : %s" % [column["label"], format_value(value, column)], 24, Ui.TEXT, true))
	box.add_child(bar)
	box.add_child(Ui.label("Échelle de %s à %s" % [GameText.number(bar.min_value), GameText.number(bar.max_value)], 0, Ui.MUTED, true))


static func _chart(box: VBoxContainer, panel: Dictionary, data: Variant, state: Dictionary) -> void:
	var columns: Array = panel.get("columns", [])
	if not data is Array or (data as Array).is_empty() or columns.is_empty():
		box.add_child(Ui.label(ABSENT if not data is Array else "Aucune semaine jouée.", 0, Ui.MUTED, true))
		return
	var chart := LineChart.new()
	chart.custom_minimum_size = Vector2(0, 180)
	chart.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	for i in columns.size():
		var column: Dictionary = columns[i]
		var target: Variant = resolve(state, str(column["target"])) if column.get("target") != null else null
		chart.series.append({
			"color": CHART_COLORS[i % CHART_COLORS.size()],
			"values": (data as Array).map(func(row: Variant) -> Variant: return (row as Dictionary).get(column["key"])),
			"target": target,
		})
	chart.weeks = (data as Array).map(func(row: Variant) -> int: return int((row as Dictionary).get("week", 0)))
	box.add_child(chart)
	var legend := Ui.flow(box, 16)
	for i in columns.size():
		var color: Color = CHART_COLORS[i % CHART_COLORS.size()]
		var target: Variant = resolve(state, str(columns[i]["target"])) if columns[i].get("target") != null else null
		var text := "━ %s" % columns[i]["label"]
		if target != null:
			text += " (cible en pointillés : %s)" % format_value(target, columns[i])
		legend.add_child(Ui.label(text, 0, color))


static func _flow(box: VBoxContainer, data: Variant) -> void:
	if not data is Dictionary or not (data as Dictionary).get("nodes") is Array:
		box.add_child(Ui.label(ABSENT, 0, Ui.MUTED, true))
		return
	var labels := {}
	var chips := Ui.flow(box, 8)
	for node: Dictionary in (data as Dictionary)["nodes"]:
		labels[node.get("id")] = str(node.get("label", node.get("id")))
		var chip := Ui.panel(chips)
		var inner := Ui.vbox(chip, 2)
		inner.add_child(Ui.label(str(labels[node.get("id")]), 0, Ui.TEXT))
		var detail := "%s unité(s)" % GameText.number(node.get("count"))
		if node.get("state") != null:
			detail = "%s · %s" % [GameText.MACHINE_STATES.get(str(node["state"]), str(node["state"])), detail]
		inner.add_child(Ui.label(detail, 0, Ui.MUTED))
	for edge: Dictionary in (data as Dictionary).get("edges", []):
		box.add_child(Ui.label(
			"%s  →  %s : %s unité(s) au dernier tour" % [labels.get(edge.get("from"), edge.get("from")), labels.get(edge.get("to"), edge.get("to")), GameText.number(edge.get("count"))],
			0, Ui.TEXT, true
		))


## Courbes par semaine (une série par colonne) avec la cible en pointillés ; échelle ajustée aux valeurs.
class LineChart extends Control:
	var series: Array = []  # [{color, values, target, partial (facultatif : seuil partiel)}]
	var weeks: Array = []
	var marks: Array = []  # semaines d'aléa : filet vertical (le texte « S3 : titre » est dans la légende)

	func _draw() -> void:
		var left := 52.0
		var bottom := 26.0
		var area := Rect2(left, 8.0, size.x - left - 12.0, size.y - bottom - 8.0)
		var low := INF
		var high := -INF
		for one: Dictionary in series:
			for v: Variant in one["values"]:
				if v != null:
					low = minf(low, float(v))
					high = maxf(high, float(v))
			for bound: Variant in [one["target"], one.get("partial")]:
				if bound != null:
					low = minf(low, float(bound))
					high = maxf(high, float(bound))
		if low == INF:
			return
		if is_equal_approx(low, high):
			low -= 1.0
			high += 1.0
		var pad := (high - low) * 0.1
		low -= pad
		high += pad
		var font := get_theme_default_font()
		var px := Ui.MIN_FONT
		draw_rect(area, UiTokens.FIELD)
		draw_string(font, Vector2(0, area.position.y + px), GameText.number(high), HORIZONTAL_ALIGNMENT_LEFT, left - 6.0, px, Ui.MUTED)
		draw_string(font, Vector2(0, area.end.y), GameText.number(low), HORIZONTAL_ALIGNMENT_LEFT, left - 6.0, px, Ui.MUTED)
		var count := weeks.size()
		var step := area.size.x / maxf(count, 1.0)
		var every := maxi(1, ceili(float(count) / maxf(floorf(area.size.x / 40.0), 1.0)))  # une graduation tous les 40 px au plus
		for i in count:
			var x := area.position.x + step * (i + 0.5)
			if i % every == 0:
				draw_string(font, Vector2(x - 12.0, size.y - 4.0), "S%d" % int(weeks[i]), HORIZONTAL_ALIGNMENT_LEFT, 40.0, px, Ui.MUTED)
		for mark: Variant in marks:
			var at := weeks.find(int(mark))
			if at >= 0:
				var mx := area.position.x + step * (at + 0.5)
				draw_line(Vector2(mx, area.position.y), Vector2(mx, area.end.y), Color(Ui.WARN, 0.5), 2.0)
		for one: Dictionary in series:
			var color: Color = one["color"]
			if one.get("partial") != null:
				var py := _y(float(one["partial"]), area, low, high)
				draw_dashed_line(Vector2(area.position.x, py), Vector2(area.end.x, py), Color(color, 0.35), 2.0, 3.0)
			if one["target"] != null:
				var ty := _y(float(one["target"]), area, low, high)
				draw_dashed_line(Vector2(area.position.x, ty), Vector2(area.end.x, ty), Color(color, 0.7), 2.0, 8.0)
			var points := PackedVector2Array()
			for i in count:
				if one["values"][i] != null:
					points.append(Vector2(area.position.x + step * (i + 0.5), _y(float(one["values"][i]), area, low, high)))
			if points.size() > 1:
				draw_polyline(points, color, 3.0, true)
			for point in points:
				draw_circle(point, 4.0, color)

	func _y(value: float, area: Rect2, low: float, high: float) -> float:
		return area.end.y - (value - low) / (high - low) * area.size.y

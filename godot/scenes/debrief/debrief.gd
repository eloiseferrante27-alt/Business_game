class_name GmixDebrief
extends RefCounted
## Débrief J3 (ADR 0012 §2), même écran pour le joueur, le formateur et l'admin : un verdict par critère, une courbe par critère
## (`criteria[].series`) avec cible et seuil partiel, les aléas, les causes tirées de `log[].kind`, puis leçons, notions et sources.
## Débrief comparé : mêmes courbes, une série par équipe. `entries` : [{name, report}] (une seule entrée hors groupe).
## Tout texte de l'API passe par GameText.esc avant un RichTextLabel ; les Label n'interprètent pas le BBCode.

const VERDICTS := {"atteint": "atteint", "partiel": "partiel", "non_atteint": "non atteint", "sans_objet": "sans objet"}
static var VERDICT_COLORS := {"atteint": UiTokens.OK, "partiel": UiTokens.WARN, "non_atteint": UiTokens.ERROR, "sans_objet": UiTokens.MUTED}
const CAUSES := [["decision", "Vos décisions"], ["auto", "Pilote automatique"], ["alea", "Ce que le hasard a imposé"]]


## Fenêtre de lecture défilante, dimensionnée sur la zone visible.
static func show_window(parent: Node, title: String, entries: Array, group_id := "") -> void:
	var dialog := AcceptDialog.new()
	dialog.title = title
	dialog.ok_button_text = "Fermer"
	var column := Ui.scroll_list(dialog, 160)
	column.get_parent().custom_minimum_size.x = 320
	fill(column, entries, group_id)
	dialog.confirmed.connect(dialog.queue_free)
	dialog.canceled.connect(dialog.queue_free)
	parent.add_child(dialog)
	dialog.popup_centered_clamped(Vector2i(1100, 720), Ui.DIALOG_RATIO)


## Débrief comparé d'un groupe ; renvoie le message d'erreur (vide si la fenêtre s'est ouverte).
static func show_group(parent: Node, group_id: String) -> String:
	var res: Dictionary = await Api.get_json("/api/v1/groups/%s/debrief" % group_id)
	if not res["ok"]:
		return "Le débrief comparé s'ouvre quand toutes les équipes ont fini leur partie." if res["status"] == 409 else str(res["error"])
	var entries: Array = (res["data"]["teams"] as Array).map(func(team: Dictionary) -> Dictionary: return {"name": str(team["name"]), "report": team["debrief"]})
	show_window(parent, "Débrief comparé : %s" % res["data"]["name"], entries)
	return ""


static func fill(box: Control, entries: Array, group_id := "") -> void:
	Ui.clear(box)
	if entries.is_empty():
		return
	var solo := entries.size() == 1
	var first: Dictionary = entries[0]["report"]
	var criteria: Array = first.get("criteria", [])
	if not criteria.is_empty():
		box.add_child(Ui.label("Critères de réussite" if solo else "Courbes comparées", 24))
	for criterion: Dictionary in criteria:
		_criterion(box, criterion, entries)
	for entry: Dictionary in entries:
		if not solo:
			box.add_child(Ui.label(str(entry["name"]), 24, Ui.ACCENT))
		_body(box, entry["report"])
	if not group_id.is_empty() and solo:
		var button := Ui.button("Débrief comparé", func() -> void:
			var error := await show_group(box, group_id)
			if not error.is_empty():
				box.add_child(Ui.label(error, 0, Ui.ERROR, true))
		)
		button.name = "DebriefCompareButton"
		button.size_flags_horizontal = Control.SIZE_SHRINK_BEGIN
		box.add_child(button)


static func _criterion(box: Control, criterion: Dictionary, entries: Array) -> void:
	var solo := entries.size() == 1
	var unit := str(criterion.get("unit", ""))
	var head := str(criterion["label"])
	if solo:
		head += " : %s" % VERDICTS.get(str(criterion["verdict"]), str(criterion["verdict"]))
		if criterion["verdict"] != "atteint" and criterion.get("worst_week") != null:
			head += " (S%d%s)" % [int(criterion["worst_week"]), " : %s" % criterion["event"] if criterion.get("event") != null else ""]
	box.add_child(Ui.label(head, 0, VERDICT_COLORS.get(str(criterion["verdict"]), Ui.TEXT) if solo else Ui.TEXT, true))
	var chart := GmixPanelView.LineChart.new()
	chart.custom_minimum_size = Vector2(0, 170)
	chart.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var events := {}  # semaine -> titres, tous groupes confondus
	var legend := PackedStringArray()
	var missing := false
	for i in entries.size():
		var report: Dictionary = entries[i]["report"]
		for event: Dictionary in report.get("events", []):
			events[int(event["week"])] = str(event["title"])
		var mine := _find(report.get("criteria", []), str(criterion["id"]))
		var values: Variant = mine.get("series")
		var line := "%s%s" % ["" if solo else "%s : " % entries[i]["name"], GameText.kpi_value(unit, mine.get("final"))]
		if not solo:
			line += " (%s)" % VERDICTS.get(str(mine.get("verdict", "sans_objet")), "")
		legend.append(line)
		if values is Array and not (values as Array).is_empty():
			chart.series.append({"color": GmixPanelView.CHART_COLORS[i % GmixPanelView.CHART_COLORS.size()], "values": values, "target": criterion["target"], "partial": criterion.get("partial")})
			chart.weeks = range(1, (values as Array).size() + 1)
		else:
			missing = true
	chart.marks = events.keys()
	if chart.series.is_empty():
		box.add_child(Ui.label("Courbe indisponible : la série de ce critère n'a pas été fournie.", 0, Ui.MUTED, true))
	else:
		box.add_child(chart)
	var flow := Ui.flow(box, 16)
	for i in legend.size():
		flow.add_child(Ui.label("━ %s" % legend[i], 0, GmixPanelView.CHART_COLORS[i % GmixPanelView.CHART_COLORS.size()]))
	var op := "≥" if criterion["op"] == ">=" else "≤"
	var marks := "cible %s %s (pointillés)" % [op, GameText.kpi_value(unit, criterion["target"])]
	if criterion.get("partial") != null:
		marks += ", partiel %s %s" % [op, GameText.kpi_value(unit, criterion["partial"])]
	box.add_child(Ui.label(marks + (". Courbe incomplète." if missing and not chart.series.is_empty() else ""), 0, Ui.MUTED, true))
	if not events.is_empty():
		var weeks: Array = events.keys()
		weeks.sort()
		box.add_child(Ui.label("Aléas : " + " · ".join(weeks.map(func(w: int) -> String: return "S%d : %s" % [w, events[w]])), 0, Ui.WARN, true))


static func _find(criteria: Array, id: String) -> Dictionary:
	for item: Dictionary in criteria:
		if item.get("id") == id:
			return item
	return {}


## Causes en trois colonnes (`log[].kind`), puis leçons, notions, historique et valeurs non sourcées.
static func _body(box: Control, report: Dictionary) -> void:
	var log: Array = report.get("log", [])
	if not log.is_empty():
		box.add_child(Ui.label("Causes", 24))
		var columns := Ui.hbox(box, 14)
		for cause: Array in CAUSES:
			var column := Ui.vbox(columns, 6)
			column.size_flags_horizontal = Control.SIZE_EXPAND_FILL
			column.custom_minimum_size.x = 120
			column.add_child(Ui.label(cause[1], 0, Ui.ACCENT, true))
			var rows := log.filter(func(e: Dictionary) -> bool: return str(e.get("kind", "decision")) == cause[0])
			if rows.is_empty():
				column.add_child(Ui.label("Aucune.", 0, Ui.MUTED, true))
			for e: Dictionary in rows:
				var who := ""
				if cause[0] == "decision" and e.get("name") != null:
					who = "%s (%s) : " % [e["name"], e.get("by", "")]
				column.add_child(Ui.label("S%d · %s%s" % [int(e["week"]), who, e["summary"]], 0, Ui.TEXT, true))
	var text := Ui.rich()
	text.text = GameText.debrief_bbcode(report, false)
	box.add_child(text)

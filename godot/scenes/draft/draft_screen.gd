class_name GmixDraftScreen
extends Control
## F3 : brouillon d'un jeu conçu par l'IA (ADR 0010 §4, ADR 0012 §1). Une carte par section ; « Régénérer » refait la section
## (consigne facultative) et laisse le reste du jeu intact ; le jeu repasse toujours en brouillon, il faut le republier.

signal navigate(target: String)

## Posé par l'écran appelant avant navigate("draft").
static var current_id := ""

const POLL_S := 2.0
const STAGES := {"brief": "lecture du brief", "concept": "idée générale", "simulation": "construction de la simulation", "checks": "vérifications", "done": "terminé"}
const FALLBACK_TEXT := "Le modèle n'a pas pu proposer mieux, la version précédente est conservée."

var _game: Dictionary = {}
var _title: Label
var _status: Label
var _notice: VBoxContainer  # résultat de la dernière régénération, retouches retirées
var _progress: VBoxContainer
var _cards: VBoxContainer
var _publish: Button
var _busy := false


## « 1 min 05 s » pour une durée en secondes.
static func elapsed(seconds: int) -> String:
	return "%d s" % seconds if seconds < 60 else "%d min %02d s" % [seconds / 60, seconds % 60]


func _ready() -> void:
	var column := Ui.vbox(Ui.screen_margin(self), 12)
	var header := Ui.flow(column)
	_title = Ui.label("", 26, Color.WHITE, true)
	_title.custom_minimum_size.x = 420
	header.add_child(_title)
	var full := Ui.button("Relecture complète", _read_all)
	full.name = "ReadAllButton"
	header.add_child(full)
	_publish = Ui.button("Publier", _publish_game, true, "play")
	_publish.name = "PublishButton"
	header.add_child(_publish)
	var back := Ui.button("Retour à l'accueil", func() -> void: navigate.emit("home"))
	back.name = "BackButton"
	header.add_child(back)
	_status = Ui.label("", 0, Ui.ACCENT, true)
	_status.name = "DraftStatus"
	column.add_child(_status)
	_notice = Ui.vbox(column, 6)
	_progress = Ui.vbox(column, 6)
	_cards = Ui.scroll_list(column, 120)
	_load()


func _load() -> void:
	var res: Dictionary = await Api.get_json("/api/v1/games/%s" % current_id)
	if not res["ok"]:
		_status.text = res["error"]
		return
	_game = res["data"]
	_show_game()


func _show_game() -> void:
	var spec: Dictionary = _game["spec"] if _game.get("spec") is Dictionary else {}
	var params: Dictionary = spec.get("params", {})
	var meta: Dictionary = spec.get("meta", {})
	var status := str(_game.get("status", ""))
	_title.text = "Brouillon : %s" % _game.get("title", "") if status != "ready" else "Jeu publié : %s" % _game.get("title", "")
	_publish.disabled = status != "draft"
	Ui.clear(_cards)
	if spec.is_empty():
		_status.text = "Le jeu n'a pas encore de spec : actualisez dans un instant."
		return
	var company := str(params.get("company_name", meta.get("company", "")))
	_card("entreprise", "Entreprise", [
		company, "Secteur : %s" % meta.get("theme_label", ""), str(meta.get("pitch", ""))], true)
	var events: Dictionary = {}
	for event: Dictionary in spec.get("events", []):
		events[event["id"]] = event["title"]
	var plan := PackedStringArray()
	for planned: Dictionary in params.get("event_plan", []):
		plan.append("S%d : %s" % [int(planned["week"]), events.get(planned["event_id"], planned["event_id"])])
	var goals := PackedStringArray()
	for criterion: Dictionary in spec.get("criteria", []):
		goals.append("%s %s %s" % [criterion["label"], str(criterion["op"]), GameText.number(criterion["target"])])
	_card("objectifs", "Objectifs et aléas", [
		"Niveau : %s · %d semaines · aléas : %s" % [meta.get("difficulty_label", ""), int(meta.get("weeks", 0)), params.get("events", "")],
		"Aléas imposés : %s" % ", ".join(plan) if not plan.is_empty() else "Aucun aléa imposé à une semaine précise.",
		"Critères : %s" % "; ".join(goals)], true)
	var people := PackedStringArray()
	for agent: Dictionary in spec.get("agents", []):
		people.append("%s, %s" % [agent["name"], agent["job"]])
	_card("personnages", "Personnages", ["Caractère : %s" % params.get("agent_tone", ""), "; ".join(people)], true)
	var products := PackedStringArray()
	for product: Dictionary in spec.get("products", []):
		products.append(str(product["name"]))
	var modules := PackedStringArray()
	for module: Dictionary in spec.get("modules", []):
		modules.append(str(module["title"]))
	_card("", "Produits, fournisseurs et rôles", [
		"Produits : %s" % ", ".join(products), "Postes joués : %s" % ", ".join(modules),
		"Cette partie se règle dans les paramètres du jeu, pas par régénération."], false)
	_show_dropped()


func _show_dropped() -> void:
	var review: Dictionary = _game["review"] if _game.get("review") is Dictionary else {}
	var dropped: Array = review["dropped"] if review.get("dropped") is Array else []
	for child in _notice.get_children():
		if child.name == "DroppedNotice":
			child.queue_free()
	if dropped.is_empty():
		return
	var lines := PackedStringArray()
	for entry: Variant in dropped:
		if entry is Dictionary:
			var detail := PackedStringArray()
			for key: String in (entry as Dictionary):
				if key != "index":
					detail.append(str(entry[key]))
			lines.append("n° %d%s" % [int(entry.get("index", 0)) + 1, " (%s)" % ", ".join(detail) if not detail.is_empty() else ""])
	var label := Ui.label("Retouches du plan qui ne tiennent plus avec la nouvelle version, retirées : %s." % "; ".join(lines), 0, Ui.WARN, true)
	label.name = "DroppedNotice"
	_notice.add_child(label)


func _card(section: String, caption: String, lines: Array, can_regenerate: bool) -> void:
	var card := Ui.panel(_cards)
	card.name = "Card_%s" % (section if not section.is_empty() else "parametres")
	var box := Ui.vbox(card, 8)
	box.add_child(Ui.label(caption, 22, Ui.ACCENT, true))
	for line: Variant in lines:
		if not str(line).is_empty():
			box.add_child(Ui.label(str(line), 0, Color.WHITE, true))
	if not can_regenerate:
		return
	var row := Ui.flow(box)
	var note := Ui.field("Consigne facultative", false, 360)
	note.name = "Note_%s" % section
	note.max_length = 300
	row.add_child(note)
	var button := Ui.button("Régénérer", func() -> void: _regenerate(section, note.text.strip_edges()), false, "refresh")
	button.name = "Regenerate_%s" % section
	row.add_child(button)


func _regenerate(section: String, note: String) -> void:
	if _busy:
		return
	var body := {"section": section}
	if not note.is_empty():
		body["note"] = note
	_status.text = ""
	_busy = true  # avant le POST : un double clic donnerait un 409
	var res: Dictionary = await Api.post_json("/api/v1/games/%s/design/regenerate" % current_id, body)
	if not res["ok"]:
		_busy = false
		_status.text = res["error"]  # 409 : jeu non conçu par l'IA, session en cours ou conception active ; 503 : bus indisponible
		return
	await _follow(section)


## Interroge le job toutes les 2 s (étape, pourcentage, temps écoulé), puis annonce le résultat.
func _follow(section: String) -> void:
	_busy = true
	var started := Time.get_ticks_msec()
	var job: Dictionary = {}
	while is_inside_tree():
		var res: Dictionary = await Api.get_json("/api/v1/games/%s/job" % current_id)
		if not res["ok"]:
			_status.text = "Suivi de la régénération impossible : %s" % res["error"]
			break
		job = res["data"]
		if job["status"] == "succeeded" or job["status"] == "failed":
			break
		_show_progress(job, (Time.get_ticks_msec() - started) / 1000)
		await get_tree().create_timer(POLL_S).timeout
	_busy = false
	Ui.clear(_progress)
	if job.is_empty() or not is_inside_tree():
		return
	await _load()
	var usage: Dictionary = job["usage"].get("design", {}) if job.get("usage") is Dictionary and job["usage"].get("design") is Dictionary else {}
	if job["status"] == "failed":
		_status.text = "La régénération n'a pas abouti : %s" % str(job.get("error", "")).strip_edges()
	elif bool(usage.get("fallback", false)):
		_status.text = FALLBACK_TEXT
	else:
		_status.text = "Section « %s » régénérée : le reste du jeu n'a pas changé. Le jeu est repassé en brouillon, republiez-le." % section


func _show_progress(job: Dictionary, seconds: int) -> void:
	Ui.clear(_progress)
	var percent := int(job.get("progress", 0))
	_progress.add_child(Ui.label("Régénération en cours : %s (%d %%) · %s" % [STAGES.get(str(job.get("stage", "")), "en attente du service"), percent, elapsed(seconds)], 0, Ui.ACCENT, true))
	var bar := ProgressBar.new()
	bar.max_value = 100
	bar.value = percent
	bar.show_percentage = false
	bar.custom_minimum_size.y = 16
	_progress.add_child(bar)


func _publish_game() -> void:
	var res: Dictionary = await Api.post_json("/api/v1/games/%s/publish" % current_id, {})
	if not res["ok"]:
		_status.text = res["error"]  # 409 : message + raisons
		return
	_status.text = "Jeu publié : vous pouvez lancer une session depuis « Mes jeux »."
	await _load()


func _read_all() -> void:
	if not _game.is_empty():
		Ui.show_text(self, str(_game.get("title", "")), GameText.game_bbcode(_game))

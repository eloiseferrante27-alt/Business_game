class_name GmixRoundBar
extends VBoxContainer
## Appel « prêt » de la semaine (annexe 0010 §1), dans la tablette et la salle du lobby. Joueur : se dire prêt et voter
## sur les absents. Formateur : qui est prêt, pas prêt ou déconnecté ; pause ; aléa ; avance forcée sans les absents.
## Données : `Session.round_view()` ; l'API décide de l'avance, rien n'est calculé ici. Une erreur de l'API part dans
## `failed` : l'écran hôte l'affiche. Les confirmations s'ouvrent sur le parent (la barre se reconstruit).

signal failed(message: String)

var _key := ""


func _ready() -> void:
	Session.lobby_changed.connect(_render)
	Session.round_changed.connect(_render)
	_render()


func _render() -> void:
	var rnd := Session.round_view()
	var state := Session.state()
	var manager := Session.is_manager()
	var key := JSON.stringify([rnd, state.get("status"), state.get("week"), manager, Session.lobby.get("my_role"), Session.lobby.get("members")])
	if key == _key:
		return  # rien n'a changé : la liste d'aléas garde son choix
	_key = key
	Ui.clear(self)
	visible = state.get("status") == "running" and not rnd.is_empty() and (manager or Session.lobby.get("my_role") != null)
	if not visible:
		return
	if manager:
		_trainer(rnd)
	else:
		_player(rnd)


func _player(rnd: Dictionary) -> void:
	var me := str(Api.user.get("id", ""))
	var is_ready: bool = me in rnd.get("ready", [])
	var row := Ui.flow(self, 10)
	row.add_child(Ui.button("Je ne suis plus prêt" if is_ready else "Prêt pour la semaine suivante", _set_ready.bind({"ready": not is_ready}), not is_ready))
	add_child(Ui.label(_summary(rnd), 0, Ui.MUTED, true))
	var vote: Dictionary = rnd.get("vote", {})
	if not vote.get("open", false) or not me in rnd.get("connected", []):
		return
	add_child(Ui.label("Absent : %s. Les autres sont prêts : faut-il l'attendre ?" % _names(rnd.get("absent", [])), 0, Ui.WARN, true))
	var mine: Variant = (vote.get("ballots", {}) as Dictionary).get(me)
	var choices := Ui.flow(self, 10)
	choices.add_child(Ui.button("Ignorer : pilote automatique (%d)" % int(vote.get("ignore", 0)), _set_ready.bind({"ready": true, "absent": "ignore"}), mine == "ignore"))
	choices.add_child(Ui.button("Attendre son retour (%d)" % int(vote.get("wait", 0)), _set_ready.bind({"ready": true, "absent": "wait"}), mine == "wait"))
	add_child(Ui.label("Ignorer demande la majorité des %d joueurs connectés ; l'égalité fait attendre." % int(vote.get("voters", 0)), 0, Ui.MUTED, true))


func _trainer(rnd: Dictionary) -> void:
	add_child(Ui.label(_summary(rnd), 0, Ui.ACCENT, true))
	var lines := PackedStringArray()
	for member: Dictionary in Session.lobby.get("members", []):
		if member.get("game_role") == null:
			continue
		var user_id := str(member["user_id"])
		var where := "déconnecté" if user_id in rnd.get("absent", []) else "prêt" if user_id in rnd.get("ready", []) else "pas prêt"
		lines.append("%s (%s) : %s" % [member["display_name"], GameText.role_title(Session.spec(), member["game_role"]), where])
	add_child(Ui.label("  ·  ".join(lines) if not lines.is_empty() else "Aucun joueur n'a encore pris de rôle.", 0, Ui.MUTED, true))
	var vote: Dictionary = rnd.get("vote", {})
	if vote.get("open", false):
		add_child(Ui.label("Vote sur les absents : ignorer %d, attendre %d, sur %d connectés." % [int(vote.get("ignore", 0)), int(vote.get("wait", 0)), int(vote.get("voters", 0))], 0, Ui.WARN, true))
	var paused := bool(rnd.get("paused", false))
	var events: Array = Session.spec().get("events", [])
	var select: OptionButton = null
	if not events.is_empty():
		select = Ui.select(events.map(func(event: Dictionary) -> String: return str(event["title"])))
		select.tooltip_text = "Aléa à déclencher"
		add_child(select)  # pleine largeur : un titre d'aléa long ne se tronque pas
	var row := Ui.flow(self, 10)
	row.add_child(Ui.button("Reprendre la partie" if paused else "Mettre en pause", _pause.bind(not paused)))
	if select != null:
		row.add_child(Ui.button("Déclencher l'aléa", func() -> void: _confirm_event(events[select.selected])))
	if not (rnd.get("absent", []) as Array).is_empty():
		row.add_child(Ui.button("Forcer sans les absents", _confirm_force))


## « 2/3 prêts · la semaine avance quand tous sont prêts » ; pause et mode manuel le disent.
func _summary(rnd: Dictionary) -> String:
	var text := "Semaine %s : %d/%d prêts" % [GameText.number(rnd.get("week")), int(rnd.get("ready_count", 0)), int(rnd.get("expected_count", 0))]
	if bool(rnd.get("paused", false)):
		return text + " · partie en pause par le formateur"
	if rnd.get("advance_mode") == "manual":
		return text + " · le formateur fait avancer la semaine"
	return text + " · la semaine avance quand tous sont prêts"


func _names(user_ids: Array) -> String:
	var names := PackedStringArray()
	for member: Dictionary in Session.lobby.get("members", []):
		if str(member["user_id"]) in user_ids:
			names.append(str(member["display_name"]))
	return ", ".join(names) if not names.is_empty() else "un joueur"


func _set_ready(body: Dictionary) -> void:
	var res: Dictionary = await Api.post_json(Session.url("/ready"), body)
	if not res["ok"]:
		failed.emit(res["error"])
		return
	Session.set_round(res["data"]["round"])
	Session.apply_state(res["data"]["state"])


func _pause(paused: bool) -> void:
	var res: Dictionary = await Api.post_json(Session.url("/pause"), {"paused": paused})
	if not res["ok"]:
		failed.emit(res["error"])
		return
	Session.set_round(res["data"]["round"])


func _confirm_event(event: Dictionary) -> void:
	Ui.confirm(
		get_parent() as Control, "Déclencher un aléa",
		"« %s » remplace l'aléa annoncé et s'appliquera à la prochaine semaine simulée. %s" % [event["title"], event["description"]],
		"Déclencher", _post_state.bind("/event", {"event_id": event["id"]})
	)


func _confirm_force() -> void:
	Ui.confirm(
		get_parent() as Control, "Forcer la semaine",
		"Absents : %s. Leurs départements passent en pilote automatique pour cette semaine, puis la semaine est simulée. Continuer ?" % _names(Session.round_view().get("absent", [])),
		"Forcer", _post_state.bind("/advance", {"ignore_absent": true})
	)


func _post_state(route: String, body: Dictionary) -> void:
	var res: Dictionary = await Api.post_json(Session.url(route), body)
	if not res["ok"]:
		failed.emit(res["error"])
		return
	Session.apply_state(res["data"]["state"])

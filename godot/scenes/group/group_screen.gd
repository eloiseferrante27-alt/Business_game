class_name GmixGroupScreen
extends Control
## Groupe d'équipes (ADR 0011 §2). Formateur : code du groupe, cartes des équipes, débrief comparé. Joueur : choix de son
## équipe (arrivée par le code du groupe) ou retour dans la sienne. Une équipe se joue comme un lobby (écran « lobby »).

signal navigate(target: String)

## Posés par l'écran appelant avant navigate("group") : groupe à afficher, et code saisi si le joueur doit choisir son équipe.
static var current_id := ""
static var join_code := ""

const TEAM_STATUS := {"ready": "ouverte", "running": "en cours", "closed": "terminée", "draft": "brouillon"}

var _title: Label
var _subtitle: Label
var _status: Label
var _code: Label
var _code_row: Control
var _teams: VBoxContainer
var _group: Dictionary = {}


func _ready() -> void:
	var column := Ui.vbox(Ui.screen_margin(self), 14)
	var header := Ui.hbox(column)
	var heading := Ui.vbox(header, 2)
	heading.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_title = Ui.label("", 26, Color.WHITE, true)
	heading.add_child(_title)
	_subtitle = Ui.label("", 20, Ui.ACCENT, true)
	heading.add_child(_subtitle)
	var refresh := Ui.button("Actualiser", _load)
	refresh.name = "RefreshButton"
	header.add_child(refresh)
	var debrief := Ui.button("Débrief comparé", _debrief)
	debrief.name = "GroupDebriefButton"
	header.add_child(debrief)
	var back := Ui.button("Retour à l'accueil", func() -> void: navigate.emit("home"))
	back.name = "BackButton"
	header.add_child(back)
	_status = Ui.label("", 0, Ui.ACCENT, true)
	column.add_child(_status)
	var code_panel := Ui.panel(column)
	_code_row = code_panel
	var code_box := Ui.hbox(code_panel)
	_code = Ui.label("", 30, Ui.ACCENT, true)
	_code.name = "GroupCode"
	_code.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	code_box.add_child(_code)
	var copy := Ui.button("Copier le code", func() -> void: DisplayServer.clipboard_set(str(_group.get("join_code", ""))), false, "copy")
	copy.name = "CopyCodeButton"
	code_box.add_child(copy)
	code_panel.visible = false
	_teams = Ui.scroll_list(Ui.panel(column), 120)
	_teams.get_parent().get_parent().size_flags_vertical = Control.SIZE_EXPAND_FILL
	_load()


func _load() -> void:
	var res: Dictionary
	if join_code.is_empty():
		res = await Api.get_json("/api/v1/groups/%s" % current_id)
	else:
		res = await Api.post_json("/api/v1/groups/join", {"code": join_code})
	if not res["ok"]:
		_status.text = res["error"]
		return
	_group = res["data"]
	_show_group()


func _show_group() -> void:
	var manager: bool = _group.get("is_manager", false)
	var choosing := not join_code.is_empty() and str(_group.get("my_team", "")).is_empty()
	_title.text = str(_group.get("name", ""))
	_subtitle.text = str(_group.get("game_title", "") if _group.get("game_title") != null else "")
	_code_row.visible = manager and _group.get("join_code") != null
	_code.text = "Code du groupe : %s" % _group.get("join_code", "")
	_status.text = "Choisissez votre équipe : vous y resterez pour toute la partie." if choosing else ""
	Ui.clear(_teams)
	for team: Dictionary in _group.get("teams", []):
		var mine := str(team["lobby_id"]) == str(_group.get("my_team", ""))
		var row := Ui.vbox(_teams, 6)
		row.name = "Team_%s" % str(team["name"]).validate_node_name()
		var names := ", ".join((team["players"] as Array).map(func(p: Dictionary) -> String: return str(p["display_name"])))
		var week: Variant = team.get("week")
		var text := "%s%s  ·  %d/%d joueurs  ·  %s" % [team["name"], " (votre équipe)" if mine else "", (team["players"] as Array).size(), int(team["max_players"]), TEAM_STATUS.get(team["status"], team["status"])]
		if week != null:
			text += "  ·  semaine %d" % int(week)
		row.add_child(Ui.label(text, 0, Ui.ACCENT if mine else Color.WHITE, true))
		if not names.is_empty():
			row.add_child(Ui.label(names, 16, Ui.MUTED, true))
		if manager or mine or choosing:
			var lobby_id := str(team["lobby_id"])
			var caption := "Rejoindre" if choosing else "Ouvrir"
			var button := Ui.button(caption, func() -> void: _enter(lobby_id, choosing), choosing)
			button.name = "JoinTeamButton" if choosing else "OpenTeamButton"
			row.add_child(button)
		row.add_child(HSeparator.new())


func _enter(lobby_id: String, joining: bool) -> void:
	var res: Dictionary
	if joining:
		res = await Api.post_json("/api/v1/groups/join", {"code": join_code, "lobby_id": lobby_id})
	else:
		res = await Api.get_json("/api/v1/lobbies/%s" % lobby_id)
	if not res["ok"]:
		_status.text = res["error"]  # 409 : « Vous êtes déjà dans une autre équipe de ce groupe » / « Lobby complet » (messages de l'API)
		return
	join_code = ""  # une fois dans l'équipe, le groupe se relit par son id
	Session.open(res["data"])
	navigate.emit("lobby")


func _debrief() -> void:
	_status.text = await GmixDebrief.show_group(self, str(_group.get("id", current_id)))

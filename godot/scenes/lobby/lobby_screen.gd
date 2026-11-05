extends Control
## Salle du lobby. Joueur : choisir son rôle (son module), entrer dans l'atelier 3D, lire le débrief à la fin.
## Formateur ou admin : code d'accès, participants, lancement, simulation des semaines, débrief, observation en 3D.
## Tenue à jour par le WebSocket (Session.lobby_changed) ; les règles restent côté API.

signal navigate(target: String)

var _title: Label
var _subtitle: Label
var _welcome: Label
var _pitch: Label
var _code: Label
var _status: Label
var _week: RichTextLabel
var _kpis: RichTextLabel
var _members: VBoxContainer
var _role_box: VBoxContainer
var _roles: VBoxContainer
var _role_mission: Label
var _enter_button: Button
var _copy_button: Button
var _start_button: Button
var _advance_button: Button
var _debrief_button: Button


func _ready() -> void:
	var column := Ui.vbox(Ui.screen_margin(self), 14)
	var header := Ui.hbox(column)
	var heading := Ui.vbox(header, 2)  # nom de la session (titre) puis titre du jeu (sous-titre), chacun sur sa ligne
	heading.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_title = Ui.label("", 26, Color.WHITE, true)
	heading.add_child(_title)
	_subtitle = Ui.label("", 20, Ui.ACCENT, true)
	heading.add_child(_subtitle)
	header.add_child(Ui.button("Actualiser", func() -> void: Session.reload()))
	header.add_child(Ui.button("Retour à l'accueil", func() -> void: navigate.emit("home")))
	_pitch = Ui.label("", 0, Ui.MUTED, true)
	column.add_child(_pitch)
	_status = Ui.label("", 0, Ui.ACCENT, true)
	column.add_child(_status)
	var body := Ui.hbox(column, 16)
	body.size_flags_vertical = Control.SIZE_EXPAND_FILL

	# Deux panneaux qui se partagent la largeur (3 : 2) ; l'état de la partie défile, les boutons restent visibles.
	var left := Ui.panel(body)
	left.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	left.size_flags_stretch_ratio = 3.0
	var left_box := Ui.vbox(left, 14)
	var code_row := Ui.hbox(left_box)
	_code = Ui.label("", 30, Ui.ACCENT, true)
	code_row.add_child(_code)
	_copy_button = Ui.button("Copier le code", func() -> void: DisplayServer.clipboard_set(str(Session.lobby.get("join_code", ""))), false, "copy")
	code_row.add_child(_copy_button)
	var state_box := Ui.scroll_list(left_box, 40)
	_week = Ui.rich()
	state_box.add_child(_week)
	_kpis = Ui.rich()
	state_box.add_child(_kpis)
	var actions := Ui.flow(left_box)
	_enter_button = Ui.button("Entrer dans l'atelier 3D", func() -> void: navigate.emit("world"), true, "play")
	_start_button = Ui.button("Lancer la partie", _start, true)
	_advance_button = Ui.button("Simuler la semaine", _confirm_advance, true)
	_debrief_button = Ui.button("Débrief", _debrief)
	for button in [_enter_button, _start_button, _advance_button, _debrief_button]:
		actions.add_child(button)
	var round_bar := GmixRoundBar.new()
	round_bar.failed.connect(func(message: String) -> void: _status.text = message)
	left_box.add_child(round_bar)

	var right := Ui.panel(body)
	right.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	right.size_flags_stretch_ratio = 2.0
	var right_box := Ui.vbox(right)
	_role_box = Ui.vbox(right_box)
	_role_box.add_child(Ui.label("Mon rôle", 22))
	_welcome = Ui.label("", 0, Ui.MUTED, true)
	_role_box.add_child(_welcome)
	_roles = Ui.scroll_list(_role_box, 40)
	_role_box.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_role_box.size_flags_stretch_ratio = 5.0
	_role_mission = Ui.label("", 0, Ui.MUTED, true)
	_role_box.add_child(_role_mission)
	right_box.add_child(Ui.label("Participants", 22))
	_members = Ui.scroll_list(right_box, 40)
	Session.lobby_changed.connect(_render)
	_render()


func _render() -> void:
	var lobby := Session.lobby
	if lobby.is_empty():
		return
	var spec := Session.spec()
	var state := Session.state()
	var manager := Session.is_manager()
	var game_status: String = state.get("status", "waiting")
	_title.text = str(lobby["name"])
	_subtitle.text = str(spec.get("meta", {}).get("title", ""))
	_pitch.text = spec.get("meta", {}).get("pitch", "")
	_code.text = "Code d'accès : %s" % lobby["join_code"] if manager and lobby.get("join_code") else ""
	_code.visible = not _code.text.is_empty() and game_status != "finished"
	_copy_button.visible = _code.visible
	_week.text = GameText.week_bbcode(spec, state)
	_kpis.text = GameText.kpis_bbcode(state)
	_start_button.visible = manager and game_status == "waiting"
	_advance_button.visible = manager and game_status == "running"
	var week := int(state.get("week", 1))
	var last_week := week >= int(state.get("weeks", 1))
	_advance_button.text = "Simuler la dernière semaine" if last_week else "Simuler la semaine %d" % week
	_debrief_button.visible = manager or game_status == "finished"
	_enter_button.text = ("Observer %s 3D" if manager else "Entrer dans %s 3D") % GameText.world_noun(spec)
	_enter_button.visible = game_status != "finished"

	var my_role: Variant = lobby.get("my_role")
	_role_box.visible = not manager
	Ui.clear(_roles)
	var locked: bool = my_role != null and game_status != "waiting"
	var who := str(Api.user.get("display_name", ""))
	_welcome.text = "Votre rôle est choisi : entrez dans l'atelier." if my_role != null else "Choisissez le rôle que vous tiendrez."
	_welcome.tooltip_text = "Bienvenue %s" % who
	for role: Dictionary in spec.get("roles", []):
		var holders: Array = []
		for member: Dictionary in lobby.get("members", []):
			if member.get("game_role") == role["id"]:
				holders.append(str(member["display_name"]))
		var mine: bool = role["id"] == my_role
		var card := Ui.vbox(Ui.panel(_roles), 2)
		var top := Ui.hbox(card, 8)  # titre, état et bouton sur une ligne : les cartes restent basses
		var role_title := Ui.label(str(role["title"]), 18, Ui.ACCENT if mine else Color.WHITE, true)
		role_title.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		top.add_child(role_title)
		if mine:
			top.add_child(Ui.label("Votre rôle", 0, Ui.OK))
		else:
			var take := Ui.button("Prendre ce rôle", _choose_role.bind(role["id"]))
			take.disabled = locked
			top.add_child(take)
		var holder_text := "Tenu par %s" % ", ".join(holders) if not holders.is_empty() else "Vacant"
		card.add_child(Ui.label("Module %s. %s%s" % [GameText.module_title(spec, role["module_id"]).to_lower(), role["mission"], "" if mine else " (%s)" % holder_text], 15, Ui.MUTED, true))
	_role_mission.visible = false  # place gagnée pour les cartes ; leur texte dit déjà qui tient quoi

	Ui.clear(_members)
	var members: Array = lobby.get("members", [])
	if members.is_empty():
		_members.add_child(Ui.label("Personne pour l'instant : donnez le code aux joueurs.", 0, Ui.MUTED, true))
	for member: Dictionary in members:
		var role_text := GameText.role_title(spec, member.get("game_role"))
		_members.add_child(Ui.label("%s  ·  %s" % [member["display_name"], role_text], 0, Color.WHITE, true))


func _choose_role(role_id: String) -> void:
	var res: Dictionary = await Api.put_json(Session.url("/role"), {"game_role": role_id})
	if not res["ok"]:
		_status.text = res["error"]
		await Session.reload()
		return
	_status.text = ""
	Session.open(res["data"])


func _start() -> void:
	var res: Dictionary = await Api.post_json(Session.url("/start"))
	if not res["ok"]:
		_status.text = res["error"]
		return
	_status.text = "Partie lancée : semaine 1 ouverte, les joueurs peuvent agir."
	Session.apply_state(res["data"]["state"])


func _confirm_advance() -> void:
	Ui.confirm(
		self, _advance_button.text,
		"Livraisons, production, ventes et coûts de la semaine vont être simulés avec les réglages actuels. Continuer ?",
		"Continuer", _advance
	)


func _advance() -> void:
	var res: Dictionary = await Api.post_json(Session.url("/advance"))
	if not res["ok"]:
		_status.text = res["error"]
		return
	Session.apply_state(res["data"]["state"])


func _debrief() -> void:
	var res: Dictionary = await Api.get_json(Session.url("/debrief"))
	if not res["ok"]:
		_status.text = res["error"]
		return
	Ui.show_text(self, "Débrief", GameText.debrief_bbcode(res["data"]))

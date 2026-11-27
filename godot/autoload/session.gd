extends Node
## État client de la séance : lobby ouvert (vue renvoyée par l'API, tenue à jour par le WebSocket). Les règles du
## jeu et la mémoire des agents restent côté serveur : rien n'est calculé ici.

signal lobby_changed
## Seul l'appel « prêt » a changé (`lobby.round`, relecture) : les formulaires ouverts ne se reconstruisent pas.
signal round_changed

const ROUND_POLL_S := 15.0

var lobby: Dictionary = {}


func _ready() -> void:
	UiTokens.use(_palette_choice())
	get_tree().root.theme = Ui.make_theme()
	EventBus.lobby_state_changed.connect(_on_state)
	EventBus.lobby_members_changed.connect(_on_members)
	EventBus.lobby_round_changed.connect(set_round)
	var poll := Timer.new()
	poll.wait_time = ROUND_POLL_S
	poll.timeout.connect(_poll_round)
	add_child(poll)
	poll.start()


## Palette demandée : `--palette=<id>` (arguments utilisateur) ou variable GMIX_PALETTE ; sinon la palette par défaut.
func _palette_choice() -> String:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--palette="):
			return arg.trim_prefix("--palette=")
	var chosen := OS.get_environment("GMIX_PALETTE")
	return chosen if not chosen.is_empty() else UiTokens.DEFAULT_PALETTE


func open(view: Dictionary) -> void:
	lobby = view
	Realtime.subscribe_lobby(str(view["id"]))
	lobby_changed.emit()


func reload() -> bool:
	if lobby.is_empty():
		return false
	var res: Dictionary = await Api.get_json("/api/v1/lobbies/%s" % lobby["id"])
	if res["ok"]:
		open(res["data"])
	return res["ok"]


func close() -> void:
	lobby = {}
	Realtime.subscribe_lobby("")


func spec() -> Dictionary:
	return lobby.get("spec", {})


func state() -> Dictionary:
	return lobby.get("state", {})


func is_manager() -> bool:
	return lobby.get("is_manager", false)


## Id de mon rôle de jeu ("" : aucun).
func my_role() -> String:
	var role: Variant = lobby.get("my_role")
	return role if role is String else ""


## Raison pour laquelle je ne peux pas agir sur ce module (vide : permis). Reprend engine.act (annexe 0010 §5) : le
## formateur agit partout, un joueur seulement sur le module de son rôle ; l'API reste juge.
func module_block(module_id: String) -> String:
	if is_manager():
		return ""
	for module: Dictionary in spec().get("modules", []):
		if module["id"] != module_id:
			continue
		var role_id: String = module["role_id"]
		if my_role() == role_id:
			return ""
		if my_role().is_empty():
			return "Choisissez un rôle dans la salle d'attente pour agir."
		return "Cette action revient au rôle « %s »." % GameText.role_title(spec(), role_id)
	return ""


func url(suffix := "") -> String:
	return "/api/v1/lobbies/%s%s" % [lobby.get("id", ""), suffix]


## État public renvoyé par une action (start, advance, actions) : affiché sans attendre le WebSocket.
func apply_state(state_view: Dictionary) -> void:
	_on_state({"state": state_view, "lobby_status": "closed" if state_view.get("status") == "finished" else "running"})


## Appel « prêt » de la semaine (vue `round`, annexe 0010 §1) ; vide hors d'un lobby.
func round_view() -> Dictionary:
	return lobby.get("round", {})


func set_round(view: Dictionary) -> void:
	if lobby.is_empty() or view.is_empty() or view == lobby.get("round"):
		return
	lobby["round"] = view
	round_changed.emit()


## shortcut: l'API n'émet rien quand un joueur se déconnecte (annexe 0010 §1) : l'appel est relu toutes les 15 s
## pendant la partie ; un événement de présence côté API le remplacerait si la charge devient gênante.
func _poll_round() -> void:
	if not lobby.has("id") or state().get("status") != "running":
		return
	var lobby_id: Variant = lobby["id"]
	var res: Dictionary = await Api.get_json(url())
	if res["ok"] and lobby.get("id") == lobby_id:
		set_round(res["data"].get("round", {}))


func _on_state(payload: Dictionary) -> void:
	if lobby.is_empty():
		return
	lobby["state"] = payload.get("state", lobby.get("state", {}))
	lobby["status"] = payload.get("lobby_status", lobby.get("status", ""))
	lobby_changed.emit()
	var action: Variant = payload.get("action")
	if action is Dictionary and action.get("type") == "advance":
		_poll_round()  # l'avance remet l'appel à zéro côté serveur


func _on_members(members: Array) -> void:
	if lobby.is_empty():
		return
	lobby["members"] = members
	lobby_changed.emit()

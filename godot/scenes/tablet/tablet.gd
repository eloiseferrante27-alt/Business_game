class_name GmixTablet
extends Control
## Tablette : mode d'affichage des panneaux et des outils de la spec (`spec.panels`, `spec.tools`, modèle Panel et Tool de
## backend/gmix/game/spec.py), à côté du menu contextuel (qui reste au clic sur un objet). Elle monte du bas de l'écran
## dans un cadre de tablette fabriqué en code, et redescend à la fermeture (touche `toggle_tablet`, Échap, clic hors du
## cadre ou bouton « Ranger »). Le contenu ne change qu'avec la spec : le formateur voit la supervision et ses outils, le
## joueur ses indicateurs, son tableau de bord et ses outils ; une spec sans panneaux (atelier) montre le tableau de bord
## d'`GameText`. Aucune règle de jeu : un outil d'action affiche le formulaire de son module (fourni par le HUD via
## `action_builder`), les outils du formateur sont rendus au HUD par `tool_requested`.
## Principe repris du jeu de référence Business_game : calque modal « tablette » avec en-tête et bouton de rangement,
## animation de sortie, dock d'onglets (Indicateurs, Outils…) puis scène défilante.

signal opened
signal closed
signal tool_requested(tool: Dictionary)
## Refus de l'API pour un appel de la barre « prêt » ou d'une alerte (le HUD l'annonce).
signal failed(message: String)
## Bouton d'une alerte : {module_id, action_id, values} prérempli par le moteur (le HUD l'envoie à /actions).
signal alert_action(action: Dictionary)

const SLIDE_S := 0.28
const BEZEL := Color("#150e0b")  # coque de la tablette : plus sombre que l'écran
const RAIL_WIDTH := 224
const SCREEN_MARGIN := 24  # écart entre la tablette et le bord de la fenêtre
## Outils que la tablette ne sait pas encore exécuter : affichés mais inactifs, avec la raison.
const UNSUPPORTED := {
	"camera": "La caméra se règle au clavier et à la souris (voir l'aide).",
	"rejeu": "Le rejeu n'est pas encore dans la tablette.",
	"memoire": "La mémoire d'un agent s'ouvre depuis son menu (clic sur l'agent).",
}

## (parent, module, action) -> void : construit le formulaire d'une action de module (fourni par le HUD).
var action_builder := Callable()
## Sans animation (contrôles automatiques qui photographient l'écran tout de suite).
var instant := false

var _is_open := false
var _tab := ""
var _tool_id := ""
var _slide: Control
var _dim: ColorRect
var _rail: VBoxContainer
var _bar: RichTextLabel
var _alerts: VBoxContainer
var _round_bar: GmixRoundBar
var _stage: VBoxContainer
var _week: Label
var _tween: Tween


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	visible = false
	mouse_filter = Control.MOUSE_FILTER_STOP
	_dim = ColorRect.new()
	_dim.color = Color(UiTokens.BACKDROP, 0.6)
	_dim.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_dim.gui_input.connect(
		func(event: InputEvent) -> void:
			if event is InputEventMouseButton and (event as InputEventMouseButton).pressed:
				close()  # clic hors du cadre
	)
	add_child(_dim)
	_slide = Control.new()
	_slide.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_slide.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_slide)
	var margin := Ui.screen_margin(_slide, SCREEN_MARGIN)
	margin.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var shell := PanelContainer.new()
	var bezel := StyleBoxFlat.new()
	bezel.bg_color = BEZEL
	bezel.set_corner_radius_all(30)
	bezel.border_color = UiTokens.EDGE
	bezel.set_border_width_all(3)
	bezel.set_content_margin_all(14)
	bezel.shadow_color = Color(Color.BLACK, 0.5)
	bezel.shadow_size = 18
	shell.add_theme_stylebox_override("panel", bezel)
	margin.add_child(shell)
	var column := Ui.vbox(shell, 10)
	var header := Ui.hbox(column)
	var tablet_icon := TextureRect.new()
	tablet_icon.texture = Ui.icon("tablet")
	tablet_icon.modulate = Ui.ACCENT
	tablet_icon.custom_minimum_size = Vector2(24, 24)
	tablet_icon.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	tablet_icon.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	header.add_child(tablet_icon)
	header.add_child(Ui.label("Bonjour %s" % Api.user.get("display_name", ""), 22, Ui.ACCENT))
	_week = Ui.label("", 0, Ui.MUTED, true)
	header.add_child(_week)
	header.add_child(Ui.button("Ranger la tablette (T)", close))
	_bar = Ui.rich()  # barre toujours visible : indicateurs clés de la semaine
	column.add_child(_bar)
	_alerts = Ui.vbox(column, 4)  # alertes de la semaine (state.alerts[], annexe 0010 §2)
	_round_bar = GmixRoundBar.new()  # appel « prêt », vote, pilotage du formateur
	_round_bar.failed.connect(func(message: String) -> void: failed.emit(message))
	column.add_child(_round_bar)
	var body := Ui.hbox(column, 10)
	body.size_flags_vertical = Control.SIZE_EXPAND_FILL
	var rail_scroll := Ui.scroll_list(body, 100)  # rail des départements (modules de la spec) puis outils
	var rail_box := rail_scroll.get_parent() as ScrollContainer
	rail_box.size_flags_horizontal = Control.SIZE_SHRINK_BEGIN
	rail_box.custom_minimum_size.x = RAIL_WIDTH
	_rail = rail_scroll
	var screen := PanelContainer.new()  # l'écran : fond des champs, les cartes (panneaux) se détachent dessus
	screen.size_flags_vertical = Control.SIZE_EXPAND_FILL
	screen.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var glass := StyleBoxFlat.new()
	glass.bg_color = UiTokens.FIELD
	glass.set_corner_radius_all(UiTokens.RADIUS_PANEL)
	glass.set_content_margin_all(12)
	screen.add_theme_stylebox_override("panel", glass)
	body.add_child(screen)
	_stage = Ui.scroll_list(screen, 120)
	Session.lobby_changed.connect(func() -> void: if _is_open: _render())


func is_open() -> bool:
	return _is_open


func toggle() -> void:
	if _is_open:
		close()
	else:
		open()


## Ouvre la tablette sur un onglet (`dashboard`, `indicators`, `supervision`, `tools`) ; vide : le premier.
func open(tab := "") -> void:
	if _is_open:
		return
	_is_open = true
	_tab = tab
	_tool_id = ""
	visible = true
	_render()
	_animate(true)
	opened.emit()


func close() -> void:
	if not _is_open:
		return
	_is_open = false
	_animate(false)
	closed.emit()


func select_tab(tab: String) -> void:
	_tab = tab
	_tool_id = ""
	_render()


func _animate(opening: bool) -> void:
	if _tween != null:
		_tween.kill()
	var hidden_y := get_viewport_rect().size.y
	if instant:
		_slide.position = Vector2.ZERO if opening else Vector2(0, hidden_y)
		_dim.modulate.a = 1.0 if opening else 0.0
		visible = opening
		return
	_tween = create_tween().set_parallel(true)
	var ease_type := Tween.EASE_OUT if opening else Tween.EASE_IN
	if opening:
		_slide.position = Vector2(0, hidden_y)
		_dim.modulate.a = 0.0
	_tween.tween_property(_slide, "position:y", 0.0 if opening else hidden_y, SLIDE_S).set_trans(Tween.TRANS_CUBIC).set_ease(ease_type)
	_tween.tween_property(_dim, "modulate:a", 1.0 if opening else 0.0, SLIDE_S)
	if not opening:
		_tween.chain().tween_callback(func() -> void: visible = _is_open)


# --- contenu ---------------------------------------------------------------------------------------------


func _audience() -> String:
	return "formateur" if Session.is_manager() else "joueur"


## [[id, titre]] des pages du rail, selon la spec et le public : vue d'ensemble, un département par module, outils.
func _tabs() -> Array:
	var spec := Session.spec()
	var tabs: Array = []
	if _audience() == "formateur" and not GmixPanelView.panels_for(spec, "supervision", "formateur").is_empty():
		tabs.append(["supervision", "Supervision"])
	else:
		if _audience() == "joueur" and not GmixPanelView.panels_for(spec, "bandeau", "joueur").is_empty():
			tabs.append(["indicators", "Indicateurs"])
		tabs.append(["dashboard", "Tableau de bord"])  # sans panneau déclaré : le tableau de bord générique
	for module: Dictionary in spec.get("modules", []):
		tabs.append(["module:%s" % module["id"], str(module["title"])])
	if not _tools().is_empty():
		tabs.append(["tools", "Outils"])
	return tabs


func _tools() -> Array:
	var audience := _audience()
	return (Session.spec().get("tools", []) as Array).filter(
		func(tool: Dictionary) -> bool: return tool.get("audience", "joueur") == audience and tool.get("bar", true)
	)


func _render() -> void:
	var state := Session.state()
	var tabs := _tabs()
	if not tabs.any(func(tab: Array) -> bool: return tab[0] == _tab):
		_tab = tabs[0][0]
	match str(state.get("status", "")):
		"waiting":
			_week.text = "En attente du lancement"
		"finished":
			_week.text = "Partie terminée"
		_:
			_week.text = "Semaine %s sur %s" % [GameText.number(state.get("week")), GameText.number(state.get("weeks"))]
	_bar.text = GameText.kpis_line(state)
	_bar.visible = not _bar.text.is_empty()
	_render_alerts(state)
	Ui.clear(_rail)
	for tab: Array in tabs:
		var button := Ui.button(_rail_title(tab), select_tab.bind(tab[0]), tab[0] == _tab, _rail_icon(str(tab[0])))
		button.alignment = HORIZONTAL_ALIGNMENT_LEFT
		button.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		button.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		_rail.add_child(button)
	Ui.clear(_stage)
	var spec := Session.spec()
	match _tab:
		"supervision":
			_cards(GmixPanelView.panels_for(spec, "supervision", "formateur"), state)
		"indicators":
			_cards(GmixPanelView.panels_for(spec, "bandeau", "joueur"), state)
		"tools":
			_render_tools(state)
		_ when _tab.begins_with("module:"):
			_render_module(_tab.trim_prefix("module:"))
		_:
			var panels := GmixPanelView.panels_for(spec, "tableau_de_bord", _audience())
			if panels.is_empty():
				var text := Ui.rich()
				text.text = GameText.dashboard_bbcode(spec, state)
				_stage.add_child(text)
			else:
				_cards(panels, state)


func _render_alerts(state: Dictionary) -> void:
	Ui.clear(_alerts)
	var alerts: Array = state.get("alerts", [])
	_alerts.visible = not alerts.is_empty()
	for alert: Dictionary in alerts:
		var color: Color = {"critical": Ui.ERROR, "warning": Ui.WARN}.get(str(alert.get("level", "info")), Ui.MUTED)
		var row := Ui.hbox(_alerts, 10)
		var text := Ui.label(str(alert.get("text", "")), 0, color, true)
		text.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		row.add_child(text)
		var action: Variant = alert.get("action")
		if action is Dictionary:
			row.add_child(Ui.button("Faire", func() -> void: alert_action.emit(action)))


func _cards(panels: Array, state: Dictionary) -> void:
	for panel: Dictionary in panels:
		_stage.add_child(GmixPanelView.build(panel, state))


func _render_tools(state: Dictionary) -> void:
	var row := Ui.flow(_stage, 10)
	for tool: Dictionary in _tools():
		var reason := _blocked(tool, state)
		var button := Ui.button(str(tool["label"]), _use.bind(tool), str(tool["id"]) == _tool_id)
		button.disabled = not reason.is_empty()
		button.tooltip_text = reason
		row.add_child(button)
	for tool: Dictionary in _tools():
		if str(tool["id"]) == _tool_id and tool["kind"] == "action":
			_action_card(tool)
	var notes: Array = _tools().filter(func(tool: Dictionary) -> bool: return not _blocked(tool, state).is_empty())
	for tool: Dictionary in notes:
		_stage.add_child(Ui.label("%s : %s" % [tool["label"], _blocked(tool, state)], 0, Ui.MUTED, true))


## Raison pour laquelle un outil est inactif (texte vide : utilisable).
func _blocked(tool: Dictionary, state: Dictionary) -> String:
	if UNSUPPORTED.has(tool["kind"]):
		return UNSUPPORTED[tool["kind"]]
	var status := str(state.get("status", ""))
	match tool["kind"]:
		"demarrer":
			return "" if status == "waiting" else "La partie est déjà lancée."
		"avancer":
			return "" if status == "running" else "La partie n'est pas en cours."
	return ""


func _use(tool: Dictionary) -> void:
	match tool["kind"]:
		"tableau_de_bord":
			select_tab("supervision" if _tabs().any(func(tab: Array) -> bool: return tab[0] == "supervision") else "dashboard")
		"action":
			_tool_id = "" if _tool_id == str(tool["id"]) else str(tool["id"])
			_render()
		_:
			tool_requested.emit(tool)


## Formulaire de l'action d'un module (spec.modules[].actions[]), construit par le HUD.
func _action_card(tool: Dictionary) -> void:
	for module: Dictionary in Session.spec().get("modules", []):
		for action: Dictionary in module["actions"]:
			if action["id"] != tool.get("action_id"):
				continue
			var box := Ui.vbox(Ui.panel(_stage), 8)
			box.add_child(Ui.label(str(module["title"]), 20, Ui.ACCENT, true))
			box.add_child(Ui.label(str(module["description"]), 0, Ui.MUTED, true))
			if action_builder.is_valid():
				action_builder.call(box, module, action)
			return
	_stage.add_child(Ui.label("Action « %s » absente de cette partie." % tool.get("action_id"), 0, Ui.WARN, true))


## Rôle de la spec qui tient ce module : {role, holder} ; `holder` : nom du joueur qui l'a pris ("" : personne).
func _role_of(module_id: String) -> Dictionary:
	for role: Dictionary in Session.spec().get("roles", []):
		if role["module_id"] != module_id:
			continue
		for member: Dictionary in Session.lobby.get("members", []):
			if member.get("game_role") == role["id"]:
				return {"role": role, "holder": str(member["display_name"]), "mine": Session.lobby.get("my_role") == role["id"]}
		return {"role": role, "holder": "", "mine": false}
	return {}


## Icône d'une page du rail (fichier de scenes/common/icons du même nom que le module ; inconnu : icône générique).
func _rail_icon(tab_id: String) -> String:
	match tab_id:
		"supervision": return "supervision"
		"dashboard", "indicators": return "dashboard"
		"tools": return "tools"
	return tab_id.trim_prefix("module:")


## Un point devant mon département ; les autres sont en lecture seule.
func _rail_title(tab: Array) -> String:
	if not str(tab[0]).begins_with("module:") or not _role_of(str(tab[0]).trim_prefix("module:")).get("mine", false):
		return str(tab[1])
	return "● %s" % tab[1]


## Page d'un département : qui le tient, puis les formulaires de ses actions (le HUD dit pourquoi un formulaire est fermé).
func _render_module(module_id: String) -> void:
	for module: Dictionary in Session.spec().get("modules", []):
		if module["id"] != module_id:
			continue
		var box := Ui.vbox(Ui.panel(_stage), 8)
		box.add_child(Ui.label(str(module["title"]), 20, Ui.ACCENT, true))
		box.add_child(Ui.label(str(module["description"]), 0, Ui.MUTED, true))
		var owner := _role_of(module_id)
		var who := "Département sans titulaire : il tourne en pilote automatique ou aide l'équipe."
		if owner.get("mine", false):
			who = "C'est votre département : vous agissez ici."
		elif not str(owner.get("holder", "")).is_empty():
			who = "Tenu par %s : lecture seule pour vous." % GameText.esc(owner["holder"])
		elif Session.is_manager():
			who = "Vous pilotez la partie : vous pouvez agir sur tous les départements."
		box.add_child(Ui.label(who, 0, Ui.OK if owner.get("mine", false) else Ui.MUTED, true))
		if action_builder.is_valid():
			for action: Dictionary in module["actions"]:
				action_builder.call(box, module, action)
		return

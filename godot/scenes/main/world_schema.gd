class_name GmixWorldSchema
extends VBoxContainer
## Schéma visuel du monde dans le formulaire « Concevoir avec l'IA » : lieux (fournisseurs, bâtiments de l'usine,
## client), blocs opérationnels (départements : leur agent et leurs équipements) et agents. Avant la conception, il
## montre le pack (GET /games/options, `packs[].world`) ; après, la spec conçue (agents nommés, bâtiments et pièces).
## Les réglages du schéma sont des clés de GameParams : `locks` les expose au formulaire comme ses autres champs
## ([CheckBox « Imposer », lecture, écriture]) ; changer un réglage coche son « Imposer ».

## Clé de GameParams -> libellé de sa case « Imposer ».
const LOCKS := {
	"buildings": "Bâtiments", "options": "Lignes", "modules": "Postes joués", "extra_agents": "Agents en plus",
	"agent_tone": "Caractère", "network": "Distances",
}

var locks: Dictionary = {}  # clé -> [CheckBox, Callable lecture, Callable écriture]

var _pack: Dictionary = {}
var _spec: Dictionary = {}
var _values: Dictionary = {}
var _diagram: VBoxContainer


## Construit le schéma pour un pack de GET /games/options (sans `world.blocks` : rien à montrer).
func setup(pack: Dictionary) -> void:
	Ui.clear(self)
	locks = {}
	_pack = pack
	_spec = {}
	add_theme_constant_override("separation", 8)
	add_child(Ui.label("Schéma du monde", 22, Ui.ACCENT))
	add_child(Ui.label("Les lieux, les blocs opérationnels (un bloc reçoit des entrées et donne des sorties) et leurs agents. L'IA les préremplit d'après votre description ; modifiez ce que vous voulez imposer.", 16, Ui.MUTED, true))
	var limits: Dictionary = pack.get("limits", {})
	var lines_param: Array = (pack.get("params", []) as Array).filter(func(p: Dictionary) -> bool: return p["id"] == "lines")
	_values = {
		"buildings": int(limits.get("buildings", [1, 1, 1])[2]),
		"options": {"lines": int(lines_param[0]["default"])} if not lines_param.is_empty() else {},
		"modules": (pack.get("modules", []) as Array).map(func(m: Dictionary) -> String: return m["id"]),
		"extra_agents": [],
		"agent_tone": pack["tones"][1 if pack["tones"].size() > 1 else 0]["id"],
		"network": {},
	}
	for site: Dictionary in pack["world"]["sites"]:
		if (site["distances"] as Array).size() > 1:
			_values["network"][site["id"]] = site["default"]
	var row := Ui.flow(self)
	row.add_child(Ui.label("Imposer à l'IA :", 16, Ui.MUTED))
	for key: String in LOCKS:
		var check := CheckBox.new()
		check.text = LOCKS[key]
		check.name = "Lock_%s" % key
		row.add_child(check)
		locks[key] = [check, func() -> Variant: return _copy(_values[key]), func(value: Variant) -> void: _assign(key, value)]
	_diagram = Ui.vbox(self, 8)
	_render()


## Spec conçue (GET /games/{id}) : noms des agents, bâtiments et pièces. Les valeurs suivent par les `locks`.
func show_spec(spec: Dictionary) -> void:
	_spec = spec
	_render()


func _copy(value: Variant) -> Variant:
	return value.duplicate(true) if value is Array or value is Dictionary else value


func _assign(key: String, value: Variant) -> void:
	_values[key] = _copy(value)
	_render.call_deferred()  # un contrôle du schéma peut être à l'origine du changement


## Changement fait par le formateur : la valeur est gardée et la case « Imposer » se coche.
func _change(key: String, value: Variant) -> void:
	_values[key] = value
	(locks[key][0] as CheckBox).button_pressed = true
	_render.call_deferred()


func _render() -> void:
	if _diagram == null:
		return
	Ui.clear(_diagram)
	var top := Ui.flow(_diagram, 16)
	top.add_child(Ui.label("Caractère des agents", 0, Color.WHITE))
	var tones: Array = _pack["tones"]
	var tone := _select(tones, "label", tones.map(func(t: Dictionary) -> String: return t["id"]).find(_values["agent_tone"]))
	tone.item_selected.connect(func(i: int) -> void: _change("agent_tone", tones[i]["id"]))
	top.add_child(tone)
	var limits: Dictionary = _pack.get("limits", {})
	if limits.has("buildings") and int(limits["buildings"][1]) > int(limits["buildings"][0]):
		top.add_child(Ui.label("Bâtiments", 0, Color.WHITE))
		top.add_child(_spin(limits["buildings"][0], limits["buildings"][1], _values["buildings"], func(v: float) -> void: _change("buildings", int(v))))

	var map := Ui.hbox(_diagram, 8)
	var suppliers := _column(map, "Fournisseurs", 260)
	map.add_child(_arrow())
	var plant := _column(map, "Usine", 0)
	map.add_child(_arrow())
	var customers := _column(map, "Client", 260)
	var blocks: Dictionary = {}
	for block: Dictionary in _pack["world"]["blocks"]:
		blocks[block["id"]] = block
	for site: Dictionary in _pack["world"]["sites"]:
		_site_card(suppliers if site["kind"] == "fournisseur" else customers, site, blocks)
	for building: Array in _buildings(blocks):
		var box := Ui.vbox(Ui.panel(plant), 6)
		box.add_child(Ui.label(building[0], 18, Ui.ACCENT, true))
		var cards := Ui.flow(box, 8)  # cartes de largeur fixe, qui passent à la ligne
		for block_id: String in building[1]:
			_block_card(cards, blocks[block_id])


## [[titre, ids des blocs]] : les bâtiments de la spec s'ils correspondent au nombre choisi, sinon un seul bloc « Usine ».
func _buildings(blocks: Dictionary) -> Array:
	var inside: Array = blocks.keys().filter(func(id: String) -> bool: return not blocks[id]["external"])
	var world: Dictionary = _spec.get("world", {})
	var built: Array = world.get("buildings", [])
	if built.size() == int(_values["buildings"]) and built.size() > 1:
		var out := []
		for i in built.size():
			var ids := []
			for room: Dictionary in world.get("rooms", []):
				if room["building_id"] == built[i]["id"]:
					ids.append_array(room["department_ids"])
			out.append(["Bâtiment %d · %s" % [i + 1, built[i]["label"]], ids])
		return out
	var title := "Hall de production"
	if int(_values["buildings"]) > 1:
		title = "Usine en %d bâtiments : les blocs y sont répartis à la conception" % int(_values["buildings"])
	return [[title, inside]]


func _site_card(parent: Node, site: Dictionary, blocks: Dictionary) -> void:
	var box := Ui.vbox(Ui.panel(parent), 4)
	box.add_child(Ui.label(str(site["label"]), 0, Color.WHITE, true))
	var placed: Array = (_spec.get("world", {}).get("sites", []) as Array).filter(func(s: Dictionary) -> bool: return s["id"] == site["id"])
	var classes: Dictionary = _pack["world"]["distance_classes"]
	var choices: Array = site["distances"]
	if choices.size() > 1:
		var current := choices.find(_values["network"].get(site["id"], site["default"]))
		var select := Ui.select(choices.map(func(c: String) -> String: return classes.get(c, c)))
		select.selected = current
		select.item_selected.connect(func(i: int) -> void:
			var network: Dictionary = _values["network"].duplicate()
			network[site["id"]] = choices[i]
			_change("network", network))
		box.add_child(select)
	else:
		box.add_child(Ui.label(classes.get(choices[0], choices[0]), 15, Ui.MUTED, true))
	if not placed.is_empty():
		box.add_child(Ui.label("%s km · %s j de transport" % [GameText.number(placed[0]["km"]), GameText.number(placed[0]["transit_days"])], 15, Ui.MUTED, true))
	for block: Dictionary in blocks.values():  # bloc externe tenu par ce site (agent du fournisseur standard, client)
		if block["external"] and block["site"] == site["id"]:
			box.add_child(Ui.label(_agent_text(block), 15, Ui.TEXT, true))


func _block_card(parent: Node, block: Dictionary) -> void:
	var card := PanelContainer.new()
	card.custom_minimum_size.x = 250
	card.name = "Block_%s" % block["id"]
	parent.add_child(card)
	var box := Ui.vbox(card, 4)
	box.add_child(Ui.label(str(block["label"]), 0, Color.WHITE, true))
	var agent := _agent_text(block)
	if not agent.is_empty():
		box.add_child(Ui.label(agent, 15, Ui.TEXT, true))
	if not (block["elements"] as Array).is_empty():
		box.add_child(Ui.label("Équipements : %s" % ", ".join(block["elements"]), 15, Ui.MUTED, true))
	var modules: Array = _pack.get("modules", [])
	if modules.any(func(m: Dictionary) -> bool: return m["id"] == block["id"]):
		var played := CheckBox.new()
		played.text = "Tenu par un joueur"
		played.tooltip_text = "Décoché : le bloc tourne en pilote automatique."
		played.button_pressed = (_values["modules"] as Array).has(block["id"])
		played.toggled.connect(func(on: bool) -> void: _toggle("modules", block["id"], on))
		box.add_child(played)
	if block["id"] == "production" and (_values["options"] as Dictionary).has("lines"):
		var lines_param: Dictionary = (_pack["params"] as Array).filter(func(p: Dictionary) -> bool: return p["id"] == "lines")[0]
		var row := Ui.hbox(box, 6)
		row.add_child(Ui.label("Lignes", 15, Color.WHITE))
		row.add_child(_spin(lines_param["min"], lines_param["max"], _values["options"]["lines"], func(v: float) -> void:
			var options: Dictionary = _values["options"].duplicate()
			options["lines"] = int(v)
			_change("options", options)))
	for extra: Dictionary in _pack.get("extra_agents", []):
		if block.get("extra_agent") is Dictionary and block["extra_agent"]["id"] == extra["id"]:
			var check := CheckBox.new()
			check.text = "%s (%s)" % [extra["title"], block["extra_agent"]["name"]]
			check.tooltip_text = str(extra["description"])
			check.button_pressed = (_values["extra_agents"] as Array).has(extra["id"])
			check.toggled.connect(func(on: bool) -> void: _toggle("extra_agents", extra["id"], on))
			box.add_child(check)


## « Agent : nom, métier » : celui de la spec conçue s'il existe, sinon celui du pack.
func _agent_text(block: Dictionary) -> String:
	var names := PackedStringArray()
	for agent: Dictionary in _spec.get("agents", []):
		if agent.get("department_id") == block["id"]:
			names.append("%s, %s" % [agent["name"], agent["job"]])
	if names.is_empty() and block.get("agent") is Dictionary:
		names.append("%s, %s" % [block["agent"]["name"], block["agent"]["job"]])
	return "Agent : %s" % " · ".join(names) if not names.is_empty() else ""


func _toggle(key: String, id: String, on: bool) -> void:
	var ids: Array = (_values[key] as Array).duplicate()
	if on and not ids.has(id):
		ids.append(id)
	elif not on:
		ids.erase(id)
	_change(key, ids)


func _column(parent: Node, title: String, width: int) -> VBoxContainer:
	var column := Ui.vbox(parent, 8)
	if width > 0:
		column.custom_minimum_size.x = width
	else:
		column.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	column.add_child(Ui.label(title, 18, Ui.MUTED))
	return column


func _arrow() -> Label:
	var arrow := Ui.label("→", 26, Ui.ACCENT)
	arrow.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	return arrow


func _select(items: Array, key: String, selected: int) -> OptionButton:
	var select := Ui.select(items.map(func(item: Dictionary) -> String: return item[key]))
	select.selected = maxi(selected, 0)
	select.custom_minimum_size.x = 220
	return select


func _spin(low: float, high: float, value: float, on_change: Callable) -> SpinBox:
	var spin := SpinBox.new()
	spin.min_value = low
	spin.max_value = high
	spin.value = value
	spin.custom_minimum_size.x = 90
	spin.value_changed.connect(on_change)
	return spin

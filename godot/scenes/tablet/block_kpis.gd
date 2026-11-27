class_name GmixBlockKpis
extends RefCounted
## KPI de performance triés par bloc opérationnel : un bloc (département de la spec) reçoit des entrées et donne des
## sorties (flux du moteur, `state.factory.flow.edges`, en produits ou unités de matière sur la dernière semaine) ; ses
## indicateurs viennent de `state.factory` (lignes, machines, stocks, commandes) et des KPI de la semaine. Aucun calcul
## de jeu : lecture seule de la vue publique (backend/gmix/game/factory_game.py, public_state).


## [{id, label, inputs, outputs, kpis: [[libellé, valeur (nombre ou null), unité]]}] dans l'ordre des départements.
static func rows(spec: Dictionary, state: Dictionary) -> Array:
	var f: Dictionary = state.get("factory", {})
	if f.is_empty():
		return []
	var kpis: Dictionary = state.get("kpis", {})
	var last: Dictionary = state["last"] if state.get("last") is Dictionary else {}
	var machines: Array = f.get("machines", [])
	var machine_ids: Array = machines.map(func(m: Dictionary) -> String: return m["id"])
	var stocks: Dictionary = f.get("stocks", {})  # une vue partielle (tests, ancienne partie) peut ne pas l'avoir
	var mp: Dictionary = stocks["mp"][0] if not (stocks.get("mp", []) as Array).is_empty() else {}
	var pf: Dictionary = stocks.get("pf", {})
	var production_orders: Array = f.get("orders", {}).get("production", [])
	var products: Dictionary = f.get("products", {})
	var edges: Array = f.get("flow", {}).get("edges", [])
	var out := []
	for dept: Dictionary in spec.get("departments", []):
		var id := str(dept["id"])
		var ids := machine_ids if id == "production" else [id]
		var row := {"id": id, "label": str(dept["label"]), "kpis": [],
			"inputs": _flow(edges, ids, true), "outputs": _flow(edges, ids, false)}
		var k: Array = row["kpis"]
		match id:
			"fournisseur":
				k.append(["Palettes en transit", mp.get("pending"), "pal."])
			"reception":
				k.append(["En quarantaine", stocks.get("quarantine"), "u."])
			"stock_mp":
				k.append(["Stock de matière", mp.get("pallets"), "/ %s pal." % GameText.number(mp.get("capacity_pallets"))])
				k.append(["Point de commande", mp.get("reorder_point"), "pal."])
				k.append(["En commande", mp.get("pending"), "pal."])
			"production":
				for line: Dictionary in f.get("lines", []):
					k.append(["%s : TRS" % line["name"], line.get("trs"), "%"])
					k.append(["%s : cadence réelle" % line["name"], line.get("real_h"), "/ %s par h" % GameText.number(line.get("theoretical_h"))])
					k.append(["%s : encours" % line["name"], line.get("wip"), "produits"])
					k.append(["%s : OF réalisés" % line["name"], line.get("production_rate"), "%"])
				k.append(["Machines en panne", machines.filter(func(m: Dictionary) -> bool: return m["state"] == "panne").size(), ""])
			"qualite":
				k.append(["Part de bons", kpis.get("good_share"), "%"])
				k.append(["Défauts détectés", _sum(machines, "defects"), "produits"])
				k.append(["Rebut (cumul)", products.get("rebut"), "produits"])
				k.append(["À retoucher", products.get("a_retoucher"), "produits"])
			"emballage":
				k.append(["Emballés en attente", products.get("emballe"), "produits"])
			"maintenance":
				k.append(["Pannes de la semaine", _sum(machines, "failures"), ""])
				k.append(["Arrêts pour panne", _sum(machines, "downtime_min"), "min"])
				var avail: Array = machines.map(func(m: Dictionary) -> Variant: return m.get("availability")).filter(func(v: Variant) -> bool: return v != null)
				k.append(["Disponibilité moyenne", _mean(avail), "%"])
				var history: Array = state.get("history", [])
				k.append(["Préventifs réalisés", history[-1].get("preventive") if not history.is_empty() else null, ""])
			"pilotage":
				k.append(["Trésorerie", state.get("cash"), "€"])
				var costs: Dictionary = last.get("costs", {})
				k.append(["Résultat de la semaine", float(last["revenue"]) - _total(costs) if last.has("revenue") else null, "€"])
				k.append(["OF en cours", production_orders.filter(func(o: Dictionary) -> bool: return o["status"] == "en_cours").size(), ""])
			"quai":
				k.append(["Commandes en retard", (last.get("delayed", []) as Array).size() if not last.is_empty() else null, ""])
			"entrepot_pf":
				k.append(["Stock de produits finis", pf.get("quantity"), "produits"])
				k.append(["Palettes occupées", pf.get("pallets"), "/ %s" % GameText.number(pf.get("capacity_pallets"))])
				k.append(["Stock minimum", pf.get("min"), "produits"])
			"client":
				k.append(["OTIF", kpis.get("otif"), "%"])
				var totals: Dictionary = last.get("totals", {})
				k.append(["Demande de la semaine", totals.get("demand"), "produits"])
				k.append(["Livrés", totals.get("served"), "produits"])
		if not k.is_empty() or row["inputs"] != null or row["outputs"] != null:
			out.append(row)
	return out


## Cartes « bloc » : entrées, sorties, puis ses KPI.
static func build(parent: Node, spec: Dictionary, state: Dictionary) -> void:
	var blocks := rows(spec, state)
	if blocks.is_empty():
		parent.add_child(Ui.label("Les KPI par bloc apparaissent après la première semaine jouée.", 0, Ui.MUTED, true))
		return
	parent.add_child(Ui.label("Un bloc opérationnel reçoit des entrées et donne des sorties (dernière semaine). Ses indicateurs sont rangés avec lui.", 15, Ui.MUTED, true))
	for block: Dictionary in blocks:
		var box := Ui.vbox(Ui.panel(parent), 4)
		box.add_child(Ui.label(block["label"], 20, Ui.ACCENT, true))
		var io := PackedStringArray()
		if block["inputs"] != null:
			io.append("Entrées : %s" % GameText.number(block["inputs"]))
		if block["outputs"] != null:
			io.append("Sorties : %s" % GameText.number(block["outputs"]))
		if not io.is_empty():
			box.add_child(Ui.label("  ·  ".join(io), 0, Ui.TEXT, true))
		for kpi: Array in block["kpis"]:
			box.add_child(Ui.label("%s : %s %s" % [kpi[0], _shown(kpi[1], kpi[2]), "" if kpi[2] == "€" else kpi[2]], 0, Color.WHITE, true))


## Lignes [bloc, indicateur, valeur, unité] pour SurExel (valeurs nombres, sans mise en forme).
static func sheet(spec: Dictionary, state: Dictionary) -> Array:
	var out := [["Bloc", "Indicateur", "Valeur", "Unité"]]
	for block: Dictionary in rows(spec, state):
		for kpi: Array in block["kpis"]:
			out.append([block["label"], kpi[0], "" if kpi[1] == null else str(kpi[1]).replace(".", ","), kpi[2]])
	return out


static func _shown(value: Variant, unit: String) -> String:
	return GameText.money(value) if unit == "€" else GameText.number(value)


## Somme des flux qui entrent dans (`incoming`) ou sortent de `ids`, sans les flux internes (machine vers machine).
static func _flow(edges: Array, ids: Array, incoming: bool) -> Variant:
	var total := 0
	var seen := false
	for edge: Dictionary in edges:
		var inside: bool = ids.has(edge["to"] if incoming else edge["from"])
		var other: String = edge["from"] if incoming else edge["to"]
		if inside and not ids.has(other):
			total += int(edge["count"])
			seen = true
	return total if seen else null


static func _sum(items: Array, key: String) -> int:
	return items.reduce(func(acc: int, m: Dictionary) -> int: return acc + int(m.get(key, 0)), 0)


static func _total(costs: Dictionary) -> float:
	return costs.values().reduce(func(acc: float, v: Variant) -> float: return acc + float(v), 0.0)


static func _mean(values: Array) -> Variant:
	if values.is_empty():
		return null
	return values.reduce(func(acc: float, v: Variant) -> float: return acc + float(v), 0.0) / values.size()

class_name GmixBasicTools
extends VBoxContainer
## Outils de base de la tablette, inspirés de ceux de la contribution Amine (SurExel, carte du trafic) : SurExel, Carte
## du monde, Recherche internet. Toujours disponibles, sans règle de jeu ; la feuille SurExel est gardée par la tablette.

signal picked(id: String)

const TOOLS :=[["surexel", "SurExel"], ["carte", "Carte du monde"], ["recherche", "Recherche internet"]]
const SEARCH_URL := "https://duckduckgo.com/?q=%s"

var tool := "surexel"
var sheet: Array = []  # cellules SurExel (tableau de la tablette : survit à la reconstruction)
var _stage: VBoxContainer


func _ready() -> void:
	add_theme_constant_override("separation", 10)
	var row := Ui.flow(self, 8)
	for entry: Array in TOOLS:
		row.add_child(Ui.button(entry[1], _pick.bind(entry[0]), entry[0] == tool))
	_stage = Ui.vbox(self, 8)
	_render()


func _pick(id: String) -> void:
	picked.emit(id)  # la tablette garde l'outil choisi et se reconstruit


func _render() -> void:
	var spec := Session.spec()
	var state := Session.state()
	match tool:
		"carte":
			_stage.add_child(Ui.label("Usine, fournisseurs, client et trajets des camions (distances et délais du moteur).", 15, Ui.MUTED, true))
			var map := GmixWorldMap.new()
			map.world = spec.get("world", {})
			_stage.add_child(map)
		"recherche":
			_stage.add_child(Ui.label("Cherchez une notion (OTIF, TRS, point de commande…) : les résultats s'ouvrent dans votre navigateur.", 15, Ui.MUTED, true))
			var row := Ui.hbox(_stage)
			var query := Ui.field("Votre recherche", false, 360)
			query.size_flags_horizontal = Control.SIZE_EXPAND_FILL
			row.add_child(query)
			var go := func(_t: String = "") -> void: _search(query.text)
			query.text_submitted.connect(go)
			row.add_child(Ui.button("Rechercher", go, true))
		_:
			var excel := GmixSurExel.new()
			excel.cells = sheet
			var row := Ui.flow(_stage, 8)
			row.add_child(Ui.button("Importer les KPI par bloc", func() -> void: excel.load_rows(GmixBlockKpis.sheet(spec, state))))
			row.add_child(Ui.button("Vider la feuille", func() -> void: excel.load_rows([])))
			_stage.add_child(excel)


func _search(text: String) -> void:
	if not text.strip_edges().is_empty():
		OS.shell_open(SEARCH_URL % text.strip_edges().uri_encode())

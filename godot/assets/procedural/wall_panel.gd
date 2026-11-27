@tool
extends GmixAsset
## Segment de mur du campus : 4 m de long (X), 0,25 m d'épaisseur (Z), 6 m (façade) ou 3 m (cloison) de haut.
## Face avant vers +Z. Un seul maillage fusionné (instanciable par cellule de 4 m), une boîte de collision.
## Propriétés : style (« bardage » métallique ou « brique »), height (6 ou 3 m). Variantes : style, hauteur.
## Emprise : 4 (X) x 0,25 (Z) x 6 m.

const LENGTH := 4.0
const THICKNESS := 0.25
const CORE := 0.2  # noyau ; nervures et joints saillent jusqu'à THICKNESS
const STYLES := ["bardage", "brique"]

@export_enum("bardage", "brique") var style := "bardage":
	set(value):
		if not STYLES.has(value):
			push_warning("%s : style inconnu « %s » (bardage affiché)" % [asset_id, value])
			value = "bardage"
		style = value
		_rebuild()
@export var height := 6.0:
	set(value):
		height = clampf(value, 2.0, 6.0)
		_rebuild()


func _ready() -> void:
	super()
	_rebuild()


func _rebuild() -> void:
	if not is_node_ready():
		return
	Mesher.clear(self)
	var batch := Mesher.Batch.new()
	var rib := (THICKNESS - CORE) / 2.0
	if style == "brique":
		var brick := Palette.RUST.lerp(Palette.WALL_WARM, 0.4)
		var mortar := Palette.WALL_WARM
		batch.box(Vector3(LENGTH, height, CORE), Vector3(0, height / 2.0, 0), brick)
		for y in range(1, int(height / 0.5)):  # joints horizontaux tous les 50 cm
			batch.box(Vector3(LENGTH, 0.05, CORE + 2.0 * rib), Vector3(0, y * 0.5, 0), mortar)
		batch.box(Vector3(LENGTH, 0.1, THICKNESS), Vector3(0, height - 0.05, 0), Palette.CONCRETE)  # couvertine
	else:
		var steel := Palette.STEEL_LIGHT
		batch.box(Vector3(LENGTH, height, CORE), Vector3(0, height / 2.0, 0), steel)
		for i in 8:  # nervures verticales tous les 50 cm, des deux côtés
			var x := -LENGTH / 2.0 + 0.25 + i * 0.5
			for z in [-1.0, 1.0]:
				batch.box(Vector3(0.12, height - 0.4, rib), Vector3(x, height / 2.0, z * (CORE + rib) / 2.0), Palette.STEEL)
		batch.box(Vector3(LENGTH, 0.3, THICKNESS), Vector3(0, 0.15, 0), Palette.STEEL_DARK)  # soubassement
		batch.box(Vector3(LENGTH, 0.1, THICKNESS), Vector3(0, height - 0.05, 0), Palette.STEEL_DARK)  # bandeau
	batch.build(self)
	Mesher.collider(self, [[Vector3(LENGTH, height, THICKNESS), Vector3(0, height / 2.0, 0)]])

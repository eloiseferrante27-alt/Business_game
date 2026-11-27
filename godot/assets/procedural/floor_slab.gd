@tool
extends GmixAsset
## Dalle de sol du campus : 4 x 4 m, 5 cm d'épaisseur, une par cellule. Un maillage fusionné et une boîte de collision
## (on marche dessus). Propriété : style (« beton » : atelier, logistique, maintenance ; « resine » : bureau, clair).
## Variante : style. Emprise : 4 (X) x 4 (Z) x 0,05 m.

const SIZE := 4.0
const THICKNESS := 0.05
const STYLES := ["beton", "resine"]

@export_enum("beton", "resine") var style := "beton":
	set(value):
		if not STYLES.has(value):
			push_warning("%s : style inconnu « %s » (beton affiché)" % [asset_id, value])
			value = "beton"
		style = value
		_rebuild()


func _ready() -> void:
	super()
	_rebuild()


func _rebuild() -> void:
	if not is_node_ready():
		return
	Mesher.clear(self)
	var batch := Mesher.Batch.new()
	if style == "resine":
		batch.box(Vector3(SIZE, THICKNESS, SIZE), Vector3(0, THICKNESS / 2.0, 0), Palette.WALL_LIGHT.lerp(Palette.SAGE, 0.15))
	else:
		var joint := Palette.CONCRETE.darkened(0.18)
		batch.box(Vector3(SIZE, THICKNESS, SIZE), Vector3(0, THICKNESS / 2.0, 0), Palette.CONCRETE)
		batch.box(Vector3(SIZE, 0.002, 0.03), Vector3(0, THICKNESS, 0), joint)  # joints de retrait en croix
		batch.box(Vector3(0.03, 0.002, SIZE), Vector3(0, THICKNESS, 0), joint)
	batch.build(self)
	Mesher.collider(self, [[Vector3(SIZE, THICKNESS, SIZE), Vector3(0, THICKNESS / 2.0, 0)]])

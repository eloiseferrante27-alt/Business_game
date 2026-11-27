@tool
extends GmixAsset
## Porte du campus, à poser dans l'ouverture d'un mur (épaisseur 0,25 m, face avant vers +Z).
## kind « sectionnelle » : 4 x 4 m (passage 3,5 x 3,5 m, lames, hublots) ; kind « pietonne » : 1 x 2,1 m.
## Propriétés : kind, open (vrai = battant relevé ou ouvert : le passage n'a AUCUNE collision, seul le cadre en a).
## Variantes : type, ouverte. Emprise par défaut (sectionnelle) : 4 (X) x 0,25 (Z) x 4 m.

const DEPTH := 0.25
const KINDS := {"sectionnelle": Vector2(4.0, 4.0), "pietonne": Vector2(1.0, 2.1)}

@export_enum("sectionnelle", "pietonne") var kind := "sectionnelle":
	set(value):
		if not KINDS.has(value):
			push_warning("%s : type inconnu « %s » (sectionnelle affichée)" % [asset_id, value])
			value = "sectionnelle"
		kind = value
		_rebuild()
@export var open := false:
	set(value):
		open = value
		_rebuild()


func _ready() -> void:
	super()
	_rebuild()


func _rebuild() -> void:
	if not is_node_ready():
		return
	Mesher.clear(self)
	var size: Vector2 = KINDS[kind]
	var jamb := 0.25 if kind == "sectionnelle" else 0.08
	var lintel := 0.5 if kind == "sectionnelle" else 0.1
	var frame := Palette.STEEL_DARK
	var opening_w := size.x - 2.0 * jamb
	var opening_h := size.y - lintel
	var batch := Mesher.Batch.new()
	var boxes: Array = []
	for side in [-1.0, 1.0]:
		var x: float = side * (size.x - jamb) / 2.0
		batch.box(Vector3(jamb, size.y, DEPTH), Vector3(x, size.y / 2.0, 0), frame)
		boxes.append([Vector3(jamb, size.y, DEPTH), Vector3(x, size.y / 2.0, 0)])
	batch.box(Vector3(opening_w, lintel, DEPTH), Vector3(0, size.y - lintel / 2.0, 0), frame)
	boxes.append([Vector3(opening_w, lintel, DEPTH), Vector3(0, size.y - lintel / 2.0, 0)])
	if kind == "sectionnelle":
		if not open:  # 4 lames empilées, la dernière avec hublots
			var slat := opening_h / 4.0
			for i in 4:
				var y := slat * (i + 0.5)
				batch.box(Vector3(opening_w, slat - 0.04, 0.08), Vector3(0, y, 0), Palette.WALL_LIGHT)
				if i == 3:
					for j in 4:
						batch.box(Vector3(0.6, 0.3, 0.09), Vector3(-1.2 + j * 0.8, y, 0), Palette.GLASS)
			boxes.append([Vector3(opening_w, opening_h, 0.1), Vector3(0, opening_h / 2.0, 0)])
		else:  # relevée : seuls les rails restent visibles de chaque côté du passage
			for side in [-1.0, 1.0]:
				batch.box(Vector3(0.05, opening_h, 0.06), Vector3(side * (opening_w / 2.0 - 0.03), opening_h / 2.0, -0.05), Palette.DARK)
	else:
		if not open:
			batch.box(Vector3(opening_w, opening_h - 0.02, 0.05), Vector3(0, opening_h / 2.0, 0), Palette.STEEL_LIGHT)
			batch.box(Vector3(0.05, 0.2, 0.08), Vector3(opening_w / 2.0 - 0.1, 1.0, 0.03), Palette.DARK)  # poignée
			boxes.append([Vector3(opening_w, opening_h, 0.05), Vector3(0, opening_h / 2.0, 0)])
		else:  # battant ouvert à 90° vers l'avant, charnière côté -X
			batch.box(Vector3(0.05, opening_h - 0.02, opening_w), Vector3(-opening_w / 2.0, opening_h / 2.0, DEPTH / 2.0 + opening_w / 2.0), Palette.STEEL_LIGHT)
	batch.build(self)
	Mesher.collider(self, boxes)

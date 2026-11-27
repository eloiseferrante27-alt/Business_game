@tool
extends GmixAsset
## Barrière de sécurité modulaire (1,5 x 0,25 x 1,0 m, multiple de la grille de 0,5 m) : deux poteaux à platine, deux
## lisses à bandes jaune et noir. Raccordable bout à bout le long de X (les poteaux d'extrémité se touchent à la
## demi-épaisseur près). Sans façade : symétrique. Collision : un bloc sur toute la longueur.

const L := 1.5
const D := 0.25
const H := 1.0
const POST := 0.08
const STRIPES := 10

func _ready() -> void:
	super()
	_rebuild()


func _rebuild() -> void:
	if not is_node_ready():
		return
	Mesher.clear(self)
	var batch := Mesher.Batch.new()
	var yellow := Palette.MARK_YELLOW
	for side in [-1.0, 1.0]:
		var x: float = side * (L / 2.0 - POST / 2.0)
		batch.box(Vector3(POST, H, POST), Vector3(x, H / 2.0, 0), yellow)  # poteau
		batch.box(Vector3(0.16, 0.02, D), Vector3(x - side * 0.04, 0.01, 0), Palette.DARK)  # platine au sol
	var span := L - 2.0 * POST
	var step := span / STRIPES
	for y in [0.45, 0.85]:  # lisses : bandes jaune et noir alternées
		for i in STRIPES:
			var c := yellow if i % 2 == 0 else Palette.DARK
			batch.box(Vector3(step, 0.12, 0.05), Vector3(-span / 2.0 + step * (i + 0.5), y, 0), c)
	batch.build(self)
	Mesher.collider(self, [[Vector3(L, H, D), Vector3(0, H / 2.0, 0)]])

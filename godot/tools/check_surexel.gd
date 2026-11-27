extends SceneTree
## Vérifie les formules de SurExel (scenes/tablet/surexel.gd).
## Usage : godot --headless --path godot --script res://tools/check_surexel.gd ; code de sortie 0 si tout passe.


func _initialize() -> void:
	var grid := GmixSurExel.blank()
	grid[0][0] = "10"
	grid[1][0] = "2,5"
	grid[2][0] = "=A1*A2"
	grid[0][1] = "=SOMME(A1:A3)"
	grid[1][1] = "=MOYENNE(A1;A2)"
	grid[2][1] = "=SI(A3>20;\"ok\";\"bas\")"
	grid[3][1] = "=MAX(A1:A3)-MIN(A1:A3)"
	grid[4][1] = "=(A1+2)/4"
	grid[5][1] = "=B6"
	grid[6][1] = "=A1/0"
	grid[7][1] = "=SOMME(A1;"
	grid[8][1] = "=-A2+1"
	var cases := [
		[2, 0, 25.0], [0, 1, 37.5], [1, 1, 6.25], [2, 1, "ok"], [3, 1, 22.5], [4, 1, 3.0],
		[5, 1, GmixSurExel.ERROR], [6, 1, GmixSurExel.ERROR], [7, 1, GmixSurExel.ERROR], [8, 1, -1.5], [0, 0, 10.0],
	]
	var failures := 0
	for case: Array in cases:
		var got: Variant = GmixSurExel.value_of(grid, case[0], case[1])
		var ok: bool = is_equal_approx(got, case[2]) if case[2] is float and got is float else str(got) == str(case[2])
		if not ok:
			failures += 1
			printerr("ÉCHEC %s%d : attendu %s, obtenu %s" % [GmixSurExel.column_name(case[1]), case[0] + 1, case[2], got])
	print("SurExel : %d cas, %d en échec" % [cases.size(), failures])
	quit(1 if failures > 0 else 0)

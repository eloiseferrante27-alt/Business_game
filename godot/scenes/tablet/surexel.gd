class_name GmixSurExel
extends VBoxContainer
## SurExel : tableur de la tablette (outil de base), repris de l'outil du même nom de la contribution Amine
## (backend/app/static/tablet/spreadsheet.js) : cellules A1…, formules `=`, fonctions SOMME, MOYENNE, MIN, MAX, SI,
## plages `A1:B3`, séparateur `;`, virgule décimale. Les cellules vivent dans `cells` (tableau du parent) : elles
## survivent à la reconstruction de la tablette.

const ROWS := 12
const COLS := 6
const FUNCTIONS := ["SOMME", "MOYENNE", "MIN", "MAX", "SI"]
const ERROR := "#ERREUR"

var cells: Array = []  # [ligne][colonne] -> texte saisi
var _edits: Array = []  # [ligne][colonne] -> LineEdit
var _focus := Vector2i(-1, -1)


## Grille vide ROWS x COLS.
static func blank() -> Array:
	var grid := []
	for r in ROWS:
		var row := []
		row.resize(COLS)
		row.fill("")
		grid.append(row)
	return grid


static func column_name(c: int) -> String:
	return String.chr(65 + c)


## Valeur affichée d'une cellule : nombre, texte ou ERROR (formule illisible, référence circulaire).
static func value_of(grid: Array, r: int, c: int, depth := 0) -> Variant:
	if r < 0 or c < 0 or r >= grid.size() or c >= (grid[r] as Array).size():
		return 0.0
	var raw := str(grid[r][c]).strip_edges()
	if not raw.begins_with("="):
		var n := _numeric(raw)
		return raw if is_nan(n) else n
	if depth > 32:
		return ERROR
	var parser := _Parser.new(grid, raw.substr(1), depth + 1)
	var result: Variant = parser.parse()
	return ERROR if parser.failed else result


static func _numeric(text: String) -> float:
	var t := text.replace(" ", "").replace(" ", "").replace(",", ".")
	return float(t) if t.is_valid_float() else NAN


func _ready() -> void:
	add_theme_constant_override("separation", 6)
	if cells.is_empty():
		cells.append_array(blank())
	add_child(Ui.label("SurExel : saisissez des nombres ou des formules (=SOMME(B2:B6) ; =MOYENNE(B2;C2) ; =SI(B2>90;\"ok\";\"à suivre\")).", 15, Ui.MUTED, true))
	var grid := GridContainer.new()
	grid.columns = COLS + 1
	grid.add_theme_constant_override("h_separation", 2)
	grid.add_theme_constant_override("v_separation", 2)
	add_child(grid)
	grid.add_child(Ui.label(""))
	for c in COLS:
		var head := Ui.label(column_name(c), 15, Ui.ACCENT)
		head.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		grid.add_child(head)
	for r in ROWS:
		grid.add_child(Ui.label(str(r + 1), 15, Ui.ACCENT))
		var row := []
		for c in COLS:
			var edit := LineEdit.new()
			edit.custom_minimum_size.x = 110
			edit.size_flags_horizontal = Control.SIZE_EXPAND_FILL
			edit.focus_entered.connect(func() -> void: _enter(r, c))
			edit.focus_exited.connect(func() -> void: _leave(r, c))
			edit.text_submitted.connect(func(_t: String) -> void: edit.release_focus())
			grid.add_child(edit)
			row.append(edit)
		_edits.append(row)
	refresh()


## Remplit la grille à partir de la ligne 1 (valeurs brutes) et recalcule.
func load_rows(rows: Array) -> void:
	cells.clear()
	cells.append_array(blank())
	for r in mini(rows.size(), ROWS):
		for c in mini((rows[r] as Array).size(), COLS):
			cells[r][c] = str(rows[r][c])
	refresh()


## Affiche les valeurs calculées ; la cellule en cours d'édition garde sa formule.
func refresh() -> void:
	for r in _edits.size():
		for c in COLS:
			if Vector2i(r, c) == _focus:
				continue
			var shown: Variant = value_of(cells, r, c)
			(_edits[r][c] as LineEdit).text = GameText.number(shown) if shown is float else str(shown)


func _enter(r: int, c: int) -> void:
	_focus = Vector2i(r, c)
	(_edits[r][c] as LineEdit).text = str(cells[r][c])


func _leave(r: int, c: int) -> void:
	cells[r][c] = (_edits[r][c] as LineEdit).text
	_focus = Vector2i(-1, -1)
	refresh()


## Analyseur descendant : comparaison > somme > produit > unaire > primaire (nombre, texte, cellule, fonction, parenthèses).
class _Parser:
	var failed := false
	var _grid: Array
	var _depth: int
	var _tokens: Array = []
	var _i := 0

	func _init(grid: Array, source: String, depth: int) -> void:
		_grid = grid
		_depth = depth
		var re := RegEx.create_from_string("\\s*(\\d+(?:[.,]\\d+)?|\"[^\"]*\"|[A-Za-z]+[0-9]*|>=|<=|<>|[-+*/()=:;<>])")
		var at := 0
		var text := source.strip_edges()
		while at < text.length():
			var m := re.search(text, at)
			if m == null or m.get_start() != at:
				failed = true
				return
			_tokens.append(m.get_string(1))
			at = m.get_end()
			while at < text.length() and text[at] == " ":
				at += 1

	func parse() -> Variant:
		if failed:
			return null
		var v: Variant = _compare()
		if _i != _tokens.size():
			failed = true
		return v

	func _peek() -> String:
		return _tokens[_i] if _i < _tokens.size() else ""

	func _take(token: String) -> bool:
		if _peek() == token:
			_i += 1
			return true
		return false

	func _num(v: Variant) -> float:
		if v is float:
			return v
		if v is bool:
			return 1.0 if v else 0.0
		var n := GmixSurExel._numeric(str(v))
		if is_nan(n):
			if not str(v).is_empty():
				failed = true
			return 0.0
		return n

	func _compare() -> Variant:
		var left: Variant = _sum()
		var op := _peek()
		if op in ["=", "<>", "<", ">", "<=", ">="]:
			_i += 1
			var right: Variant = _sum()
			var a := _num(left)
			var b := _num(right)
			match op:
				"=": return is_equal_approx(a, b)
				"<>": return not is_equal_approx(a, b)
				"<": return a < b
				">": return a > b
				"<=": return a <= b
				_: return a >= b
		return left

	func _sum() -> Variant:
		var v: Variant = _product()
		while _peek() in ["+", "-"]:
			var op: String = _tokens[_i]
			_i += 1
			var right := _num(_product())
			v = _num(v) + right if op == "+" else _num(v) - right
		return v

	func _product() -> Variant:
		var v: Variant = _unary()
		while _peek() in ["*", "/"]:
			var op: String = _tokens[_i]
			_i += 1
			var right := _num(_unary())
			if op == "/" and is_zero_approx(right):
				failed = true
				return 0.0
			v = _num(v) * right if op == "*" else _num(v) / right
		return v

	func _unary() -> Variant:
		if _take("-"):
			return -_num(_unary())
		_take("+")
		return _primary()

	func _primary() -> Variant:
		var t := _peek()
		if t.is_empty():
			failed = true
			return 0.0
		_i += 1
		if t == "(":
			var v: Variant = _compare()
			if not _take(")"):
				failed = true
			return v
		if t.begins_with("\""):
			return t.substr(1, t.length() - 2)
		if t[0].is_valid_int():
			return float(t.replace(",", "."))
		var name := t.to_upper()
		if name in GmixSurExel.FUNCTIONS and _take("("):
			return _call(name)
		var cell := _cell(name)
		if cell.x < 0:
			failed = true
			return 0.0
		var v: Variant = GmixSurExel.value_of(_grid, cell.x, cell.y, _depth)
		if str(v) == GmixSurExel.ERROR:
			failed = true
		return v

	## Arguments séparés par `;` ; une plage A1:B3 donne toutes ses cellules.
	func _call(name: String) -> Variant:
		var args: Array = []
		if not _take(")"):
			while true:
				args.append_array(_argument())
				if _take(")"):
					break
				if not _take(";"):
					failed = true
					return 0.0
		if name == "SI":
			if args.size() < 2:
				failed = true
				return 0.0
			return args[1] if _num(args[0]) != 0.0 else (args[2] if args.size() > 2 else false)
		var numbers: Array = args.filter(func(a: Variant) -> bool: return a is float)
		match name:
			"SOMME":
				return numbers.reduce(func(acc: float, n: float) -> float: return acc + n, 0.0)
			"MOYENNE":
				if numbers.is_empty():
					failed = true
					return 0.0
				return numbers.reduce(func(acc: float, n: float) -> float: return acc + n, 0.0) / numbers.size()
			"MIN":
				return numbers.min() if not numbers.is_empty() else 0.0
			_:
				return numbers.max() if not numbers.is_empty() else 0.0

	func _argument() -> Array:
		var start := _i
		var first := _cell(_peek().to_upper())
		if first.x >= 0 and _i + 1 < _tokens.size() and _tokens[_i + 1] == ":":
			var last := _cell(str(_tokens[_i + 2]).to_upper() if _i + 2 < _tokens.size() else "")
			if last.x < 0:
				failed = true
				return []
			_i += 3
			var out: Array = []
			for r in range(mini(first.x, last.x), maxi(first.x, last.x) + 1):
				for c in range(mini(first.y, last.y), maxi(first.y, last.y) + 1):
					var v: Variant = GmixSurExel.value_of(_grid, r, c, _depth)
					if str(v) == GmixSurExel.ERROR:
						failed = true
					out.append(v)
			return out
		_i = start
		return [_compare()]

	## "B3" -> (ligne 2, colonne 1) ; (-1, -1) si ce n'est pas une cellule.
	func _cell(name: String) -> Vector2i:
		var m := RegEx.create_from_string("^([A-Z])([1-9][0-9]*)$").search(name)
		if m == null:
			return Vector2i(-1, -1)
		return Vector2i(int(m.get_string(2)) - 1, m.get_string(1).unicode_at(0) - 65)

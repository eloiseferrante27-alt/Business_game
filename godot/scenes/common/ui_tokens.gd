class_name UiTokens
extends RefCounted
## Jetons de direction artistique : seul endroit où l'on règle couleurs, rayons, espacements, polices et ambiance 3D.
## Palette chaude (brun cacao, crème, accent abricot) ; structure reprise du jeu de référence Business_game, avec l'accord
## de son autrice. Les noms LIME* désignent l'accent (nom historique, valeur abricot). Tailles ramenées à la lisibilité de G-mix (corps 18 px, jamais sous 15 px).
## Palette choisie une fois au démarrage par Session (`use`) ; pas de changement à chaud : les écrans déjà construits gardent leurs couleurs.
## `contrast_failures()` (appelée par `-Check`) calcule le rapport de contraste de chaque texte sur son fond (>= 4,5:1).

const DEFAULT_PALETTE := "ardoise"
## Palettes choisissables (argument `--palette=<id>` ou variable GMIX_PALETTE, lus par Session). `ardoise` (bleu et blanc) est la palette par défaut ;
## `cacao` est la sombre, `chaud` et `sauge` d'autres claires (contrastes calculés par `contrast_failures`). Une couleur ne s'écrit qu'ici.
const PALETTES := {
	"cacao": {  # cacao sombre
		"INK": "#fbf3e6",
		"MUTED": "#d3c4b2",
		"LIME": "#f4b066",
		"LIME_HOVER": "#f8c58b",
		"LIME_PRESSED": "#e49d4e",
		"ON_LIME": "#33200f",
		"OK": "#a9d28f",
		"WARN": "#f2c45e",
		"ERROR": "#f9a99a",
		"INFO": "#9fc7e0",
		"BACKDROP": "#1d1411",
		"PANEL": "#2a1e18",
		"FIELD": "#21170f",
		"EDGE": "#6b5240",
		"BUTTON": "#4a372b",
		"BUTTON_HOVER": "#5c4636",
		"BUTTON_PRESSED": "#38281e",
		"BUTTON_OFF": "#2e221b",
		"TEXT_OFF": "#ac9a8a",
		"PLACEHOLDER": "#b3a393",
		"TAB_OFF": "#241913",
		"MENU_HOVER": "#5c4636",
		"BEZEL": "#150e0b",
	},
	"chaud": {  # beige, bois clair, terracotta
		"INK": "#3a2e25",
		"MUTED": "#645444",
		"LIME": "#9a4929",
		"LIME_HOVER": "#ab5633",
		"LIME_PRESSED": "#8f4223",
		"ON_LIME": "#fffaf2",
		"OK": "#2f6f2f",
		"WARN": "#8a5a00",
		"ERROR": "#a3392b",
		"INFO": "#2a6590",
		"BACKDROP": "#e9e0d2",
		"PANEL": "#f7f1e7",
		"FIELD": "#fffbf4",
		"EDGE": "#c9baa6",
		"BUTTON": "#e8dccb",
		"BUTTON_HOVER": "#ddceb9",
		"BUTTON_PRESSED": "#d2c0a8",
		"BUTTON_OFF": "#eee6da",
		"TEXT_OFF": "#6e6050",
		"PLACEHOLDER": "#76685a",
		"TAB_OFF": "#ece3d6",
		"MENU_HOVER": "#ddceb9",
		"BEZEL": "#e9e0d2",
	},
	"sauge": {  # crème et sauge
		"INK": "#2b3329",
		"MUTED": "#515c4d",
		"LIME": "#55672f",
		"LIME_HOVER": "#657a38",
		"LIME_PRESSED": "#47562a",
		"ON_LIME": "#fbfaf0",
		"OK": "#2a7048",
		"WARN": "#85580a",
		"ERROR": "#9c3b30",
		"INFO": "#2d6788",
		"BACKDROP": "#e6e8d8",
		"PANEL": "#f5f4e8",
		"FIELD": "#fdfcf5",
		"EDGE": "#bfc6ab",
		"BUTTON": "#e3e7d2",
		"BUTTON_HOVER": "#d7ddc1",
		"BUTTON_PRESSED": "#cbd3b0",
		"BUTTON_OFF": "#ebeddf",
		"TEXT_OFF": "#5f6a5a",
		"PLACEHOLDER": "#6c7767",
		"TAB_OFF": "#e9ebdb",
		"MENU_HOVER": "#d7ddc1",
		"BEZEL": "#e6e8d8",
	},
	"ardoise": {  # gris-bleu clair, ardoise
		"INK": "#25303b",
		"MUTED": "#4d5b69",
		"LIME": "#3d5a80",
		"LIME_HOVER": "#4b6a94",
		"LIME_PRESSED": "#314a69",
		"ON_LIME": "#f8fafc",
		"OK": "#2b6e4b",
		"WARN": "#8a5a00",
		"ERROR": "#a13d3d",
		"INFO": "#1f6a8a",
		"BACKDROP": "#dfe5ec",
		"PANEL": "#f1f4f8",
		"FIELD": "#fafbfd",
		"EDGE": "#b7c2cf",
		"BUTTON": "#dde4ec",
		"BUTTON_HOVER": "#d0d9e4",
		"BUTTON_PRESSED": "#c3cedb",
		"BUTTON_OFF": "#e6ebf1",
		"TEXT_OFF": "#5a6672",
		"PLACEHOLDER": "#667380",
		"TAB_OFF": "#e5eaf0",
		"MENU_HOVER": "#d0d9e4",
		"BEZEL": "#dfe5ec",
	},
}

static var palette_id := DEFAULT_PALETTE

# --- Texte et accents, fonds et traits : valeurs de la palette choisie (`use`) ---
static var INK: Color = _c("INK")
static var MUTED: Color = _c("MUTED")
static var LIME: Color = _c("LIME")
static var LIME_HOVER: Color = _c("LIME_HOVER")
static var LIME_PRESSED: Color = _c("LIME_PRESSED")
static var ON_LIME: Color = _c("ON_LIME")
static var OK: Color = _c("OK")
static var WARN: Color = _c("WARN")
static var ERROR: Color = _c("ERROR")
static var INFO: Color = _c("INFO")
static var BACKDROP: Color = _c("BACKDROP")
static var PANEL: Color = _c("PANEL")
static var FIELD: Color = _c("FIELD")
static var EDGE: Color = _c("EDGE")
static var BUTTON: Color = _c("BUTTON")
static var BUTTON_HOVER: Color = _c("BUTTON_HOVER")
static var BUTTON_PRESSED: Color = _c("BUTTON_PRESSED")
static var BUTTON_OFF: Color = _c("BUTTON_OFF")
static var TEXT_OFF: Color = _c("TEXT_OFF")
static var PLACEHOLDER: Color = _c("PLACEHOLDER")
static var TAB_OFF: Color = _c("TAB_OFF")
static var MENU_HOVER: Color = _c("MENU_HOVER")
static var BEZEL: Color = _c("BEZEL")
static var MUTED_HEX: String = "#" + MUTED.to_html(false)  # hex aussi pour le BBCode
static var OK_HEX: String = "#" + OK.to_html(false)
static var WARN_HEX: String = "#" + WARN.to_html(false)
const GLASS_ALPHA := 0.86


# --- Rayons, espacements ---
const RADIUS_CONTROL := 10
const RADIUS_PANEL := 14
const RADIUS_MODAL := 18
const PANEL_PAD := Vector2i(16, 14)
const CONTROL_PAD := Vector2i(14, 7)
const FIELD_PAD := Vector2i(10, 7)
const TAB_PAD := Vector2i(20, 9)
const GAP := 10

# --- Polices (fichiers déposés par assets-3d ; absents : police par défaut de Godot) ---
const FONT_DISPLAY := "res://assets/fonts/ManropeBold.tres"  # titres
const FONT_BODY := "res://assets/fonts/DMSans.ttf"  # corps
const FONT_BODY_BOLD := "res://assets/fonts/DMSansBold.tres"  # gras du corps
const FONT_MONO := "res://assets/fonts/DMMono.ttf"  # étiquettes et chiffres
const BODY_SIZE := 18
const MIN_SIZE := 15
const HEADING_FROM := 20  # `Ui.label` pose la police des titres à partir de cette taille
const TAB_SIZE := 20
const TIP_SIZE := 16
const WINDOW_TITLE_SIZE := 18

# --- Ambiance 3D (atelier et usine) ---
# Couleurs : palette 3D de assets/procedural/palette.gd (assets-3d), qui reste la seule source.
const SKY_TOP := Palette.SKY  # hémisphère : ciel
const SKY_HORIZON := Palette.BACKGROUND  # fond et brouillard
const GROUND := Palette.GROUND_BOUNCE  # hémisphère : sol
const SUN := Palette.SUN  # soleil chaud
const FOG := Palette.BACKGROUND
const LAWN := Palette.GRASS  # herbe autour du hall
const TONE_EXPOSURE := 0.6  # l'ACES de Godot éclaircit (gain 1/0,6 en entrée) : exposition réduite pour garder le sauge de la palette
const AMBIENT_ENERGY := 0.45
const SUN_ENERGY := 0.8


static func _c(key: String) -> Color:
	return Color(str((PALETTES[palette_id] as Dictionary)[key]))


## Applique une palette (id inconnu : palette par défaut) puis recopie les alias de `Ui`, de `GameText` et des courbes.
## À appeler avant `Ui.make_theme()`.
static func use(id: String) -> void:
	palette_id = id if PALETTES.has(id) else DEFAULT_PALETTE
	INK = _c("INK")
	MUTED = _c("MUTED")
	LIME = _c("LIME")
	LIME_HOVER = _c("LIME_HOVER")
	LIME_PRESSED = _c("LIME_PRESSED")
	ON_LIME = _c("ON_LIME")
	OK = _c("OK")
	WARN = _c("WARN")
	ERROR = _c("ERROR")
	INFO = _c("INFO")
	BACKDROP = _c("BACKDROP")
	PANEL = _c("PANEL")
	FIELD = _c("FIELD")
	EDGE = _c("EDGE")
	BUTTON = _c("BUTTON")
	BUTTON_HOVER = _c("BUTTON_HOVER")
	BUTTON_PRESSED = _c("BUTTON_PRESSED")
	BUTTON_OFF = _c("BUTTON_OFF")
	TEXT_OFF = _c("TEXT_OFF")
	PLACEHOLDER = _c("PLACEHOLDER")
	TAB_OFF = _c("TAB_OFF")
	MENU_HOVER = _c("MENU_HOVER")
	BEZEL = _c("BEZEL")
	MUTED_HEX = "#" + MUTED.to_html(false)
	OK_HEX = "#" + OK.to_html(false)
	WARN_HEX = "#" + WARN.to_html(false)
	Ui.OK = OK
	Ui.WARN = WARN
	Ui.ERROR = ERROR
	Ui.MUTED = MUTED
	Ui.ACCENT = LIME
	Ui.TEXT = INK
	Ui.BACKDROP = BACKDROP
	Ui.PANEL = PANEL
	Ui.FIELD = FIELD
	Ui.EDGE = EDGE
	GameText.GREEN = OK_HEX
	GameText.ORANGE = WARN_HEX
	GameText.GREY = MUTED_HEX
	GmixPanelView.CHART_COLORS = [LIME, INFO, WARN, OK]
	GmixDebrief.VERDICT_COLORS = {"atteint": OK, "partiel": WARN, "non_atteint": ERROR, "sans_objet": MUTED}


## Rapport de contraste WCAG entre deux couleurs opaques (1 à 21).
static func contrast(a: Color, b: Color) -> float:
	var la := a.srgb_to_linear().get_luminance()
	var lb := b.srgb_to_linear().get_luminance()
	return (maxf(la, lb) + 0.05) / (minf(la, lb) + 0.05)


## Textes de l'interface avec leur fond : [légende, texte, fond]. Le verre sur le monde est pris sur du blanc (pire cas).
static func text_pairs() -> Array:
	var glass := PANEL.lerp(Color.WHITE, 1.0 - GLASS_ALPHA)
	var pairs: Array = [
		["texte sur panneau", INK, PANEL],
		["légende sur panneau", MUTED, PANEL],
		["accent sur panneau", LIME, PANEL],
		["texte sur champ", INK, FIELD],
		["indice de champ", PLACEHOLDER, FIELD],
		["texte sur bouton", INK, BUTTON],
		["texte sur bouton survolé", INK, BUTTON_HOVER],
		["texte sur bouton enfoncé", INK, BUTTON_PRESSED],
		["texte de contrôle inactif", TEXT_OFF, BUTTON_OFF],
		["bouton principal", ON_LIME, LIME],
		["bouton principal survolé", ON_LIME, LIME_HOVER],
		["bouton principal enfoncé", ON_LIME, LIME_PRESSED],
		["onglet choisi", INK, PANEL],
		["onglet", MUTED, TAB_OFF],
		["menu survolé", INK, MENU_HOVER],
	]
	for pair: Array in [["texte", INK], ["légende", MUTED], ["accent", LIME], ["ok", OK], ["alerte", WARN]]:
		pairs.append(["%s sur la coque de la tablette" % pair[0], pair[1], BEZEL])
	for pair: Array in [["texte", INK], ["légende", MUTED], ["accent", LIME], ["ok", OK], ["alerte", WARN], ["erreur", ERROR], ["info", INFO]]:
		pairs.append(["%s sur verre (monde clair derrière)" % pair[0], pair[1], glass])
		pairs.append(["%s sur panneau" % pair[0], pair[1], PANEL])
	return pairs


## Légendes des couples qui n'atteignent pas 4,5:1, pour chaque palette (liste vide : tout est lisible).
static func contrast_failures() -> Array[String]:
	var failures: Array[String] = []
	var current := palette_id
	for id: String in PALETTES:
		use(id)
		for pair: Array in text_pairs():
			var ratio := contrast(pair[1], pair[2])
			if ratio < 4.5:
				failures.append("%s (%s) : %.2f:1" % [pair[0], id, ratio])
	use(current)
	return failures

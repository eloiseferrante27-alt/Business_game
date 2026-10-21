extends Node3D

const API_BASE_URL := "http://127.0.0.1:8000"

@onready var _http: HTTPRequest = $HTTPRequest
@onready var _npc_manager: Node3D = $NpcManager

var _status_label: Label
var _week_label: Label
var _kpi_label: Label
var _events_label: Label
var _next_turn_button: Button


func _ready() -> void:
    _http.request_completed.connect(_on_request_completed)
    _build_interface()
    _load_state()


func _build_interface() -> void:
    var canvas := CanvasLayer.new()
    add_child(canvas)
    var panel := PanelContainer.new()
    panel.position = Vector2(16.0, 16.0)
    panel.custom_minimum_size = Vector2(320.0, 0.0)
    canvas.add_child(panel)

    var layout := VBoxContainer.new()
    layout.add_theme_constant_override("separation", 8)
    panel.add_child(layout)

    var title := Label.new()
    title.text = "G-mix | Supply Chain"
    title.add_theme_font_size_override("font_size", 22)
    layout.add_child(title)

    _status_label = Label.new()
    _status_label.text = "Connexion à l’API…"
    layout.add_child(_status_label)
    _week_label = Label.new()
    layout.add_child(_week_label)
    _kpi_label = Label.new()
    layout.add_child(_kpi_label)
    _events_label = Label.new()
    _events_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    layout.add_child(_events_label)

    _next_turn_button = Button.new()
    _next_turn_button.text = "Passer à la semaine suivante"
    _next_turn_button.pressed.connect(_advance_turn)
    layout.add_child(_next_turn_button)


func _load_state() -> void:
    _send_request("/api/state", HTTPClient.METHOD_GET)


func _advance_turn() -> void:
    _next_turn_button.disabled = true
    _status_label.text = "Simulation en cours…"
    _send_request("/api/next-turn", HTTPClient.METHOD_POST, "{}")


func _send_request(path: String, method: HTTPClient.Method, body: String = "") -> void:
    var headers := PackedStringArray()
    if method == HTTPClient.METHOD_POST:
        headers.append("Content-Type: application/json")
    var error := _http.request(API_BASE_URL + path, headers, method, body)
    if error != OK:
        _status_label.text = "Impossible de joindre l’API (" + str(error) + ")"
        _next_turn_button.disabled = false


func _on_request_completed(
    result: int,
    response_code: int,
    _headers: PackedStringArray,
    body: PackedByteArray
) -> void:
    _next_turn_button.disabled = false
    if result != HTTPRequest.RESULT_SUCCESS or response_code < 200 or response_code >= 300:
        _status_label.text = "Erreur API : HTTP " + str(response_code)
        return

    var state: Variant = JSON.parse_string(body.get_string_from_utf8())
    if not state is Dictionary:
        _status_label.text = "Réponse API invalide"
        return
    _display_state(state)


func _display_state(state: Dictionary) -> void:
    var kpis: Dictionary = state.get("kpis", {})
    _status_label.text = "API connectée"
    _week_label.text = "Semaine %s" % str(state.get("current_week", "?"))
    _kpi_label.text = "OTIF : %.1f %%   TRS : %.1f %%\nStocks : %s €   Ruptures : %s" % [
        float(kpis.get("otif", 0.0)),
        float(kpis.get("trs", 0.0)),
        str(kpis.get("stock_value", 0.0)),
        str(kpis.get("stockouts", 0)),
    ]
    var events: Array = state.get("events", [])
    _events_label.text = "Aléas : aucun" if events.is_empty() else "Aléas :\n" + "\n".join(PackedStringArray(events))
    _npc_manager.call("apply_state", state)


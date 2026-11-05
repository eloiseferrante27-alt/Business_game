"""Génération d'un business game d'usine (pack `engine: factory`, ADR 0007 et 0010) à partir de paramètres seulement.

Même principe que l'atelier : aucun texte libre ni appel à un modèle, la même graine donne le même jeu. Le pack
(ai/packs/usine.yaml) fournit les valeurs de référence, la difficulté en fixe les facteurs. Capacités, stocks et
trésorerie sont calibrés sur la demande, qui vient du débit attendu des machines de la partie (`factory.expected_h`).
Le plan du monde est posé par `layout.recompile_layout`, puis la spec est validée et jouée en pilote automatique.
"""

import copy
import math
import random
from typing import Any

from gmix.game import engine, factory, layout
from gmix.game.generation import apply_rules, autopilot_check
from gmix.game.spec import GameParams, SimSpec, _resolve_citations, load_pack

MAX_LOAD = 0.95  # charge réelle maximale (pack : client.charge)
MP_FILL = 0.75  # part des racks de matière remplie au départ, au plus
BAR_TOOLS = 6  # UI_LIMITS["tools"] : outils de barre par public
DEFAULT_LINES = 2


def generate_factory(params: GameParams) -> dict[str, Any]:
    pack = copy.deepcopy(load_pack(params.pack))
    seed = params.seed if params.seed is not None else random.SystemRandom().randrange(2**31)
    rng = random.Random(seed)
    level = dict(pack["difficulties"][params.difficulty])
    for key, profile in params.tunings.items():  # réglage choisi par la conception : valeur d'un autre profil
        level[key] = pack["difficulties"][profile][key]
    theme = pack["themes"][params.theme]
    company = params.company_name or rng.choice(theme["companies"])
    item = theme["products"][rng.randrange(len(theme["products"]))]
    n_lines = int(params.options.get("lines", DEFAULT_LINES))
    played = list(params.modules)

    machines = _machines(pack, item, level, n_lines)
    suppliers, offers = _offers(pack, item, level, params)
    spec: dict[str, Any] = {
        "kind": "simulation", "version": 2, "seed": seed,
        "meta": _meta(pack, params, theme, level, company, item),
        "params": params.model_dump(),
        "products": [], "components": [], "suppliers": suppliers, "offers": offers, "lines": [],
        "modules": [], "roles": [],
        "agents": [], "stations": [],
        "world": {"template": pack["world"]["template"], "size": list(pack["world"]["size"]),
                  "spawn": list(pack["world"]["spawn"]), "objects": []},
        "notions": [], "events": [],
        "economy": {
            "initial_cash": 0.0, "holding_rate_week": _val(pack, "pilotage.taux_possession_semaine"),
            "maintenance_rate": {}, "trs_drift": {}, "control_cost_rate": 0.0,
            "interest_rate_week": _val(pack, "pilotage.taux_interet_semaine"), "price_elasticity": 0.0,
            "defect_rate": 0.0, "demand_noise": 0.0,
            "events_probability": pack["events_levels"][params.events]["probability"], "transport": {},
        },  # fmt: skip
        "targets": {"otif": pack["targets"]["otif"], "trs": pack["targets"]["trs"],
                    "stockouts": pack["targets"]["stockouts"], "cash_final": 0.0},  # fmt: skip
        "departments": [], "panels": [], "provenance": _provenance(pack),
    }  # fmt: skip
    spec["modules"], spec["roles"] = _modules(pack, played)
    spec["notions"] = _notions(pack, spec)
    spec["events"] = [{"id": k, **v} for k, v in pack["events"].items() if set(v["modules"]) & set(played)]
    _calibrate(spec, pack, level, item, machines)
    spec["stations"], spec["agents"] = _stations_and_agents(pack, params, rng, spec)
    spec["factory"]["crew"] = _crew(pack, spec["factory"]["machines"])
    spec["notions"] = _notions(pack, spec)
    spec["panels"] = copy.deepcopy(pack["panels"])
    spec["tools"], spec["tutorial"] = _ui(pack, spec)
    spec, _ = layout.recompile_layout(spec, pack, [])
    for role in spec["roles"]:  # page de la tablette : département de la première station du module
        role["department_id"] = next((s["department_id"] for s in spec["stations"]
                                      if role["module_id"] in s["modules"]),
                                     None)  # fmt: skip
    spec = SimSpec.model_validate(spec).model_dump(mode="json")
    # Objectif de trésorerie calé sur la partie de référence, jamais sous la trésorerie de départ.
    initial_cash = spec["economy"]["initial_cash"]
    gain = max(0, autopilot_check(spec)["final_cash"] - initial_cash)
    spec["targets"]["cash_final"] = round(initial_cash + pack["targets"]["cash_share"] * gain, -2)
    return apply_rules(spec, pack)


def _val(pack: dict[str, Any], key: str) -> Any:
    return pack["values"][key]["value"]


def _meta(pack, params, theme, level, company, item) -> dict[str, Any]:
    titles = [pack["modules"][m]["title"].lower() for m in params.modules]
    text = ", ".join(titles[:-1]) + (" et " if len(titles) > 1 else "") + titles[-1]
    return {
        "title": f"{company} · {theme['label']}", "company": company, "client": theme["client"],
        "theme": params.theme, "theme_label": theme["label"],
        "pitch": f"{theme['description']} Pendant {params.weeks} semaines, votre équipe pilote {text} pour livrer "
        f"{theme['client']} à la date promise : {item['name'].lower()}, sans rupture de matière ni stock inutile. "
        f"Niveau {level['label'].lower()} : {level['detail']}.",
        "difficulty": params.difficulty, "difficulty_label": level["label"], "weeks": params.weeks,
        "players": {"min": params.players_min, "max": params.players_max}, "language": "fr",
        "domain": pack["domain"], "pack": params.pack,
    }  # fmt: skip


def _provenance(pack: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for key, entry in pack["values"].items():
        out[key] = {k: entry[k] for k in ("status", "source", "note") if k in entry}
    for rule in pack.get("placement_rules", []):  # annexe 0010 §3 : la provenance des règles de placement
        out[f"placement_rules.{rule['id']}"] = {k: rule[k] for k in ("status", "citation", "note") if k in rule}
    _resolve_citations(out, pack["domain"])
    return {k: {f: v[f] for f in ("status", "citation", "note") if f in v} for k, v in out.items()}


def _machines(pack, item, level, n_lines) -> list[dict[str, Any]]:
    """Une ligne = les opérations du produit, chacune sur la machine du type indiqué (annexe §1)."""
    asset = next(
        e["asset"]
        for d in pack["departments"]
        if d["id"] == "production"
        for e in d["elements"]
        if e["role"] == "machine"
    )  # 6c : l'asset de la machine est celui de l'élément « machine » du département production
    machines = []
    for line in range(1, n_lines + 1):
        for rank, (operation, type_id) in enumerate(item["operations"], start=1):
            t = pack["machine_types"][type_id]
            machines.append({
                "id": f"l{line}-m{rank}", "line_id": f"l{line}", "rank": rank, "name": f"M{rank} · {operation}",
                "operation": operation, "cycle_min": t["cycle_min"], "run_min": t["run_min"], "stop_min": t["stop_min"],
                "mtbf_h": round(t["mtbf_h"] * level["mtbf_factor"], 1), "weibull_shape": t["weibull_shape"],
                "mttr_h": t["mttr_h"], "setup_min": t["setup_min"],
                "defect_rate": round(t["defect_rate"] * level["defect_factor"], 4), "buffer": t["buffer"],
                "transfer_min": t["transfer_min"], "operators": t["operators"], "asset": asset,
            })  # fmt: skip
    return machines


def _offers(pack, item, level, params) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    profiles = _val(pack, "fournisseur.profils")
    mp = item["mp"]
    suppliers, offers = [], []
    for index, ((name, city), (profile, p)) in enumerate(zip(mp["suppliers"], profiles.items(), strict=True), start=1):
        lead = layout.site_lead_days({"params": params.model_dump()}, pack, f"fournisseur_{profile}")
        reliability = max(30.0, min(100.0, p["reliability"] + level["reliability_shift"]))
        cost = round(mp["cost"] * p["cost_factor"], 2)
        suppliers.append({"id": f"s{index}", "name": name, "region": city})
        offers.append({
            "id": f"o{index}", "supplier_id": f"s{index}", "component_id": "c1", "profile": profile, "lead_time": lead,
            "reliability": reliability, "unit_cost": cost, "min_order": p["min_pallets"],
            "label": f"{mp['name']} · {name} ({city}) · {lead} j · {reliability:.0f} % à l'heure · "
            f"{engine.money(cost)}/u. · min. {p['min_pallets']} palette(s)",
        })  # fmt: skip
    return suppliers, offers


def _modules(pack, played) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    modules, roles = [], []
    for module_id in played:
        src = pack["modules"][module_id]
        modules.append({
            "id": module_id, "title": src["title"], "description": src["description"], "role_id": src["role"]["id"],
            "stations": src["stations"], "actions": src["actions"], "autopilot": src["autopilot"],
            "notions": src["notions"],
        })  # fmt: skip
        roles.append({**src["role"], "module_id": module_id})
    return modules, roles


def _notions(pack, spec) -> list[dict[str, Any]]:
    """Notions des modules joués et de leurs agents : la spec ne garde que la citation résolue."""
    ids = [n for m in spec["modules"] for n in m["notions"]] + [n for a in spec["agents"] for n in a["notions"]]
    return [{"id": i, **{k: pack["notions"][i][k] for k in ("title", "text", "citation")}} for i in dict.fromkeys(ids)]


def _calibrate(spec, pack, level, item, machines) -> None:
    """Capacités, demande, stocks et trésorerie calés sur le débit attendu des machines (pack : client.charge)."""
    lg_src = {
        "units_per_pallet_mp": item["mp"]["units_per_pallet"],
        "unload_min_per_pallet": _val(pack, "reception.dechargement_min_palette"),
        "inspect_min_per_pallet": _val(pack, "reception.controle_min_palette"),
        "supplier_nonconform_rate": _val(pack, "fournisseur.taux_non_conforme"),
        "delivery_window_min": _val(pack, "fournisseur.creneau_livraison_min"),
        "mp_capacity_pallets": _val(pack, "stock_mp.capacite_palettes"), "kit_min": _val(pack, "stock_mp.kit_min"),
        "qc_min_per_unit": _val(pack, "qualite.controle_min_produit"),
        "units_per_case": _val(pack, "emballage.produits_par_colis"),
        "cases_per_pallet": _val(pack, "emballage.colis_par_palette"),
        "pack_min_per_case": _val(pack, "emballage.min_par_colis"),
        "wrap_min_per_pallet": _val(pack, "emballage.filmage_min_palette"),
        "pf_capacity_pallets": _val(pack, "entrepot_pf.capacite_palettes"),
        "load_min_per_pallet": _val(pack, "entrepot_pf.chargement_min_palette"),
        "repair_travel_min": _val(pack, "maintenance.trajet_min"),
        "preventive_min": _val(pack, "maintenance.preventif_min"),
    }  # fmt: skip
    lot = _val(pack, "pilotage.taille_lot")
    spec["factory"] = {
        "product_id": "p1", "lot_size": lot, "pf_min": 1,
        "bom": [{"component_id": "c1", "per_unit": item["mp"]["per_unit"]}],
        "machines": machines, "crew": [], "clock": copy.deepcopy(pack["clock"]),
        "logistics": lg_src,
        "customer": {
            "demand_per_day": 1, "variability": level["demand_variability"], "promised_days": level["promised_days"],
            "orders_per_day": _val(pack, "client.orders_per_day"),
            "pickup_window_min": _val(pack, "client.pickup_window_min"),
        },
        "resources": {"docks": 1, "forklifts": _val(pack, "stock_mp.chariots"),
                      "technicians": _val(pack, "maintenance.techniciens"),
                      "line_leads": _val(pack, "pilotage.chefs_de_ligne")},  # fmt: skip
        "costs": {"repair_per_h": _val(pack, "maintenance.cout_reparation_h"),
                  "preventive_per_intervention": _val(pack, "maintenance.cout_preventif"),
                  "operator_per_h": _val(pack, "pilotage.cout_operateur_h")},  # fmt: skip
        "protect_buffer": _val(pack, "machine.protect_buffer"),
    }  # fmt: skip
    line_ids = sorted({m["line_id"] for m in machines})
    spec["lines"] = [
        {"id": lid, "name": f"Ligne {lid[1:]}", "product_id": "p1", "capacity": 1, "trs": 50.0, "label": ""}
        for lid in line_ids
    ]
    spec["products"] = [{
        "id": "p1", "name": item["name"], "category": item["category"], "price": float(item["price"]),
        "unit_cost": float(item["cost"]), "demand": 1, "component_id": "c1", "line_id": line_ids[0],
        "initial_stock": 0, "safety_stock": 0,
    }]  # fmt: skip
    mp = item["mp"]
    spec["components"] = [{
        "id": "c1", "name": mp["name"], "unit_cost": float(mp["cost"]), "usage": 1, "initial_stock": 0,
        "safety_stock": 0, "product_id": "p1",
    }]  # fmt: skip
    spec["agents"] = [{"id": "x"}]  # Plant ne lit que les identifiants d'agents
    plant = factory.Plant(spec)
    hours = [factory.expected_h(plant, i) for i in range(plant.nl)]
    per_day = sum(hours) * plant.mpd / 60
    demand = max(1, int(level["load"] * per_day))
    if demand / per_day >= MAX_LOAD:
        raise ValueError("Charge réelle de l'usine trop haute pour la partie")
    yields = [factory.trs_factors(plant, i)["qualite"] for i in range(plant.nl)]
    mp_day = demand / (sum(yields) / len(yields)) * mp["per_unit"]
    cap_mp = lg_src["mp_capacity_pallets"] * lg_src["units_per_pallet_mp"]
    cap_pf = lg_src["pf_capacity_pallets"] * lg_src["units_per_case"] * lg_src["cases_per_pallet"]
    stock_mp = min(round(level["mp_stock_days"] * mp_day), int(MP_FILL * cap_mp))
    stock_pf = min(round(level["pf_stock_days"] * demand), cap_pf)
    days = plant.days
    spec["factory"]["customer"]["demand_per_day"] = demand
    spec["factory"]["pf_min"] = min(cap_pf, math.ceil(_val(pack, "pilotage.pf_min_jours") * demand))
    spec["factory"]["pf_max"] = min(cap_pf, math.ceil(_val(pack, "pilotage.pf_max_jours") * demand))
    spec["factory"]["mp_safety_days"] = _val(pack, "stock_mp.stock_securite_jours")
    spec["factory"]["logistics"]["qc_block_threshold"] = _block_threshold(yields, lot)
    spec["products"][0] |= {
        "demand": demand * days,
        "initial_stock": stock_pf,
        "safety_stock": spec["factory"]["pf_min"],
    }
    spec["components"][0] |= {
        "usage": max(1, round(mp_day * days)),
        "initial_stock": stock_mp,
        "safety_stock": max(1, round(mp_day)),
    }
    for line, theoretical, hour in zip(
        spec["lines"], (60 / m["cycle_min"] for m in _bottlenecks(plant)), hours, strict=True
    ):
        capacity = int(theoretical * plant.mpd / 60 * days)
        trs = max(30.0, min(100.0, round(100 * hour / theoretical, 1)))
        line |= {"capacity": capacity, "trs": trs,
                 "label": f"{line['name']} · {item['name']} · {capacity} u./sem. à 100 %"}  # fmt: skip
    weekly_purchase = mp_day * days * mp["cost"]
    spec["economy"]["initial_cash"] = round(weekly_purchase * level["cash_weeks"], -2)


def _bottlenecks(plant) -> list[dict[str, Any]]:
    return [plant.machines[i] for i in plant.bottleneck]


def _block_threshold(yields: list[float], lot: int) -> float:
    """Limite haute de la carte p (pack : qualite.seuil_blocage) : p + 3 x racine(p (1 - p) / n), n = lot."""
    p = 1 - sum(yields) / len(yields)
    return round(min(1.0, p + 3 * math.sqrt(p * (1 - p) / lot)), 3)


def _stations_and_agents(pack, params, rng, spec) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    played = {m["id"] for m in spec["modules"]}

    def modules_of(kind: str) -> list[str]:
        return [m["id"] for m in spec["modules"] if kind in m["stations"]]

    stations, agents = [], []
    personalities = pack["agent_tones"][params.agent_tone]["personalities"]
    offset = rng.randrange(len(personalities))

    def agent(agent_id, src, kind, module_id, department_id) -> None:
        pid = personalities[(offset + len(agents)) % len(personalities)]
        agents.append({
            "id": agent_id, "name": src["name"], "job": src["job"], "kind": kind, "module_id": module_id,
            "department_id": department_id, "facts": src["facts"],
            "personality": {"id": pid, **pack["personalities"][pid]}, "tasks": src["tasks"],
            "character": src["character"], "zone": department_id, "route": [[0.0, 0.0]],
            "notions": [n for n in src["notions"] if n in pack["notions"]],
        })  # fmt: skip

    for dep in pack["departments"]:
        for st in dep["stations"]:
            stations.append({
                "id": st["kind"], "kind": st["kind"], "label": st["label"], "position": [0.0, 0.0], "ref": None,
                "modules": modules_of(st["kind"]), "department_id": dep["id"],
            })  # fmt: skip
        if dep["id"] == "production":
            for m in spec["factory"]["machines"]:
                stations.append({
                    "id": f"machine_{m['id']}", "kind": "machine", "label": m["name"], "position": [0.0, 0.0],
                    "ref": m["id"], "modules": modules_of("machine"), "department_id": "production",
                })  # fmt: skip
        src = dep.get("agent")
        if src:
            module = src.get("module") if src.get("module") in played else None
            kind = (
                "module" if module else {"fournisseur": "fournisseur", "client": "client"}.get(dep["id"], "departement")
            )
            agent(f"agent_{dep['id']}", src, kind, module, dep["id"])
    for extra in params.extra_agents:
        src = pack["extra_agents"][extra]
        agent(f"agent_{extra}", src, extra, None, src["department"])
    return stations, agents


def _crew(pack, machines) -> list[dict[str, Any]]:
    crew = []
    for c in pack["crew"]:
        chars = c["characters"]
        if c.get("per") == "machine":
            for i, m in enumerate(machines):
                crew += [{
                    "id": f"op_{m['id']}", "job": c["job"], "department_id": "production", "machine_id": m["id"],
                    "character": chars[i % len(chars)],
                }]  # fmt: skip
        else:
            crew.append({"id": c["job"], "job": c["job"], "department_id": c["department"], "machine_id": None,
                         "character": chars[0]})  # fmt: skip
    return crew


def _ui(pack, spec) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Outils et tutoriel du pack, réduits à ce que la partie permet (6b)."""
    actions = {a["id"] for m in spec["modules"] for a in m["actions"]}
    kinds = {s["kind"] for s in spec["stations"]}
    agent_ids = {a["id"] for a in spec["agents"]}
    sites = {"fournisseur", "client"}

    def target_ok(sel: str) -> bool:
        head, _, name = sel.partition(":")
        return {"station": name in kinds, "agent": name == "*" or name in agent_ids, "site": name in sites}.get(
            head, False
        )

    tools = []
    for tool in copy.deepcopy(pack["tools"]):
        if tool["kind"] == "action" and tool["action_id"] not in actions:
            continue
        if "menu" in tool:
            tool["menu"] = [s for s in tool["menu"] if target_ok(s)]
        tools.append(tool)
    bar = [t for t in tools if t.get("audience", "joueur") == "joueur" and t.get("bar", True)]
    # shortcut: au-delà de 6 outils de barre, on masque en partant de la fin ceux qui ont un menu (restent
    # accessibles au clic sur le poste) ; la caméra n'a pas de menu : jamais masquée. Ordre à valider par game-designer.
    for tool in reversed(bar):
        if len(bar) <= BAR_TOOLS:
            break
        if tool.get("menu"):
            tool["bar"] = False
            bar.remove(tool)
    anchors = {f"panel:{p['id']}" for p in spec["panels"]} | {f"tool:{t['id']}" for t in tools}
    anchors |= {f"station:{k}" for k in kinds} | {f"dept:{d['id']}" for d in pack["departments"]}
    anchors |= {f"agent:{a}" for a in agent_ids}
    tutorial = [s for s in copy.deepcopy(pack["tutorial"]) if s["anchor"] in anchors]
    return tools, tutorial

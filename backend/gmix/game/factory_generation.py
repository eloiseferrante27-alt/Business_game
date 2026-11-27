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

from gmix.game import factory, layout
from gmix.game.generation import _money, apply_rules, autopilot_check
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
    first = rng.randrange(len(theme["products"]))
    # produit k = products[(i + k - 1) mod n] (annexe 0013 §3 bis, complément 8) ; une ligne au moins par produit
    items = [theme["products"][(first + k) % len(theme["products"])] for k in range(params.products)]
    n_lines = max(int(params.options.get("lines", DEFAULT_LINES)), params.products)
    played = list(params.modules)
    limits = pack["limits"]
    varied = (params.suppliers or limits["suppliers"][2]) != limits["suppliers"][2]

    machines = _machines(pack, items, level, n_lines, random.Random(f"{seed}:types") if varied else None)
    suppliers, offers = _offers(pack, items, level, params)
    spec: dict[str, Any] = {
        "kind": "simulation", "version": 2, "seed": seed,
        "meta": _meta(pack, params, theme, level, company, items),
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
    spec["modules"], spec["roles"], spec["role_plans"] = _modules(pack, played)
    spec["notions"] = _notions(pack, spec)
    spec["events"] = [{"id": k, **v} for k, v in pack["events"].items() if set(v["modules"]) & set(played)]
    _calibrate(spec, pack, level, items, machines, theme, params.clients or params.products)
    if len(params.world_plan) >= 2 or (params.buildings or 1) >= 2:  # campus : trajets calculés (annexe 0013 §2 bis)
        for field, key in (("walk_m_per_min", "trajet.marche_m_min"), ("forklift_m_per_min", "trajet.chariot_m_min"),
                           ("pallet_handling_min", "trajet.manutention_palette_min")):  # fmt: skip
            spec["factory"]["logistics"][field] = _val(pack, key)
            spec["provenance"][f"logistics.{field}"] = spec["provenance"][key]
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


def _meta(pack, params, theme, level, company, items) -> dict[str, Any]:
    titles = [pack["modules"][m]["title"].lower() for m in params.modules]
    text = ", ".join(titles[:-1]) + (" et " if len(titles) > 1 else "") + titles[-1]
    names = [i["name"].lower() for i in items]
    product = ", ".join(names[:-1]) + (" et " if len(names) > 1 else "") + names[-1]
    return {
        "title": f"{company} · {theme['label']}", "company": company, "client": theme["client"],
        "theme": params.theme, "theme_label": theme["label"],
        "pitch": f"{theme['description']} Pendant {params.weeks} semaines, votre équipe assure "
        f"{'les modules' if len(titles) > 1 else 'le module'} {text} pour livrer "
        f"{theme['client']} à la date promise : {product}, sans rupture de matière ni stock inutile. "
        f"Niveau {level['label'].lower()} : {_fragments(pack, params)}.",
        "difficulty": params.difficulty, "difficulty_label": level["label"], "weeks": params.weeks,
        "players": {"min": params.players_min, "max": params.players_max}, "language": "fr",
        "domain": pack["domain"], "pack": params.pack,
    }  # fmt: skip


def _fragments(pack: dict[str, Any], params: GameParams) -> str:
    """Réglages effectifs du pitch : pour chaque clé, le fragment du profil réellement appliqué (règle n° 4)."""
    profiles = pack["difficulties"]
    keys = profiles[params.difficulty]["fragments"]
    return ", ".join(f for k in keys if (f := profiles[params.tunings.get(k, params.difficulty)]["fragments"][k]))


def _provenance(pack: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for key, entry in pack["values"].items():
        out[key] = {k: entry[k] for k in ("status", "source", "note") if k in entry}
    for rule in pack.get("placement_rules", []):  # annexe 0010 §3 : la provenance des règles de placement
        out[f"placement_rules.{rule['id']}"] = {k: rule[k] for k in ("status", "citation", "note") if k in rule}
    _resolve_citations(out, pack["domain"])
    return {k: {f: v[f] for f in ("status", "citation", "note") if f in v} for k, v in out.items()}


def _machines(pack, items, level, n_lines, rng=None) -> list[dict[str, Any]]:
    """Une ligne = les opérations de son produit (ligne j : produit (j - 1) mod P), chacune sur la machine du type
    indiqué (annexe §1)."""
    asset = next(
        e["asset"]
        for d in pack["departments"]
        if d["id"] == "production"
        for e in d["elements"]
        if e["role"] == "machine"
    )  # 6c : l'asset de la machine est celui de l'élément « machine » du département production
    machines = []
    types = pack["machine_types"]
    ops_of = []
    for item in items:
        ops = item["operations"]
        if rng:  # type tiré par rang parmi ceux qui le permettent (machine.types_par_operation), le même par produit
            ops = [(op, rng.choice([k for k, v in types.items() if rank in v["ranks"]]))
                   for rank, (op, _) in enumerate(ops, start=1)]  # fmt: skip
        ops_of.append(ops)
    for line in range(1, n_lines + 1):
        item, ops = items[(line - 1) % len(items)], ops_of[(line - 1) % len(items)]
        for rank, (operation, type_id) in enumerate(ops, start=1):
            t = types[type_id]
            machines.append({
                "id": f"l{line}-m{rank}", "line_id": f"l{line}", "rank": rank, "name": f"M{rank} · {operation}",
                "operation": operation, "cycle_min": t["cycle_min"], "run_min": t["run_min"], "stop_min": t["stop_min"],
                "mtbf_h": round(t["mtbf_h"] * level["mtbf_factor"], 1), "weibull_shape": t["weibull_shape"],
                "mttr_h": t["mttr_h"], "setup_min": t["setup_min"],
                "defect_rate": round(t["defect_rate"] * level["defect_factor"], 4), "buffer": t["buffer"],
                "transfer_min": types[item["operations"][rank - 1][1]]["transfer_min"], "type": type_id,
                "operators": t["operators"], "asset": asset,
            })  # fmt: skip
    if (shape := level.get("bottleneck_shape")) is not None:  # P2 : forme propre au goulot (la plus lente de la ligne)
        for line in range(1, n_lines + 1):
            line_machines = [m for m in machines if m["line_id"] == f"l{line}"]
            max(line_machines, key=lambda m: m["cycle_min"])["weibull_shape"] = shape
    return machines


def _offers(pack, items, level, params) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Fournisseurs du premier produit ; chacun offre la matière de chaque produit (ids o1, o2... par matière puis
    fournisseur, annexe 0013 §3 bis)."""
    profiles = _val(pack, "fournisseur.profils")
    suppliers, offers = [], []
    base = [(n, c, pr) for (n, c), pr in zip(items[0]["mp"]["suppliers"], profiles, strict=True)]
    # règle de jeu : les 3 de la référence, puis les extra_suppliers du secteur (fournisseur.supplementaires)
    extra = [(e["name"], e["city"], e["profile"]) for e in pack["themes"][params.theme].get("extra_suppliers", [])]
    chosen = (base + extra)[: params.suppliers or len(base)]
    for k, item in enumerate(items, start=1):
        mp = item["mp"]
        for index, (name, city, profile) in enumerate(chosen, start=1):
            p = profiles[profile]
            lead = layout.site_lead_days({"params": params.model_dump()}, pack, f"fournisseur_{profile}")
            reliability = max(30.0, min(100.0, p["reliability"] + level["reliability_shift"]))
            cost = round(mp["cost"] * p["cost_factor"], 2)
            if k == 1:
                suppliers.append({"id": f"s{index}", "name": name, "region": city})
            offers.append({
                "id": f"o{(k - 1) * len(chosen) + index}", "supplier_id": f"s{index}", "component_id": f"c{k}",
                "profile": profile, "lead_time": lead, "reliability": reliability, "unit_cost": cost,
                "min_order": p["min_pallets"],
                "label": f"{mp['name']} · {name} ({city}) · {lead} j · {reliability:.0f} % à l'heure · "
                f"{_money(cost)} €/u. · min. {p['min_pallets']} palette(s)",
            })  # fmt: skip
    return suppliers, offers


def _modules(pack, played) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Modules joués, rôles (ceux des modules, puis ceux du pack dont une action est jouée) et plans de rôles
    (annexe 0013 §3 ter) ; un rôle ou un plan sans action jouée est retiré."""
    modules, roles = [], []
    for module_id in played:
        src = pack["modules"][module_id]
        modules.append({
            "id": module_id, "title": src["title"], "description": src["description"], "role_id": src["role"]["id"],
            "stations": src["stations"], "actions": src["actions"], "autopilot": src["autopilot"],
            "notions": src["notions"],
        })  # fmt: skip
        roles.append({**src["role"], "module_id": module_id, "actions": [a["id"] for a in src["actions"]]})
    module_of = {a["id"]: m["id"] for m in modules for a in m["actions"]}
    for role_id, src in (pack.get("roles") or {}).items():
        actions = [a for a in src["actions"] if a in module_of]
        if actions:
            module_id = src["module"] if src["module"] in played else module_of[actions[0]]
            roles.append({"id": role_id, "title": src["title"], "mission": src["mission"], "module_id": module_id,
                          "actions": actions})  # fmt: skip
    kept = {r["id"] for r in roles}
    plans = []
    for players, ids in sorted((pack.get("role_plans") or {}).items()):
        if ids := [r for r in ids if r in kept]:
            plans.append({"players": players, "roles": ids})
    return modules, roles, plans


def _notions(pack, spec) -> list[dict[str, Any]]:
    """Notions des modules joués et de leurs agents : la spec ne garde que la citation résolue."""
    ids = [n for m in spec["modules"] for n in m["notions"]] + [n for a in spec["agents"] for n in a["notions"]]
    return [{"id": i, **{k: pack["notions"][i][k] for k in ("title", "text", "citation")}} for i in dict.fromkeys(ids)]


def _calibrate(spec, pack, level, items, machines, theme, n_clients) -> None:
    """Capacités, demande, stocks et trésorerie calés sur le débit attendu des machines (pack : client.charge) ;
    à plusieurs produits, demande et stocks par produit, plafonds au prorata des lignes (annexe 0013 §3 bis, n° 4)."""
    item, n_products = items[0], len(items)
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
    if n_products > 1:  # loi de Little : même couverture en jours qu'au cahier (2 lignes) ; 1 produit : inchangé
        n_lines = len({m["line_id"] for m in machines})
        lg_src["pf_capacity_pallets"] = (
            lg_src["pf_capacity_pallets"] * max(n_lines, 2) // _val(pack, "entrepot_pf.lignes_cahier")
        )
    lot = _val(pack, "pilotage.taille_lot")
    spec["factory"] = {
        "product_id": "p1", "lot_size": lot, "pf_min": 1,
        "bom": [{"component_id": f"c{k}", "per_unit": it["mp"]["per_unit"]} | ({"product_id": f"p{k}"} if k > 1 else {})
                for k, it in enumerate(items, start=1)],
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
                  "damage_per_failure": pack["values"].get("maintenance.cout_degats_panne", {}).get("value", 0),
                  "operator_per_h": _val(pack, "pilotage.cout_operateur_h")},  # fmt: skip
        "protect_buffer": _val(pack, "machine.protect_buffer"),
    }  # fmt: skip
    line_ids = sorted({m["line_id"] for m in machines})
    spec["lines"] = [
        {
            "id": lid,
            "name": f"Ligne {lid[1:]}",
            "product_id": f"p{(int(lid[1:]) - 1) % n_products + 1}",
            "capacity": 1,
            "trs": 50.0,
            "label": "",
        }
        for lid in line_ids
    ]
    spec["products"] = [{
        "id": f"p{k}", "name": it["name"], "category": it["category"], "price": float(it["price"]),
        "unit_cost": float(it["cost"]), "demand": 1, "component_id": f"c{k}",
        "line_id": next(x["id"] for x in spec["lines"] if x["product_id"] == f"p{k}"),
        "initial_stock": 0, "safety_stock": 0,
    } for k, it in enumerate(items, start=1)]  # fmt: skip
    spec["components"] = [{
        "id": f"c{k}", "name": it["mp"]["name"], "unit_cost": float(it["mp"]["cost"]), "usage": 1, "initial_stock": 0,
        "safety_stock": 0, "product_id": f"p{k}",
    } | ({"units_per_pallet": it["mp"]["units_per_pallet"]} if k > 1 else {})
        for k, it in enumerate(items, start=1)]  # fmt: skip
    spec["agents"] = [{"id": "x"}]  # Plant ne lit que les identifiants d'agents
    plant = factory.Plant(spec)
    hours = [factory.expected_h(plant, i) for i in range(plant.nl)]
    yields = [factory.trs_factors(plant, i)["qualite"] for i in range(plant.nl)]
    cap_pf = lg_src["pf_capacity_pallets"] * lg_src["units_per_case"] * lg_src["cases_per_pallet"]
    days, mp_days, demands, stock_mps = plant.days, [], [], []
    for k, it in enumerate(items):
        mine = [ln for ln in range(plant.nl) if plant.line_prod[ln] == k]
        per_day = sum(hours[ln] for ln in mine) * plant.mpd / 60
        demand = max(1, int(level["load"] * per_day))
        if demand / per_day >= MAX_LOAD:
            raise ValueError("Charge réelle de l'usine trop haute pour la partie")
        mp_day = demand / (sum(yields[ln] for ln in mine) / len(mine)) * it["mp"]["per_unit"]
        cap_mp = lg_src["mp_capacity_pallets"] * plant.upps[k] * len(mine) // plant.nl  # prorata des lignes
        stock_mp = min(round(level["mp_stock_days"] * mp_day), int(MP_FILL * cap_mp))
        stock_pf = min(round(level["pf_stock_days"] * demand), cap_pf * len(mine) // plant.nl)
        demands.append(demand)
        mp_days.append(mp_day)
        stock_mps.append(stock_mp)
        spec["products"][k] |= {"demand": demand * days, "initial_stock": stock_pf}
        spec["components"][k] |= {"usage": max(1, round(mp_day * days)), "initial_stock": stock_mp,
                                  "safety_stock": max(1, round(mp_day))}  # fmt: skip
    top = max(demands)  # pf_min et pf_max communs, sur la plus forte demande d'un produit (complément 5)
    spec["factory"]["pf_min"] = min(cap_pf // n_products, math.ceil(_val(pack, "pilotage.pf_min_jours") * top))
    spec["factory"]["pf_max"] = min(cap_pf // n_products, math.ceil(_val(pack, "pilotage.pf_max_jours") * top))
    for product in spec["products"]:
        product["safety_stock"] = spec["factory"]["pf_min"]
    spec["factory"]["mp_safety_days"] = _val(pack, "stock_mp.stock_securite_jours")
    spec["factory"]["logistics"]["qc_block_threshold"] = _block_threshold(yields, lot)
    _clients(spec, theme, n_clients, demands)
    for line, theoretical, hour in zip(
        spec["lines"], (60 / m["cycle_min"] for m in _bottlenecks(plant)), hours, strict=True
    ):
        capacity = int(theoretical * plant.mpd / 60 * days)
        trs = max(30.0, min(100.0, round(100 * hour / theoretical, 1)))
        name = items[int(line["product_id"][1:]) - 1]["name"]
        line |= {"capacity": capacity, "trs": trs, "label": f"{line['name']} · {name} · {capacity} u./sem. à 100 %"}
    weekly_purchase = sum(d * days * it["mp"]["cost"] for d, it in zip(mp_days, items, strict=True))
    spec["economy"]["initial_cash"] = round(weekly_purchase * level["cash_weeks"], -2)
    _initial_orders(spec, pack, level, plant, mp_days, stock_mps)


def _clients(spec, theme, n_clients, demands) -> None:
    """Client i achète le produit ((i - 1) mod P) + 1 ; la demande d d'un produit est répartie entre ses n clients,
    d // n chacun et 1 de plus pour les d % n premiers (client.partage_demande) ; `customer` reste celui du client 1.
    1 produit et 1 client : `Factory.clients` reste vide (référence inchangée)."""
    f, n_products = spec["factory"], len(demands)
    names = [theme["client"], *theme.get("extra_clients", [])]
    if n_products == 1 and n_clients == 1:
        f["customer"]["demand_per_day"] = demands[0]
        return
    served = [i % n_products for i in range(n_clients)]
    f["clients"] = []
    for i, k in enumerate(served):
        rank = served[:i].count(k)  # rang du client parmi ceux de son produit
        share = demands[k] // served.count(k) + (rank < demands[k] % served.count(k))
        f["clients"].append({**f["customer"], "id": f"c{i + 1}", "name": names[i], "product_id": f"p{k + 1}",
                             "demand_per_day": max(1, share),
                             "site_id": "client" if i == 0 else f"client_{chr(97 + i)}"})  # fmt: skip
    f["customer"]["demand_per_day"] = f["clients"][0]["demand_per_day"]


def _initial_orders(spec, pack, level, plant, mp_days, stock_mps) -> None:
    """Règle n° 5a (calibrage non sourcé) : si le stock de départ d'une matière couvre moins que délai + 1 jour, une
    commande `offer` est déjà en route, arrivant au jour floor(mp_stock_days) (stock_mp.commande_initiale) ; c1 dans
    `initial_order`, c2 et c3 dans `initial_orders`. Place libre au prorata des lignes du produit."""
    rule = _val(pack, "stock_mp.commande_initiale")
    days, f = level["mp_stock_days"], spec["factory"]
    for k, (mp_day, stock_mp) in enumerate(zip(mp_days, stock_mps, strict=True)):
        offer = next(o for o in spec["offers"] if o["profile"] == rule["offer"] and o["component_id"] == plant.comps[k])
        need = offer["lead_time"] + rule["cover_extra_days"] - days
        if need <= 0:
            continue
        upp, lines = plant.upps[k], plant.line_prod.count(k)
        free = f["logistics"]["mp_capacity_pallets"] * lines // plant.nl - math.ceil(stock_mp / upp)
        pallets = min(_val(pack, "fournisseur.camion_palettes"), free, math.ceil(round(need * mp_day / upp, 2)))
        if pallets >= offer["min_order"]:
            order = {"offer_id": offer["id"], "pallets": pallets, "arrival_day": int(days)}
            if k == 0:
                f["initial_order"] = order
            else:
                f.setdefault("initial_orders", []).append(order)


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

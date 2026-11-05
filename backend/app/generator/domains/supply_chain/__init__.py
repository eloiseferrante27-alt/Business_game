"""Domaine supply chain : usine du monde v3 (fournisseurs -> quai -> réception -> stock -> lignes -> qualité ->
emballage -> logistique -> clients). Les sections qui ne varient pas viennent du scénario de base du pack."""

import copy
import math
from collections import Counter, defaultdict

from ....scenario import load_scenario
from ... import place_zones


def _up(value: float, step: int) -> int:
    return int(math.ceil(value / step - 1e-9) * step)


def _uniform(rng, bounds, digits: int = 1) -> float:
    return round(rng.uniform(*bounds), digits)


def build(pack: dict, rng, params: dict) -> dict:
    base = copy.deepcopy(load_scenario(pack["base_scenario"]))
    counts, ranges, ratios = pack["counts"], pack["ranges"], pack["ratios"]
    ops = pack["operations"]

    n = int(params.get("products") or rng.randint(*counts["products"]))
    n_machines = int(params.get("machines") or rng.randint(*counts["machines"]))
    if not 1 <= n <= min(len(pack["products"]), len(pack["line_names"])):
        raise ValueError(f"Nombre de produits hors catalogue : {n}")
    if not 2 <= n_machines <= 2 + len(ops["middle"]):
        raise ValueError(f"Nombre de machines hors catalogue : {n_machines}")

    base_items = {item["sku"]: item for item in base["stock_items"]}
    box_sku = base["packaging"]["box_sku"]
    sf_template = next(item for item in base["stock_items"] if item["category"] == "SF")

    # Produits, nomenclatures, demande
    chosen = rng.sample(pack["products"], n)
    demand, values, products, lines = {}, {}, [], []
    for i, (product, line_name) in enumerate(zip(chosen, rng.sample(pack["line_names"], n)), start=1):
        sku, sf, mat = f"SKU-{i:02d}", f"SF-{i:02d}", f"MAT-{i:02d}"
        values[sku] = float(rng.randint(*ranges["pf_unit_value"]))
        values[mat] = round(values[sku] * ratios["mp_value"], 2)
        values[sf] = round(values[sku] * ratios["sf_value"], 2)
        low, high = ranges["weekly_demand"]
        demand[sku] = 50 * rng.randint(low // 50, high // 50)
        products.append({"sku": sku, "category": product["category"], "semi_finished_sku": sf, "bom": {mat: 1}})
        lines.append({"id": f"LINE-{i:02d}", "name": f"Ligne {line_name}", "product_sku": sku})
    values[box_sku] = base_items[box_sku]["unit_value"]
    values["MAT-PDR"] = base_items["MAT-PDR"]["unit_value"]

    # Fournisseurs : chaque article acheté reçoit entre 2 et 3 offres distinctes (cahier des charges §4)
    articles = {"matiere": [next(iter(p["bom"])) for p in products], "emballage": [box_sku], "pdr": ["MAT-PDR"]}
    suppliers = []
    for family, skus in articles.items():
        pool = pack["suppliers"][family]
        offers = rng.randint(*counts["offers_per_article"])
        picked = rng.sample(pool, min(len(pool), max(offers, len(skus))))
        prices = [{} for _ in picked]
        for sku in skus:
            for index in sorted(rng.sample(range(len(picked)), min(offers, len(picked)))):
                prices[index][sku] = round(values[sku] * rng.uniform(*ranges["price_factor"]), 2)
        for supplier, price in zip(picked, prices):
            if price:
                suppliers.append({
                    "id": f"SUP-{len(suppliers) + 1:02d}", **supplier,
                    "lead_time_weeks": rng.randint(*ranges["lead_weeks"][family]),
                    "reliability": float(rng.randint(*ranges["reliability"])),
                    "nonconformity_rate": _uniform(rng, ranges["nonconformity_rate"]),
                    "prices": price,
                })
    best_lead = {sku: min(s["lead_time_weeks"] for s in suppliers if sku in s["prices"]) for skus in articles.values() for sku in skus}

    # Stock : point de commande >= consommation × délai + sécurité ; capacité >= point de commande + quantité
    def purchased(sku: str, weekly: float, template: dict) -> dict:
        minimum = _up(weekly * ratios["safety_weeks"], 50)
        reorder_point = _up(weekly * best_lead[sku] + minimum, 50)
        reorder_qty = _up(weekly * rng.uniform(*ranges["mp_reorder_weeks"]), 50)
        return {**template, "sku": sku, "unit_value": values[sku], "minimum": minimum, "reorder_point": reorder_point,
                "reorder_qty": reorder_qty, "initial": _up(reorder_point + weekly * rng.uniform(*ranges["mp_extra_initial_weeks"]), 50),
                "capacity_max": _up((reorder_point + reorder_qty) * ratios["storage_margin"], 100)}

    names = [product["name"] for product in chosen]
    mp_template = next(item for item in base["stock_items"] if item["category"] == "MP" and item["sku"] != box_sku)
    stock_items = [purchased(next(iter(p["bom"])), demand[p["sku"]], {**mp_template, "name": f"Composant · {name}"})
                   for p, name in zip(products, names)]
    stock_items.append(purchased(box_sku, sum(demand.values()) / base["packaging"]["products_per_box"], base_items[box_sku]))
    stock_items += [{**sf_template, "sku": p["semi_finished_sku"], "name": f"Semi-fini · {name}",
                     "unit_value": values[p["semi_finished_sku"]]} for p, name in zip(products, names)]
    for p, name in zip(products, names):
        weekly = demand[p["sku"]]
        stock_items.append({
            "sku": p["sku"], "name": name, "category": "PF", "unit": "pièce", "unit_value": values[p["sku"]],
            "initial": _up(weekly * rng.uniform(*ranges["pf_initial_weeks"]), 10),
            "minimum": _up(weekly * ratios["pf_minimum_weeks"], 10),
            "reorder_point": _up(weekly * ratios["pf_reorder_weeks"], 50),
            "reorder_qty": _up(weekly * ratios["pf_reorder_qty_weeks"], 50),
            "capacity_max": _up(weekly * ratios["pf_capacity_weeks"], 100),
        })
    stock_items.append(base_items["MAT-PDR"])

    # Gamme : machines en série, première et dernière opérations fixes
    middle = sorted(rng.sample(ops["middle"], n_machines - 2), key=ops["middle"].index)
    machines = [{
        "operation": operation,
        "cycle_minutes": _uniform(rng, ranges["cycle_minutes"]),
        "defect_rate": _uniform(rng, ranges["defect_rate"]),
        "mtbf_hours": rng.randint(*ranges["mtbf_hours"]),
        "mttr_hours": _uniform(rng, ranges["mttr_hours"]),
    } for operation in [ops["first"], *middle, ops["last"]]]

    customers = {**base["customers"], "weekly_demand": demand,
                 "names": rng.sample(pack["customers"], rng.randint(*counts["customers"]))}

    # Disposition : la chaîne s'allonge avec le nombre de machines
    layout = pack["layout"]
    zones = [dict(zone) for zone in layout["zones"]]
    for zone in zones:
        if zone["id"] == "chaine_production":
            zone["w"] = layout["production_width_base"] + layout["production_width_per_machine"] * n_machines

    return {
        **base,
        "name": "Usine générée · " + " / ".join(names[:2]) + (" …" if n > 2 else ""),
        "description": (f"Monde généré ({pack['label']}) : {n} produits, {n} lignes de {n_machines} machines, "
                        f"{len(suppliers)} fournisseurs, {len(customers['names'])} clients."),
        "stock_items": stock_items,
        "products": products,
        "routing": {**base["routing"], "semi_finished_after_machine": rng.randint(1, n_machines - 1), "machines": machines},
        "lines": lines,
        "suppliers": suppliers,
        "customers": customers,
        "layout": {"aisle": layout["aisle"], "zones": place_zones(zones, layout["rows"], layout["aisle"])},
    }


def validate(world: dict) -> list[str]:
    """Contrôles du cahier des charges §4 + ce que le moteur actuel attend. Marche aussi sur default.json."""
    try:
        return _validate(world)
    except (KeyError, TypeError, ValueError, ZeroDivisionError) as error:
        return [f"Champ manquant ou mal formé : {error!r}"]


def _validate(world: dict) -> list[str]:
    issues: list[str] = []
    stock = {item["sku"]: item for item in world["stock_items"]}
    category = {sku: item["category"] for sku, item in stock.items()}
    if len(stock) != len(world["stock_items"]):
        issues.append("SKU en double dans stock_items.")

    blocks = {block["id"] for block in world["blocks"]}
    issues += [f"Agent {a['id']} : bloc inconnu {a['block_id']}." for a in world["agents"] if a["block_id"] not in blocks]

    products = {p["sku"]: p for p in world["products"]}
    for sku, p in products.items():
        if category.get(sku) != "PF":
            issues.append(f"Produit {sku} absent du stock PF.")
        if category.get(p["semi_finished_sku"]) != "SF":
            issues.append(f"Produit {sku} : semi-fini {p['semi_finished_sku']} absent du stock SF.")
        issues += [f"Produit {sku} : composant {m} absent du stock MP." for m in p["bom"] if category.get(m) != "MP"]
    issues += [f"Ligne {line['id']} : produit inconnu {line['product_sku']}." for line in world["lines"] if line["product_sku"] not in products]

    box_sku = world["packaging"]["box_sku"]
    issues += [f"Article {sku} attendu par le moteur, absent du stock." for sku in (box_sku, "MAT-PDR") if sku not in stock]

    leads: dict[str, list[int]] = {sku: [] for sku, c in category.items() if c in ("MP", "PDR")}
    for supplier in world["suppliers"]:
        for sku in supplier["prices"]:
            if sku in leads:
                leads[sku].append(supplier["lead_time_weeks"])
            else:
                issues.append(f"Fournisseur {supplier['id']} : vend {sku}, qui n'est pas un article acheté.")
    issues += [f"Article {sku} : {len(l)} offre(s), il en faut au moins 2." for sku, l in leads.items() if len(l) < 2]

    machines = world["routing"]["machines"]
    issues += [f"Machine {m['operation']} : MTTR ({m['mttr_hours']} h) >= MTBF ({m['mtbf_hours']} h)." for m in machines if m["mttr_hours"] >= m["mtbf_hours"]]
    if not 1 <= world["routing"]["semi_finished_after_machine"] < len(machines):
        issues.append("Gamme : le passage en semi-fini doit se faire entre deux machines.")

    demand = world["customers"]["weekly_demand"]
    issues += [f"Demande client sur {sku}, produit inconnu." for sku in demand if sku not in products]
    weekly: dict[str, float] = defaultdict(float)
    for sku, p in products.items():
        for material, quantity in p["bom"].items():
            weekly[material] += demand.get(sku, 0) * quantity
    weekly[box_sku] += sum(demand.values()) / world["packaging"]["products_per_box"]
    for sku, consumption in weekly.items():
        if leads.get(sku) and sku in stock:
            need = consumption * min(leads[sku]) + stock[sku]["minimum"]
            if stock[sku]["reorder_point"] < need:
                issues.append(f"Article {sku} : point de commande {stock[sku]['reorder_point']} < consommation × délai + sécurité = {need:g}.")

    for sku, item in stock.items():
        if item["minimum"] > item["reorder_point"]:
            issues.append(f"Article {sku} : minimum au-dessus du point de commande.")
        if item["reorder_point"] + item["reorder_qty"] > item["capacity_max"] or item["initial"] > item["capacity_max"]:
            issues.append(f"Article {sku} : capacité de stockage {item['capacity_max']} insuffisante.")

    profiles = world["difficulty_profiles"]
    issues += [f"Profil de difficulté {name} manquant." for name in ("facile", "normal", "difficile") if name not in profiles]
    normal = profiles.get("normal")
    if normal and machines:
        per_line = min(normal["capacity"], world["work_minutes_per_week"] / max(m["cycle_minutes"] for m in machines))
        per_line *= normal["efficiency"] / 100
        lines_per_product = Counter(line["product_sku"] for line in world["lines"])
        issues += [f"Produit {sku} : demande {d}/sem. > capacité {lines_per_product[sku] * per_line:g}/sem. (profil normal)."
                   for sku, d in demand.items() if d > lines_per_product[sku] * per_line]
    return issues

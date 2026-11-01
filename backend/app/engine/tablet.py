"""Read-only tablet projection, computed on the server from journal replay."""
from .journal import Journal
from .kpis import customer_indicators


DEPARTMENTS = (
    ("fournisseurs", "Fournisseurs", "Fournisseurs", "Comparer les offres et approvisionner l’usine."),
    ("quai-dechargement", "Quai de déchargement", "Déchargement", "Suivre les camions fournisseurs."),
    ("reception", "Bureau de réception", "Réception", "Contrôler les livraisons avant leur mise en stock."),
    ("stock", "Stock", "Stock", "Matières premières, semi-finis et produits finis."),
    ("production", "Chaîne de production", "Production", "Lancer les ordres de fabrication et suivre les lignes."),
    ("qualite", "Contrôle qualité", "Qualité", "Suivre les produits conformes, retouchés et rebutés."),
    ("emballage", "Emballage", "Emballage", "Mettre en colis et préparer les produits finis."),
    ("maintenance", "Maintenance et stock PDR", "Maintenance", "Réparer les machines et gérer les pièces."),
    ("logistique", "Logistique & Transport", "Logistique", "Expédier les commandes depuis le stock PF."),
    ("clients", "Clients", "Clients", "Suivre la demande et les engagements de livraison."),
)


def metric(label, value, unit="", **extra):
    return dict(label=label, value=value, unit=unit, trend="Dernière période simulée", direction="flat", **extra)


def table(identifier, title, columns, rows):
    return dict(id=identifier, title=title, columns=[dict(key=key, label=label) for key, label in columns], rows=rows)


def tablet_snapshot(journal: Journal, *, game_id=0):
    state = journal.state
    kpi, report = state["kpis"], state["last_week"]
    customer_kpis = customer_indicators(journal)
    kpi["otif"] = customer_kpis["otif"]
    stocks, lines = state["stocks"], state["production_lines"]
    purchases, customers, orders = state["purchase_orders"], state["customer_orders"], state["production_orders"]
    by_sku = {item["sku"]: item for item in stocks}
    suppliers = {item["id"]: item for item in state["suppliers"]}
    open_customers = [item for item in customers if item["status"] in {"ouverte", "en retard"}]
    broken = [line for line in lines if not line["operational"]]
    queued = state["maintenance_queue"]
    alerts = []

    def alert(department, severity, title, detail):
        alerts.append(dict(id=f"SYS-ALERTE-{len(alerts)+1:02d}", departmentId=department,
                           severity=severity, title=title, detail=detail))

    for item in stocks:
        if item["quantity"] == 0:
            alert("maintenance" if item["category"] == "PDR" else "stock", "grave", f"Rupture : {item['name']}",
                  "Aucune unité disponible. Consultez les approvisionnements et les OF.")
        elif item["quantity"] <= item["reorder_point"]:
            alert("stock", "mineure", f"Stock bas : {item['name']}",
                  f"{item['quantity']} {item['unit']} disponibles ; point de commande {item['reorder_point']}.")
    for line in broken:
        alert("maintenance", "grave", f"{line['name']} en panne",
              "Intervention déjà planifiée." if line["id"] in queued else "Planifiez une intervention avec une pièce de rechange.")
    for order in open_customers:
        if order["status"] == "en retard":
            alert("clients", "grave", f"Commande {order['id']} en retard", f"{order['customer']} attend {order['quantity']} unités.")
    alerts.sort(key=lambda item: item["severity"] != "grave")

    stock_rows = [dict(**item, status="Rupture" if item["quantity"] == 0 else "Sous le seuil" if item["quantity"] <= item["reorder_point"] else "Disponible") for item in stocks]
    customer_table = table("customers", "Carnet de commandes", [("id", "Commande"), ("customer", "Client"), ("sku", "Produit"),
                            ("quantity", "Quantité"), ("due_week", "Échéance (semaine)"), ("mode", "Transport"), ("status", "Statut")], customers)
    shipment_table = table("trucks", "Camions de la dernière période", [("id", "Camion"), ("kind", "Type"),
                            ("label", "Partenaire"), ("quantity", "Quantité"), ("block_id", "Quai")], state["trucks"])
    all_machines = [dict(**machine, line=line["name"]) for line in lines for machine in line["machines"]]
    page_kpis = {
        "fournisseurs": [metric("Commandes en transit", len(purchases), "commandes"), metric("Achats de la période", report.get("purchases_cost", 0), "€")],
        "quai-dechargement": [metric("Camions reçus", report.get("received_orders", 0), "camions"), metric("Unités acceptées", report.get("received_units", 0), "unités")],
        "reception": [metric("Unités réceptionnées", report.get("received_units", 0), "unités"), metric("Unités non conformes", report.get("quarantined", 0), "unités")],
        "stock": [metric("Valeur du stock", kpi["stock_value"], "€"), metric("Articles à zéro", sum(item["quantity"] == 0 for item in stocks), "articles"), metric("PF sous leur minimum", kpi["stockouts"], "références")],
        "production": [metric("Produits conformes", kpi["produced"], "produits"), metric("Rendement des lignes", kpi["trs"], "%"), metric("OF en cours", len(orders), "OF")],
        "qualite": [metric("Taux de qualité", kpi["quality_rate"], "%"), metric("Produits retouchés", report.get("reworked", 0)), metric("Rebuts", report.get("quality_losses", 0))],
        "emballage": [metric("Produits emballés", report.get("packed", 0)), metric("Palettes de la période", report.get("pallets", 0)), metric("Produits en attente", sum(state["packing_queue"].values()))],
        "maintenance": [metric("Lignes en panne", len(broken)), metric("Interventions planifiées", len(queued)), metric("Pièces de rechange", by_sku.get("MAT-PDR", {}).get("quantity", 0))],
        "logistique": [metric("Unités expédiées", kpi["delivered"]), metric("Commandes livrées", report.get("customer_orders_delivered", 0)), metric("OTIF client", kpi["otif"], "%")],
        "clients": [metric("Taux de service", customer_kpis["service_rate"], "%"), metric("Commandes à servir", len(open_customers)), metric("Commandes en retard", sum(o["status"] == "en retard" for o in open_customers)), metric("Annulations de la période", report.get("customer_orders_cancelled", 0))],
    }
    page_tables = {
        "fournisseurs": [table("suppliers", "Fournisseurs et offres", [("id", "Référence"), ("name", "Fournisseur"), ("region", "Région"),
                         ("lead_time_weeks", "Délai (sem.)"), ("reliability", "Fiabilité (%)"), ("nonconformity_rate", "Non-conformité (%)")], list(suppliers.values())),
                         table("purchases", "Commandes fournisseurs", [("id", "Commande"), ("supplier", "Fournisseur"), ("sku", "Matière"),
                         ("quantity", "Quantité"), ("unit_price", "Prix unitaire (€)"), ("arrival_week", "Arrivée (semaine)")],
                         [dict(**order, supplier=suppliers.get(order["supplier_id"], {}).get("name", order["supplier_id"])) for order in purchases])],
        "quai-dechargement": [shipment_table],
        "reception": [table("reception", "Dernière réception", [("label", "Mesure"), ("value", "Valeur")],
                            [dict(label="Unités acceptées", value=report.get("received_units", 0)), dict(label="Unités non conformes écartées", value=report.get("quarantined", 0))])],
        "stock": [table("stock", "Stock unifié", [("sku", "Article"), ("name", "Désignation"), ("category", "Partie"), ("quantity", "Disponible"),
                         ("minimum", "Minimum"), ("reorder_point", "Point de commande"), ("reorder_qty", "Quantité conseillée"), ("capacity_max", "Capacité"), ("status", "État")], stock_rows)],
        "production": [table("lines", "Lignes de production", [("id", "Ligne"), ("name", "Nom"), ("product_sku", "Produit"), ("efficiency", "Efficacité (%)"), ("status", "État")],
                              [dict(**line, status="En service" if line["operational"] else "En panne") for line in lines]),
                       table("orders", "Ordres de fabrication", [("id", "OF"), ("sku", "Produit"), ("quantity", "Quantité"), ("semi_finished_done", "Semi-finis"), ("finished_done", "Terminés"), ("status", "État")], orders),
                       table("machines", "Machines et gamme", [("id", "Machine"), ("line", "Ligne"), ("operation", "Opération"), ("cycle_minutes", "Cycle (min)"), ("state", "État")], all_machines)],
        "qualite": [table("quality", "Bilan du contrôle", [("label", "Destination"), ("value", "Produits")],
                          [dict(label="Conformes", value=kpi["produced"]), dict(label="Retouchés", value=report.get("reworked", 0)), dict(label="Rebut", value=report.get("quality_losses", 0))])],
        "emballage": [table("packing", "File d’emballage", [("sku", "Produit"), ("name", "Désignation"), ("quantity", "En attente")],
                            [dict(sku=sku, name=by_sku[sku]["name"], quantity=quantity) for sku, quantity in state["packing_queue"].items()])],
        "maintenance": [table("repairs", "État des lignes", [("id", "Ligne"), ("name", "Nom"), ("status", "État"), ("intervention", "Intervention")],
                              [dict(id=line["id"], name=line["name"], status="En service" if line["operational"] else "En panne", intervention="Planifiée" if line["id"] in queued else "Aucune") for line in lines])],
        "logistique": [customer_table, shipment_table], "clients": [customer_table],
    }
    actions = {"fournisseurs": [dict(id="purchase", label="Commander de la matière"), dict(id="compare", label="Comparer les fournisseurs")],
               "stock": [dict(id="purchase", label="Réapprovisionner"), dict(id="production", label="Lancer un OF")],
               "production": [dict(id="production", label="Lancer un ordre de fabrication")],
               "maintenance": [dict(id="maintenance", label="Planifier une réparation"), dict(id="purchase", label="Commander des PDR")]}
    configs = {name: [] for name, *_ in DEPARTMENTS}
    for item in stocks:
        for key, label in (("minimum", "Stock minimum"), ("reorder_point", "Point de commande"), ("reorder_qty", "Quantité commandée")):
            configs["stock"].append(dict(id=f"{item['sku']}:{key}", label=f"{label} · {item['name']}", value=item[key], right="verrouille",
                                        reason="Les réglages de ce monde sont en lecture seule."))
    parameters = {name: [] for name, *_ in DEPARTMENTS}
    parameters["production"] = [dict(label=f"{machine['id']} · {machine['operation']}", value=f"{machine['cycle_minutes']} min / produit · MTBF {machine['mtbf_hours']} h · MTTR {machine['mttr_hours']} h") for machine in all_machines]
    parameters["fournisseurs"] = [dict(label=supplier["name"], value=f"Délai {supplier['lead_time_weeks']} semaines · fiabilité {supplier['reliability']} %") for supplier in suppliers.values()]
    departments = []
    for identifier, name, short, description in DEPARTMENTS:
        relevant = [a for a in alerts if a["departmentId"] == identifier or (identifier == "production" and a["departmentId"] == "maintenance")
                    or (identifier == "logistique" and a["departmentId"] == "clients")]
        status = "rouge" if any(a["severity"] == "grave" for a in relevant) else "orange" if relevant else "vert"
        departments.append(dict(id=identifier, name=name, shortName=short, description=description, status=status,
                                kpis=page_kpis[identifier], configurations=configs[identifier], worldParameters=parameters[identifier],
                                actions=actions.get(identifier, []), tables=page_tables[identifier]))
    events = []
    recorded_messages = {(e["time"]["period"], e["message"]) for e in journal.events if e["type"] == "event"}
    department_for_path = {"stocks": "stock", "purchase_orders": "fournisseurs", "production_orders": "production", "production_lines": "production",
                           "customer_orders": "clients", "maintenance_queue": "maintenance", "packing_queue": "emballage"}
    for event in journal.events:
        path = event["path"]
        if event["type"] in {"refusal", "event"}:
            message = event["message"]
        elif path == ["events"]:
            before = set(event["old_state"] or [])
            for text in event["new_state"]:
                if text not in before and (event["time"]["period"], text) not in recorded_messages:
                    events.append(dict(time=f"Semaine {event['time']['period']}", period=event["time"]["period"], departmentId="production", type="evenement", cause=event["cause"], message=text))
            continue
        elif path and path[0] in department_for_path:
            field = str(path[-1])
            message = f"{event['element']} · {field} : {event['old_state']} → {event['new_state']}"
            if len(message) > 300:
                message = f"{event['element']} · {path[0]} mis à jour."
        else:
            continue
        events.append(dict(time=f"Semaine {event['time']['period']}", period=event["time"]["period"], departmentId=event.get("department", department_for_path.get(path[0] if path else "", "stock")),
                           type=event["type"], cause=event["cause"], message=message))
    tool_list = [("tableur", "Tableur", "Vos calculs et comparaisons, sans modifier la partie."),
                 ("carte", "Carte du monde", "Plan de l’usine et partenaires du scénario."),
                 ("graphiques", "Graphiques", "Historique réel des périodes jouées."),
                 ("planning", "Planning", "Échéances des commandes et ordres en cours."),
                 ("journal", "Journal", "Décisions, changements d’état et refus enregistrés.")]
    return dict(mode="live", gameId=game_id, companyName=state["company_name"], started=state["started"],
                clock=dict(unit="week", period=state["current_week"], label=f"Semaine {state['current_week']}", canAdvance=state["started"], supportsRealtime=False),
                departments=departments, tools=[dict(id=i, name=n, description=d, available=True) for i, n, d in tool_list],
                globalKpis=[metric(label, kpi[key], unit, id=key, departmentId=dep) for key, label, unit, dep in
                            [("otif", "OTIF clients", "%", "clients"), ("trs", "Rendement des lignes", "%", "production"),
                             ("produced", "Production de la période", "produits", "production"), ("stock_value", "Valeur du stock", "€", "stock"),
                             ("quality_rate", "Taux de qualité", "%", "qualite"), ("delivered", "Produits expédiés", "produits", "logistique")]],
                alerts=alerts, objectives=[], events=list(reversed(events)), history=customer_kpis["history"], raw=journal.state)

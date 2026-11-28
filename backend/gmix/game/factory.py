"""Noyau de simulation d'usine (docs/decisions/0007, annexe §1 à §3) : un tour est une suite de jours de
`minutes_per_day` minutes simulées, calculée par événements discrets (`heapq`). Fonction pure : l'état JSON d'entrée
n'est pas modifié, l'état de sortie est un nouveau dictionnaire, la chronologie (`Timeline`) est rendue à part.
Ni entrée-sortie, ni horloge, ni modèle : le hasard vient de flux `random.Random` par source (machine, fournisseur,
client), dérivés de la graine de la spec par une chaîne de caractères (stable d'un processus à l'autre).

Le temps est continu d'un tour au suivant (la nuit et le week-end n'existent pas) : les événements qui dépassent la
fin du tour sont gardés dans l'état, avec des dates relatives, et reprennent au tour suivant.

Flux : commande d'achat -> camion (quai) -> déchargement -> contrôle des palettes (quarantaine) -> stock MP -> kit
d'un lot (chariot) -> machine 1 -> ... -> machine k (tables d'attente) -> contrôle (bon ou rebut) -> emballage ->
entrepôt PF -> camion du client (quai). Les postes (réception, chariot, contrôle, emballage, entrepôt) s'arrêtent
aux pauses `Clock.breaks` ; le technicien et le quai non. Tout nombre vient de la spec (donc du pack) ; les seules
règles propres au moteur sont écrites en constantes ci-dessous.
"""

import bisect
import copy
import heapq
import math
import random
from collections import deque
from typing import Any, get_args

from gmix.game import layout
from gmix.game.spec import COUNTERS, MachineState, frame_times

STATES = get_args(MachineState)
ARRET, MARCHE, PAUSE, REGLAGE, PANNE, ATTENTE, PLEINE = range(7)  # index dans STATES
IDLE, SETUP, RUN, BLOCKED = range(4)  # phase du produit tenu par une machine
SUPPLIER_LATE_DAYS = 1  # pack usine : fournisseur.retard_jours (calibre) ; une livraison en retard arrive le lendemain
KEPT_ORDERS = 10  # commandes et OF clos gardés dans l'état
KEPT_LOTS = 60  # correspondances lot -> OF gardées
INF = float("inf")
AUTO_PRIO = 1  # après les commandes du client du même instant
FRAME_PRIO = 9  # un instantané voit l'état après tous les événements datés du même instant
SPAN_KINDS = {"mdone", "mfail", "msetup", "mostop"}  # événements de machine qui portent un jeton de génération


class Plant:
    """Constantes d'une usine, lues une fois dans `spec["factory"]` (le moteur peut la garder pour tous les tours)."""

    def __init__(self, spec: dict[str, Any]) -> None:
        f = spec["factory"]
        clock, self.lg, self.cu, self.rs, self.costs = (
            f["clock"],
            f["logistics"],
            f["customer"],
            f["resources"],
            f["costs"],
        )
        self.seed = spec["seed"]
        self.mpd, self.days, self.start_h, self.frame_min = (
            clock["minutes_per_day"], clock["days_per_turn"], clock["day_start_h"], clock["frame_min"],
        )  # fmt: skip
        self.T = self.days * self.mpd
        self.breaks = sorted((s, d) for s, d in clock["breaks"])
        self.lot_size, self.pf_min, self.protect = f["lot_size"], f["pf_min"], f["protect_buffer"]
        self.pallet_pf = self.lg["units_per_case"] * self.lg["cases_per_pallet"]
        used = {m["line_id"] for m in f["machines"]}
        self.line_ids = [line["id"] for line in spec["lines"] if line["id"] in used]
        rank = {lid: i for i, lid in enumerate(self.line_ids)}
        self.machines = sorted(f["machines"], key=lambda m: (rank[m["line_id"]], m["rank"]))
        self.mids = [m["id"] for m in self.machines]
        self.n, self.nl = len(self.machines), len(self.line_ids)
        self.line_machines: list[list[int]] = [[] for _ in self.line_ids]
        self.line_of = []
        for i, m in enumerate(self.machines):
            self.line_of.append(rank[m["line_id"]])
            self.line_machines[rank[m["line_id"]]].append(i)
        self.first = [ms[0] for ms in self.line_machines]
        self.last = [ms[-1] for ms in self.line_machines]
        self.bottleneck = [  # le goulot est la machine la plus lente de la ligne (la première en cas d'égalité)
            max(ms, key=lambda i: self.machines[i]["cycle_min"]) for ms in self.line_machines
        ]
        self.spares = f.get("spares")  # pièces de rechange par type de machine (annexe 0013 §3 quater) ; None : aucune
        if self.spares:
            self.mtype = [m.get("type") or m["id"] for m in self.machines]
            self.types = sorted(set(self.mtype))
            work_h = (self.mpd - sum(d for _, d in self.breaks)) / 60  # une journée de marche par machine
            self.s_star = {
                t: _poisson_stock(
                    sum(work_h / m["mtbf_h"] for m, mt in zip(self.machines, self.mtype, strict=True) if mt == t),
                    self.spares["service_level"],
                )
                for t in self.types
            }
            self.hold_rate = spec["economy"]["holding_rate_week"]
        self.scale = [m["mtbf_h"] * 60 / math.gamma(1 + 1 / m["weibull_shape"]) for m in self.machines]
        self.agents = {a["id"] for a in spec["agents"]} | {c["id"] for c in f["crew"]}
        # produits fabriqués (un par ligne en multi-produit) : une matière, une nomenclature, un stock PF chacun ;
        # les attributs sans suffixe (component, upp, mp0...) sont ceux du premier produit (partie à un produit)
        made = {line.get("product_id", f["product_id"]) for line in spec["lines"] if line["id"] in used}
        self.pids = [p["id"] for p in spec["products"] if p["id"] in made]
        self.np = len(self.pids)
        bom = {b.get("product_id") or f["product_id"]: b for b in f["bom"]}
        comps = {c["id"]: c for c in spec["components"]}
        self.comps = [bom[pid]["component_id"] for pid in self.pids]
        self.p_of_comp = {c: p for p, c in enumerate(self.comps)}
        self.per_units = [bom[pid]["per_unit"] for pid in self.pids]
        self.needs = [math.ceil(self.lot_size * u) for u in self.per_units]  # matière d'un kit (un lot)
        self.upps = [comps[c].get("units_per_pallet") or self.lg["units_per_pallet_mp"] for c in self.comps]
        self.mp0s = [comps[c]["initial_stock"] for c in self.comps]
        self.pf0s = [next(p["initial_stock"] for p in spec["products"] if p["id"] == pid) for pid in self.pids]
        self.component, self.per_unit, self.need, self.upp = (
            self.comps[0],
            self.per_units[0],
            self.needs[0],
            self.upps[0],
        )
        self.mp0, self.pf0 = self.mp0s[0], self.pf0s[0]
        made_by = {x["id"]: x.get("product_id", f["product_id"]) for x in spec["lines"]}
        self.line_prod = [self.pids.index(made_by[lid]) for lid in self.line_ids]
        self.prod_of_line = dict(zip(self.line_ids, self.line_prod, strict=True))
        self.multi = bool(f.get("clients")) or self.np > 1  # états et vues gardent leur forme d'avant sinon
        self.clients = [  # un acheteur par client ; sans `clients`, `customer` seul achète le produit de l'usine
            {**c, "p": self.pids.index(c["product_id"])} for c in f.get("clients") or []
        ] or [{**f["customer"], "id": "c1", "p": self.pids.index(f["product_id"]), "site_id": None}]
        sites = (spec.get("world") or {}).get("sites") or []  # camions de la carte : aucun événement sans site
        by_supplier = {s["supplier_id"]: s["id"] for s in sites if s.get("supplier_id")}
        self.offer_site = {o["id"]: by_supplier[o["supplier_id"]] for o in spec.get("offers", [])
                           if o.get("supplier_id") in by_supplier}  # fmt: skip
        self.client_site = next((s["id"] for s in sites if s.get("kind") == "client"), None)
        for c in self.clients:
            c["site"] = c.get("site_id") or self.client_site
        # trajets du campus (annexe 0013 §2 bis) : vitesses absentes (1 bâtiment) = durées fixes du hall de référence
        self.kit_t, self.walk_t = 0.0, self.lg["repair_travel_min"]
        self.pal_h = self.pal_t = None
        if self.lg.get("walk_m_per_min") is not None:
            links = layout.TIMED_LINKS
            self.kit_t = layout.travel_min(spec, *links["kit"])
            self.walk_t = layout.travel_min(spec, *links["repair"])
            if self.lg.get("pallet_handling_min") is not None:
                self.pal_h, self.pal_t = self.lg["pallet_handling_min"], layout.travel_min(spec, *links["pallet"])


def _poisson_stock(mean: float, level: float) -> int:
    """Plus petit S >= 1 tel que P(Poisson(mean) >= S) <= 1 - level : le stock du pilote pour un type de machine."""
    term = cdf = math.exp(-mean)  # P(N = 0) puis P(N <= S - 1)
    s = 1
    while 1.0 - cdf > 1.0 - level:
        term *= mean / s
        cdf += term
        s += 1
    return s


def _rng(plant: Plant, *key: Any) -> random.Random:
    return random.Random(":".join(str(k) for k in (plant.seed, *key)))


def _split(key: Any) -> tuple[int, int]:
    """Clé d'un camion client : le jour (client c1, forme historique) ou « jour-n° du client »."""
    day, _, k = str(key).partition("-")
    return int(day), int(k or 0)


def _hazard(rng: random.Random) -> float:
    """Seuil de risque cumulé tiré à chaque remise à zéro de l'âge : la panne arrive quand (âge / échelle)^forme
    l'atteint (loi de Weibull ; avec une forme de 1, loi exponentielle sans mémoire)."""
    return -math.log(1.0 - rng.random())


def spares_target(plant: Plant, cfg: dict[str, Any] | None) -> dict[str, int]:
    """Stock visé par type : S* du pilote (cfg None) ou `pieces` par type couvert par `cible` du joueur."""
    if cfg is None:
        return dict(plant.s_star)
    covered = {"aucune": set(), "goulot": {plant.mtype[b] for b in plant.bottleneck}, "toutes": set(plant.types)}
    return {t: cfg["pieces"] if t in covered[cfg["cible"]] else 0 for t in plant.types}


def initial_state(plant: Plant) -> dict[str, Any]:
    ids = plant.line_ids
    spares = {}
    if plant.spares:  # clés ajoutées seulement avec `spares` : une spec sans pièces garde l'état d'avant
        spares = {"spares": {
            "target": dict(plant.s_star), "stock": dict(plant.s_star), "transit": dict.fromkeys(plant.types, 0),
            "waiting": {t: [] for t in plant.types}, "reserved": [],
        }}  # fmt: skip
    return spares | {
        "day": 0,
        "seq": 0,
        "ids": {"lot": 0, "of": 0, "po": 0, "co": 0},
        "settings": {
            "preventive": dict.fromkeys(ids, "aucune"),
            "priority": "arrivee",
            "protect": dict.fromkeys(ids, "aucune"),
        }
        | ({"spares": None} if plant.spares else {}),  # None : stock S* du pilote ; sinon {cible, pieces}
        "machines": [
            {
                "cur": None,
                "phase": IDLE,
                "rem_setup": 0.0,
                "rem_cycle": 0.0,
                "seg": None,
                "gen": 0,
                "ostop": False,
                "down": 0,
                "age": 0.0,
                "hazard": _hazard(_rng(plant, "panne", 0, mid)),
                "rsince": 0.0,
                "last_lot": None,
                "fail_t": None,
                "wake": None,
            }
            for mid in plant.mids
        ],  # fmt: skip
        "tables": [[] for _ in plant.mids],
        "pools": [[] for _ in ids],
        "ofs": [],
        "lot_of": {},
        "lot_left": {},
        "mp": {"units": sum(plant.mp0s), "staged": 0, "quarantine": 0, "reserved": 0}
        | (
            {
                "by": {
                    "units": list(plant.mp0s),
                    "staged": [0] * plant.np,
                    "quarantine": [0] * plant.np,
                    "reserved": [0] * plant.np,
                }
            }
            if plant.multi
            else {}
        ),
        "inflight": [0] * plant.nl,
        "starve": [None] * plant.nl,
        "pending": [],
        "receiving": {},
        "dock": {"busy": 0, "queue": []},
        "insp": {"busy": False, "queue": []},
        "orders": [],
        "loading": {},
        "pf": {"units": sum(plant.pf0s)} | ({"by": list(plant.pf0s)} if plant.multi else {}),
        "qc": {"busy": False, "wake": None},
        "pack": {"conf": 0, "busy": None, "cases": 0, "units": 0, "wait": False}
        | ({"by_conf": [0] * plant.np, "p": None} if plant.multi else {}),
        "tech": {"busy": 0, "queue": []},
        "fk": {"busy": 0},
        "events": [],
        "totals": {"launched": 0, "scrap": 0, "good": 0, "out": 0, "shipped": 0, "received": 0},
    }


# --- Décisions des joueurs (appelées par les handlers du moteur sur un état déjà copié) ----------------------------


def launch_of(plant: Plant, fs: dict[str, Any], line_id: str, lots: int) -> str:
    """Ordre de fabrication de `lots` lots sur une ligne ; les OF d'une ligne passent dans l'ordre de lancement."""
    if line_id not in plant.line_ids or lots < 1:
        raise ValueError("Ligne inconnue ou nombre de lots invalide")
    fs["ids"]["of"] += 1
    of_id = f"of{fs['ids']['of']}"
    fs["ofs"].append(
        {"id": of_id, "line_id": line_id, "quantity": lots * plant.lot_size, "lots": lots, "kitted": 0, "out": 0,
         "good": 0, "status": "attente"}
    )  # fmt: skip
    return of_id


def order_mp(
    plant: Plant,
    fs: dict[str, Any],
    offer: dict[str, Any],
    pallets: int,
    cost_index: float = 1.0,
    day: int | None = None,
) -> str:
    """Commande d'achat d'un camion de `pallets` palettes ; livrée `lead_time` jours ouvrés plus tard (si le fournisseur
    est à l'heure : fiabilité de l'offre). La matière est payée à la réception (palettes acceptées), au prix de la
    commande : `cost_index` fige la hausse de coût en vigueur ce jour-là. `day` : jour de la commande (défaut : début
    du tour)."""
    day = fs["day"] if day is None else day
    if pallets < offer["min_order"] or offer["component_id"] not in plant.p_of_comp:
        raise ValueError("Commande inférieure au minimum du fournisseur ou matière inconnue")
    fs["ids"]["po"] += 1
    po_id = f"po{fs['ids']['po']}"
    fs["pending"].append(
        {"id": po_id, "offer_id": offer["id"], "component_id": offer["component_id"], "pallets": pallets,
         "ordered_day": day, "due_day": day + offer["lead_time"], "reliability": offer["reliability"],
         "unit_cost": offer["unit_cost"], "unit_price": round(offer["unit_cost"] * cost_index, 4),
         "eta_day": None, "eta_min": None}
    )  # fmt: skip
    return po_id


# --- Formules attendues (annexe §2) -------------------------------------------------------------------------------


def break_share(plant: Plant) -> float:
    return sum(d for _, d in plant.breaks) / plant.mpd


def trs_factors(plant: Plant, line: int, mtbf_factor: float = 1.0) -> dict[str, float]:
    """Disponibilité, performance et qualité attendues d'une ligne, mesurées sur son goulot (le TRS est leur produit).
    Disponibilité = part du temps hors pauses x marche entre arrêts propres x MTBF / (MTBF + trajet + MTTR)."""
    b = plant.machines[plant.bottleneck[line]]
    own = b["run_min"] / (b["run_min"] + b["stop_min"]) if b["stop_min"] > 0 else 1.0
    mtbf_h = b["mtbf_h"] * mtbf_factor
    repair = mtbf_h / (mtbf_h + plant.lg["repair_travel_min"] / 60 + b["mttr_h"])
    quality = math.prod(1 - plant.machines[i]["defect_rate"] for i in plant.line_machines[line])
    return {"disponibilite": (1 - break_share(plant)) * own * repair, "performance": 1.0, "qualite": quality}


def theoretical_h(plant: Plant, line: int) -> float:
    return 60 / plant.machines[plant.bottleneck[line]]["cycle_min"]


def expected_h(plant: Plant, line: int, mtbf_factor: float = 1.0) -> float:
    """Bons par heure attendus : 60 / cycle du goulot x disponibilité x rendement cumulé de la ligne (annexe §2)."""
    f = trs_factors(plant, line, mtbf_factor)
    return theoretical_h(plant, line) * f["disponibilite"] * f["qualite"]


# --- Simulation d'un tour -----------------------------------------------------------------------------------------


class _M:
    """Une machine pendant un tour (les constantes viennent de la spec, le reste de l'état)."""

    __slots__ = (
        "i", "id", "line", "is_first", "is_last", "cycle", "setup", "defect", "transfer", "scale", "shape", "mttr",
        "run_min", "stop_min", "cur", "phase", "rem_setup", "rem_cycle", "seg", "gen", "ostop", "down", "age", "hazard",
        "rsince", "last_lot", "fail_t", "wake", "st", "st_t", "bk", "produced", "defects", "failures", "rng", "drng",
    )  # fmt: skip


class _Sim:
    def __init__(
        self, plant: Plant, fs: dict[str, Any], week: int, effects: dict[str, float], auto: dict[str, Any] | None = None
    ) -> None:
        P = self.P = plant
        self.fs = fs
        self.auto = auto or {}
        first = self.auto.get("order") or {}  # une règle d'achat, ou une liste (une par matière : budget commun)
        self.budget = (first[0] if isinstance(first, list) else first).get("budget", 0.0)
        self.week = week
        self.effects = effects
        self.T = float(P.T)
        self.now = 0.0
        self.in_break = False
        self.mtbf_factor = effects.get("mtbf", 1.0)
        self.h: list[tuple[Any, ...]] = []
        for dt, prio, seq, kind, a, b in fs["events"]:
            self.h.append((dt, prio, seq, kind, a, b))
        heapq.heapify(self.h)
        self.seq = fs["seq"]
        self.events: list[list[Any]] = []
        self.astate: dict[str, tuple[Any, ...]] = {}
        # calendrier des pauses (un jour de plus que le tour : une tâche de fin de tour peut le déborder)
        self.cal = [(d * P.mpd + s, d * P.mpd + s + dur) for d in range(P.days + 1) for s, dur in P.breaks]
        self.cal_e = [e for _, e in self.cal]
        self.slots = self.cal[: P.days * len(P.breaks)]
        settings = fs["settings"]
        self.settings = settings
        # tables d'attente : tampon avant le goulot
        self.cap = [m["buffer"] for m in P.machines]
        self.relieved: set[int] = set()
        self.slot_owner: dict[int, int] = {}
        for ln, lid in enumerate(P.line_ids):
            mode = settings["protect"].get(lid, "aucune")
            b = P.bottleneck[ln]
            if mode == "tampon_avant" and b != P.first[ln]:
                self.cap[b - 1] = max(self.cap[b - 1], P.protect)
            elif mode == "releve_pauses":
                self.relieved.add(b)
        self.M: list[_M] = []
        for i, (mc, ms) in enumerate(zip(P.machines, fs["machines"], strict=True)):
            m = _M()
            m.i, m.id, m.line = i, mc["id"], P.line_of[i]
            m.is_first, m.is_last = P.first[m.line] == i, P.last[m.line] == i
            m.cycle, m.setup, m.defect, m.transfer = (
                mc["cycle_min"],
                mc["setup_min"],
                mc["defect_rate"],
                mc["transfer_min"],
            )
            m.scale, m.shape, m.mttr = P.scale[i], mc["weibull_shape"], mc["mttr_h"] * 60
            m.run_min, m.stop_min = mc["run_min"], mc["stop_min"]
            for key in ("cur", "phase", "rem_setup", "rem_cycle", "seg", "gen", "ostop", "down", "age", "hazard",
                        "rsince", "last_lot", "fail_t", "wake"):  # fmt: skip
                setattr(m, key, ms[key])
            m.bk, m.produced, m.defects, m.failures = [0.0] * 7, 0, 0, 0
            m.rng = _rng(P, "panne", week, mc["id"])  # seuils de panne
            m.drng = _rng(P, "defaut", week, mc["id"])  # défauts : indépendants des pannes (pilote et passif appariés)
            m.st, m.st_t = ARRET, 0.0
            self.M.append(m)
        self.tables = [deque((r, c) for r, c in t) for t in fs["tables"]]
        self.pools = [deque([lot, n] for lot, n in pool) for pool in fs["pools"]]
        self.pool_n = [sum(n for _, n in pool) for pool in self.pools]
        self.ofd = {of["id"]: of for of in fs["ofs"]}
        self.ofq = [
            deque(of for of in fs["ofs"] if of["line_id"] == lid and of["kitted"] < of["lots"]) for lid in P.line_ids
        ]
        self.lots_left = [sum(of["lots"] - of["kitted"] for of in q) for q in self.ofq]
        self.inline = [sum(len(self.tables[i]) + (self.M[i].cur is not None) for i in ms) for ms in P.line_machines]
        self.lot_of = {int(k): v for k, v in fs["lot_of"].items()}
        self.lot_left = {int(k): v for k, v in fs["lot_left"].items()}
        mp = fs["mp"]
        by = mp.get("by") or {k: [mp[k]] for k in ("units", "staged", "quarantine", "reserved")}  # par matière
        self.mp, self.staged, self.quar, self.res = by["units"], by["staged"], by["quarantine"], by["reserved"]
        self.inflight = fs["inflight"]
        self.starve = fs["starve"]
        self.pending = fs["pending"]
        self.receiving = fs["receiving"]
        self.dock_busy, self.dock_q = fs["dock"]["busy"], fs["dock"]["queue"]
        self.insp_busy, self.insp_q = fs["insp"]["busy"], deque(tuple(x) for x in fs["insp"]["queue"])
        self.orders = fs["orders"]
        self.loading = fs["loading"]
        self.pf = fs["pf"].get("by") or [fs["pf"]["units"]]
        self.qc_busy, self.qc_wake = fs["qc"]["busy"], fs["qc"]["wake"]
        pk = fs["pack"]
        self.conf, self.pk_busy, self.pk_cases, self.pk_units, self.pk_wait = (
            pk.get("by_conf") or [pk["conf"]], pk["busy"], pk["cases"], pk["units"], pk["wait"],
        )  # fmt: skip
        self.pk_p = pk.get("p")  # produit de la palette en cours d'emballage (None : palette vide)
        self.tech_busy, self.repair_q = fs["tech"]["busy"], [tuple(x) for x in fs["tech"]["queue"]]
        self.fk_busy, self.transit = fs["fk"]["busy"], fs["fk"].get("transit", 0)
        self.totals = fs["totals"]
        # compteurs du tour
        self.out = [0] * P.nl
        self.good = [0] * P.nl
        self.scrap = [0] * P.nl
        self.entered = [0] * P.nl
        self.kits = [0] * P.nl
        self.starve_min = [0.0] * P.nl
        self.starve_days: set[tuple[int, int]] = set()
        self.scrap_turn = self.shipped_turn = 0
        self.consumed = 0
        self.shipped_p = [0] * P.np
        self.received = {"trucks": 0, "pallets": 0, "accepted": 0, "quarantined": 0, "wait_min": 0.0}
        self.tech_stats = {"repairs": 0, "wait_min": 0.0, "waited": 0, "busy_min": 0.0}
        self.prev_done: list[str] = []
        self.prev_skipped: list[str] = []
        self.costs = {"repair": 0.0, "preventive": 0.0, "mp": 0.0}
        if P.spares:
            self.sp = fs["spares"]
            self.sp_last = 0.0
            self.sp_area = dict.fromkeys(P.types, 0.0)  # stock x minutes, par type
            self.sp_stat = {"used": 0, "missing": 0, "wait_min": 0.0, "bought": 0, "purchase": 0.0}
        self.dock_stats = {"wait_min": 0.0, "busy_min": 0.0}
        self.fk_busy_min = 0.0
        self.relief_min = 0.0
        self.frames: list[list[Any]] = []
        self.qc_count = 0
        self.packed = {"cases": 0, "pallets": 0}
        self.packed_p = [0] * P.np
        self.not_last = [i for i in range(P.n) if i not in P.last]
        self.disp = {
            "mdone": self._mdone, "mfail": self._mfail, "msetup": self._msetup, "mostop": self._mostop,
            "moresume": self._moresume, "mwake": self._mwake, "bs": self._bs, "be": self._be, "day": self._day,
            "auto": self._auto, "pick": self._pick, "truck": self._truck, "unl": self._unl, "insp": self._insp,
            "kit": self._kit, "qc": self._qc, "qcw": self._qcw, "case": self._case, "wrap": self._wrap,
            "pdel": self._pdel, "fkfree": self._fkfree, "load": self._load, "rstart": self._rstart, "rep": self._rep,
            "prv": self._prv, "frame": self._frame, "spare": self._spare,
        }  # fmt: skip

    # -- mécanique ---------------------------------------------------------------------------------------------------

    def _push(self, t: float, kind: str, a: Any = 0, b: Any = 0, prio: int = 0) -> None:
        heapq.heappush(self.h, (t, prio, self.seq, kind, a, b))
        self.seq += 1

    def _work_end(self, t: float, dur: float) -> float:
        """Fin d'une tâche de poste de `dur` minutes de travail commencée à t : le travail saute les pauses."""
        cal = self.cal
        for k in range(bisect.bisect_right(self.cal_e, t), len(cal)):
            s, e = cal[k]
            if t >= s:
                t = e
            elif t + dur <= s:
                break
            else:
                dur -= s - t
                t = e
        return t + dur

    def _ev(self, now: float, kind: str, subject: str, **data: Any) -> None:
        self.events.append([round(now, 2), kind, subject, data])

    def _agent(self, now: float, agent: str, state: str, at: str | None, until: float | None = None) -> None:
        if agent in self.P.agents and self.astate.get(agent) != (state, at):
            self.astate[agent] = (state, at)
            self._ev(now, "agent", agent, state=state, at=at, until=None if until is None else round(until, 2))

    def _vis(self, m: _M) -> int:
        if m.down == 1:
            return PANNE
        if m.down == 2:
            return PAUSE if self.in_break else ARRET
        if (self.in_break and m.i not in self.relieved) or m.ostop:
            return PAUSE
        if m.phase == SETUP:
            return REGLAGE
        if m.phase == RUN:
            return MARCHE
        if m.phase == BLOCKED:
            return PLEINE
        ln = m.line
        return ATTENTE if self.lots_left[ln] or self.pool_n[ln] or self.inline[ln] else ARRET

    def _refresh(self, m: _M, now: float) -> None:
        s = self._vis(m)
        if s != m.st:
            m.bk[m.st] += now - m.st_t
            m.st, m.st_t = s, now

    # -- machines ----------------------------------------------------------------------------------------------------

    def _fail_age(self, m: _M) -> float:
        return m.scale * self.mtbf_factor * m.hazard ** (1 / m.shape)

    def _accrue(self, m: _M, now: float) -> None:
        """Arrête la progression en cours (pause, panne, préventif) et compte le travail fait."""
        if m.seg is None:
            return
        el = now - m.seg
        m.seg = None
        m.gen += 1
        if m.phase == SETUP:
            m.rem_setup = max(0.0, m.rem_setup - el)
        elif m.phase == RUN:
            m.rem_cycle = max(0.0, m.rem_cycle - el)
            m.age += el
            m.rsince += el

    def _try(self, m: _M, now: float) -> None:
        if m.down or m.ostop or m.seg is not None or m.phase == BLOCKED or (m.i not in self.relieved and self.in_break):
            return
        if m.cur is None:
            code = self._pull(m, now)
            if code is None:
                self._refresh(m, now)
                return
            lot = code >> 1
            m.cur = code
            m.rem_cycle = m.cycle
            m.rem_setup = m.setup if m.setup > 0 and lot != m.last_lot else 0.0
            m.last_lot = lot
            if m.rem_setup:
                self._ev(now, "reglage", m.id, duration_min=round(m.rem_setup, 2))
        m.seg = now
        if m.rem_setup > 1e-9:
            m.phase = SETUP
            self._push(now + m.rem_setup, "msetup", m.i, m.gen)
        else:
            m.rem_setup = 0.0
            self._cycle(m, now)
        self._refresh(m, now)

    def _cycle(self, m: _M, now: float) -> None:
        m.phase = RUN
        c = m.rem_cycle
        fail_in = self._fail_age(m) - m.age
        ostop_in = m.run_min - m.rsince if m.stop_min > 0 else INF
        if fail_in < c and fail_in <= ostop_in:
            self._push(now + max(fail_in, 0.0), "mfail", m.i, m.gen)
        elif ostop_in < c:
            self._push(now + max(ostop_in, 0.0), "mostop", m.i, m.gen)
        else:
            self._push(now + c, "mdone", m.i, m.gen)

    def _pull(self, m: _M, now: float) -> int | None:
        ln = m.line
        if m.is_first:
            pool = self.pools[ln]
            if not pool:
                return None
            head = pool[0]
            code = head[0] << 1
            head[1] -= 1
            if not head[1]:
                pool.popleft()
            self.pool_n[ln] -= 1
            self.inline[ln] += 1
            self.entered[ln] += 1
            if len(pool) < 2 and not self.inflight[ln] and self.lots_left[ln]:
                self._kit_try(now)  # le lot d'avance est entamé : le chariot prépare le suivant
            return code
        tbl = self.tables[m.i - 1]
        if not tbl:
            return None
        ready, code = tbl[0]
        if ready > now:
            if m.wake is None or ready < m.wake:
                m.wake = ready
                self._push(ready, "mwake", m.i)
            return None
        tbl.popleft()
        up = self.M[m.i - 1]
        if up.phase == BLOCKED:
            self._unblock(up, now)
        return code

    def _unblock(self, up: _M, now: float) -> None:
        self._place(up, up.cur, now, notify=False)  # type: ignore[arg-type]
        self._refresh(up, now)
        self._try(up, now)

    def _place(self, m: _M, code: int, now: float, notify: bool = True) -> None:
        """Le produit fini quitte la machine pour sa table de sortie (il y arrive après le temps de transfert)."""
        self.tables[m.i].append((now + m.transfer, code))
        m.cur = None
        m.phase = IDLE
        if m.is_last:
            self._exit(m, code, now)
            if notify:
                self._qc_try(now)
        elif notify:
            self._try(self.M[m.i + 1], now)

    def _exit(self, m: _M, code: int, now: float) -> None:
        lot, ln = code >> 1, m.line
        self.out[ln] += 1
        self.totals["out"] += 1
        of = self.ofd[self.lot_of[lot]]
        of["out"] += 1
        left = self.lot_left[lot] - 1
        if left:
            self.lot_left[lot] = left
        else:
            del self.lot_left[lot]
            self._ev(now, "lot_termine", of["id"], line_id=of["line_id"], quantity=self.P.lot_size)
        if of["out"] == of["quantity"]:
            of["status"] = "termine"

    def _mdone(self, now: float, i: int, gen: int) -> None:
        m = self.M[i]
        if gen != m.gen:
            return
        m.age += m.rem_cycle
        m.rsince += m.rem_cycle
        m.rem_cycle = 0.0
        m.seg = None
        m.gen += 1
        code = m.cur
        if m.drng.random() < m.defect:
            code |= 1  # type: ignore[operator]
            m.defects += 1
        m.produced += 1
        if len(self.tables[i]) >= self.cap[i]:
            m.cur, m.phase = code, BLOCKED
            self._refresh(m, now)
            return
        self._place(m, code, now)  # type: ignore[arg-type]
        self._try(m, now)

    def _msetup(self, now: float, i: int, gen: int) -> None:
        m = self.M[i]
        if gen != m.gen:
            return
        m.rem_setup = 0.0
        m.seg = now
        m.gen += 1
        self._cycle(m, now)
        self._refresh(m, now)

    def _mfail(self, now: float, i: int, gen: int) -> None:
        m = self.M[i]
        if gen != m.gen:
            return
        delta = max(self._fail_age(m) - m.age, 0.0)
        m.age += delta
        m.rsince += delta
        m.rem_cycle = max(m.rem_cycle - delta, 0.0)
        m.seg = None
        m.gen += 1
        m.down, m.fail_t = 1, now
        m.failures += 1
        self._ev(now, "panne", m.id, duration_min=round(m.mttr, 2))
        self.repair_q.append((now, i))
        self._refresh(m, now)
        self._tech_try(now)

    def _mostop(self, now: float, i: int, gen: int) -> None:
        m = self.M[i]
        if gen != m.gen:
            return
        self._accrue(m, now)
        m.rsince = 0.0
        m.ostop = True
        self._push(now + m.stop_min, "moresume", i)
        self._refresh(m, now)

    def _moresume(self, now: float, i: int, _: Any) -> None:
        m = self.M[i]
        m.ostop = False
        self._try(m, now)

    def _mwake(self, now: float, i: int, _: Any) -> None:
        m = self.M[i]
        m.wake = None
        self._try(m, now)

    # -- pauses et préventif -----------------------------------------------------------------------------------------

    def _bs(self, now: float, s: int, _: Any) -> None:
        self.in_break = True
        for m in self.M:
            if m.i not in self.relieved:
                self._accrue(m, now)
                self._refresh(m, now)
        for b in self.relieved:
            self._agent(now, "agent_production", "occupe", self.M[b].id, self.slots[s][1])
        self._slot(now, s)

    def _be(self, now: float, s: int, _: Any) -> None:
        self.in_break = False
        if self.relieved:
            self.relief_min += len(self.relieved) * (self.slots[s][1] - self.slots[s][0])
            self._agent(now, "agent_production", "disponible", "production")
        for m in self.M:
            self._refresh(m, now)
            self._try(m, now)

    def _slot(self, now: float, s: int) -> None:
        """Début d'une pause : le préventif prévu pour ce créneau démarre si le technicien est libre."""
        mi = self.slot_owner.pop(s, None)
        if mi is None:
            return
        m, P = self.M[mi], self.P
        if self.tech_busy >= P.rs["technicians"] or m.down:
            later = next((k for k in range(s + 1, len(self.slots)) if k not in self.slot_owner), None)
            if later is None:
                self.prev_skipped.append(m.id)
            else:
                self.slot_owner[later] = mi
            return
        self._accrue(m, now)
        m.down = 2
        self.tech_busy += 1
        dur = P.lg["preventive_min"]
        self._agent(now, "agent_maintenance", "occupe", m.id, now + dur)
        self._push(now + dur, "prv", mi)
        self._refresh(m, now)

    def _prv(self, now: float, mi: int, _: Any) -> None:
        m, P = self.M[mi], self.P
        m.down, m.age, m.hazard = 0, 0.0, _hazard(m.rng)
        self.tech_busy -= 1
        dur = P.lg["preventive_min"]
        self.tech_stats["busy_min"] += dur
        self.costs["preventive"] += P.costs["preventive_per_intervention"]
        self.prev_done.append(m.id)
        self._ev(now, "preventif", m.id, by="agent_maintenance", duration_min=round(dur, 2))
        self._refresh(m, now)
        self._try(m, now)
        self._tech_try(now)

    # -- réparations -------------------------------------------------------------------------------------------------

    def _tech_try(self, now: float) -> None:
        P = self.P
        while self.tech_busy < P.rs["technicians"] and self.repair_q:
            if self.settings["priority"] == "goulot":
                k = next((k for k, (_, i) in enumerate(self.repair_q) if i in P.bottleneck), 0)
            else:
                k = 0
            t0, i = self.repair_q.pop(k)
            m = self.M[i]
            self.tech_busy += 1
            travel = P.walk_t
            self.tech_stats["wait_min"] += now - t0
            self.tech_stats["waited"] += now > t0 + 1e-9
            self._agent(now, "agent_maintenance", "deplacement", m.id, now + travel)
            self._push(now + travel, "rstart", i)

    def _rstart(self, now: float, i: int, _: Any) -> None:
        m = self.M[i]
        if self.P.spares and not self._take_spare(now, i):
            return
        self._ev(now, "reparation_debut", m.id, by="agent_maintenance")
        self._agent(now, "agent_maintenance", "occupe", m.id, now + m.mttr)
        self._push(now + m.mttr, "rep", i)

    # -- pièces de rechange ------------------------------------------------------------------------------------------

    def _sp_acc(self, now: float) -> None:
        """Cumule stock x durée jusqu'à now (avant tout changement de stock) : base du coût de possession."""
        dt = now - self.sp_last
        for t, n in self.sp["stock"].items():
            self.sp_area[t] += n * dt
        self.sp_last = now

    def _sp_order(self, now: float, t: str) -> None:
        """Commande jusqu'à la cible (stock + en route - machines en attente) ; livraison à l'ouverture du
        `lead_days`-ième jour suivant (lead_days = 1 : la prochaine ouverture)."""
        sp, cfg = self.sp, self.P.spares
        while sp["stock"][t] + sp["transit"][t] - len(sp["waiting"][t]) < sp["target"][t]:
            sp["transit"][t] += 1
            self.sp_stat["bought"] += 1
            self.sp_stat["purchase"] += cfg["price"]
            self._push((now // self.P.mpd + cfg["lead_days"]) * self.P.mpd, "spare", t)

    def _take_spare(self, now: float, i: int) -> bool:
        """Début de réparation : True si la pièce est là ; sinon la machine attend, le technicien est libéré."""
        P, sp, t = self.P, self.sp, self.P.mtype[i]
        if i in sp["reserved"]:
            sp["reserved"].remove(i)
        elif sp["stock"][t] > 0:
            self._sp_acc(now)
            sp["stock"][t] -= 1
            self._sp_order(now, t)  # pièce utilisée = pièce recommandée (règle maintenance.pieces)
        else:
            self.sp_stat["missing"] += 1
            sp["waiting"][t].append([now, i])
            self._sp_order(now, t)
            k = len(sp["waiting"][t]) - 1  # la k-ième machine attend la k-ième livraison en route
            due = sorted(e[0] for e in self.h if e[3] == "spare" and e[4] == t)[k]
            self._ev(now, "attente_piece", self.M[i].id, duration_min=round(due - now, 2))
            self.tech_busy -= 1
            self.tech_stats["busy_min"] += P.walk_t
            self._agent(now, "agent_maintenance", "disponible", "maintenance")
            self._tech_try(now)
            return False
        self.sp_stat["used"] += 1
        return True

    def _spare(self, now: float, t: str, _: Any) -> None:
        sp = self.sp
        sp["transit"][t] -= 1
        if sp["waiting"][t]:  # la pièce va à la première machine en attente ; le technicien revient (trajet + MTTR)
            t0, i = sp["waiting"][t].pop(0)
            self.sp_stat["wait_min"] += now - t0
            sp["reserved"].append(i)
            self.repair_q.append((now, i))
            self._tech_try(now)
        else:
            self._sp_acc(now)
            sp["stock"][t] += 1

    def _sp_week(self) -> None:
        """Début de semaine : cible du pilote (S*) ou du joueur, puis commande jusqu'à la cible."""
        P, sp = self.P, self.sp
        sp["target"] = spares_target(P, self.settings.get("spares"))
        for t in P.types:
            self._sp_order(0.0, t)

    def _rep(self, now: float, i: int, _: Any) -> None:
        m, P = self.M[i], self.P
        self._ev(now, "reparation_fin", m.id, by="agent_maintenance")
        m.down, m.age, m.hazard, m.fail_t = 0, 0.0, _hazard(m.rng), None
        self.tech_busy -= 1
        self.tech_stats["repairs"] += 1
        self.tech_stats["busy_min"] += m.mttr + P.walk_t
        self.costs["repair"] += m.mttr / 60 * P.costs["repair_per_h"] + P.costs.get("damage_per_failure", 0.0)
        self._agent(now, "agent_maintenance", "disponible", "maintenance")
        self._refresh(m, now)
        self._try(m, now)
        self._tech_try(now)

    # -- kits : matière d'un lot, du stock à la tête de ligne --------------------------------------------------------

    def _kit_try(self, now: float) -> None:
        """Le chariot prépare le kit de la ligne la moins approvisionnée (un lot d'avance au plus par ligne)."""
        P = self.P
        while self.fk_busy < P.rs["forklifts"]:
            wanting = [
                ln for ln in range(P.nl) if not self.inflight[ln] and len(self.pools[ln]) < 2 and self.lots_left[ln]
            ]
            if not wanting:
                return
            ready = []
            for ln in wanting:
                p = P.line_prod[ln]
                if self.mp[p] - self.res[p] >= P.needs[p]:
                    ready.append(ln)
                elif not self.pools[ln] and self.starve[ln] is None:  # pas assez de matière : la ligne s'arrête
                    self.starve[ln] = now
            if not ready:
                return
            ln = min(ready, key=lambda x: (len(self.pools[x]), x))
            if self.starve[ln] is not None:
                self._close_starve(ln, now)
            of = self.ofq[ln][0]
            of["kitted"] += 1
            self.lots_left[ln] -= 1
            if of["kitted"] == of["lots"]:
                self.ofq[ln].popleft()
            if of["status"] == "attente":
                of["status"] = "en_cours"
                self._ev(now, "of_lance", of["id"], line_id=of["line_id"], quantity=of["quantity"])
            self.fs["ids"]["lot"] += 1
            lot = self.fs["ids"]["lot"]
            self.lot_of[lot], self.lot_left[lot] = of["id"], P.lot_size
            self.res[P.line_prod[ln]] += P.needs[P.line_prod[ln]]
            self.inflight[ln] += 1
            self.fk_busy += 1
            end = self._work_end(now, P.lg["kit_min"])
            self.fk_busy_min += end - now + 2 * P.kit_t
            self._agent(now, "agent_stock_mp", "occupe", "stock_mp", end)
            self._push(end + P.kit_t, "kit", ln, lot)  # remis à la ligne à 8 + t ; chariot libre à 8 + 2t (_fkfree)

    def _close_starve(self, ln: int, now: float) -> None:
        t0 = self.starve[ln]
        self.starve[ln] = None
        self.starve_min[ln] += now - max(t0, 0.0)
        d0, d1 = int(max(t0, 0.0) // self.P.mpd), int(now // self.P.mpd)
        self.starve_days.update((ln, d) for d in range(d0, d1 + 1) if d < self.P.days)

    def _kit(self, now: float, ln: int, lot: int) -> None:
        P = self.P
        if P.kit_t:
            self._push(now + P.kit_t, "fkfree")  # retour à vide
        else:
            self.fk_busy -= 1
        self.inflight[ln] -= 1
        p = P.line_prod[ln]
        self.mp[p] -= P.needs[p]
        self.res[p] -= P.needs[p]
        self.consumed += P.needs[p]
        self.kits[ln] += 1
        self.pools[ln].append([lot, P.lot_size])
        self.pool_n[ln] += P.lot_size
        self.totals["launched"] += P.lot_size
        self._ev(now, "kit_livre", self.lot_of[lot], line_id=P.line_ids[ln], quantity=P.needs[p])
        if not self.fk_busy:
            self._agent(now, "agent_stock_mp", "disponible", "stock_mp")
        self._flush_staged(now)
        self._kit_try(now)
        self._try(self.M[P.first[ln]], now)

    # -- réception ---------------------------------------------------------------------------------------------------

    def _places(self, p: int) -> int:
        """Places du stock MP si une palette de plus de la matière `p` y entrait (palette = taille de sa matière)."""
        P = self.P
        return sum(-(-(self.mp[q] + (P.upps[q] if q == p else 0)) // P.upps[q]) for q in range(P.np))

    def _flush_staged(self, now: float) -> None:
        P = self.P
        for p in range(P.np):
            while self.staged[p] and self._places(p) <= P.lg["mp_capacity_pallets"]:
                self.staged[p] -= 1
                self.mp[p] += P.upps[p]

    def _dock_take(self, now: float, what: str, key: Any, since: float) -> None:
        """Un camion prend le quai (fournisseur : déchargement ; client : chargement)."""
        P = self.P
        self.dock_busy += 1
        self.dock_stats["wait_min"] += now - since
        self._truck_ev(now, "camion_arrive", what, key)
        if what == "po":
            po = self.receiving[key]
            self.received["wait_min"] += now - since
            end = self._work_end(now, po["pallets"] * P.lg["unload_min_per_pallet"])
            self._agent(now, "chauffeur_fournisseur", "occupe", "quai", end)
            self._agent(now, "agent_reception", "occupe", "reception", end)
            self.dock_stats["busy_min"] += end - now
            self._push(end, "unl", key)
        else:
            info = self.loading[str(key)]  # key : jour, ou « jour-n° du client » pour les clients suivants
            pallets = sum(-(-q // P.pallet_pf) for _, q in info["ship"])
            end = self._work_end(now, pallets * P.lg["load_min_per_pallet"])
            self._agent(now, "chauffeur_client", "occupe", "quai", end)
            self.dock_stats["busy_min"] += end - now
            self._push(end, "load", key)

    def _truck_ev(self, now: float, kind: str, what: str, key: Any) -> None:
        """Le camion entre au quai (arrive) ou le quitte (part) : Godot l'anime 30 min avant et 30 min après."""
        if what == "po":
            site = self.P.offer_site.get(self.receiving[key]["offer_id"])
            subject = key
        else:
            day, k = _split(key)
            site, subject = self.P.clients[k]["site"], f"client-{self.fs['day'] + day}" + (f"-{k}" if k else "")
        if site:
            self._ev(now, kind, subject, site_id=site)

    def _dock_next(self, now: float) -> None:
        while self.dock_busy < self.P.rs["docks"] and self.dock_q:
            what, key, since = self.dock_q.pop(0)
            self._dock_take(now, what, key, since)

    def _truck(self, now: float, po_id: str, _: Any) -> None:
        po = next(p for p in self.pending if p["id"] == po_id)
        self.pending.remove(po)
        self.receiving[po_id] = {**po, "left": po["pallets"], "accepted": 0, "quarantined": 0}
        self.received["trucks"] += 1
        self.received["pallets"] += po["pallets"]
        if self.dock_busy < self.P.rs["docks"]:
            self._dock_take(now, "po", po_id, now)
        else:
            self.dock_q.append(["po", po_id, now])

    def _unl(self, now: float, po_id: str, _: Any) -> None:
        self.dock_busy -= 1
        self._truck_ev(now, "camion_part", "po", po_id)
        self._agent(now, "chauffeur_fournisseur", "disponible", "fournisseur")
        for k in range(self.receiving[po_id]["pallets"]):
            self.insp_q.append((po_id, k))
        self._dock_next(now)
        self._insp_try(now)

    def _insp_try(self, now: float) -> None:
        if self.insp_busy or not self.insp_q:
            return
        po_id, k = self.insp_q.popleft()
        self.insp_busy = True
        self._push(self._work_end(now, self.P.lg["inspect_min_per_pallet"]), "insp", po_id, k)

    def _insp(self, now: float, po_id: str, k: int) -> None:
        P = self.P
        self.insp_busy = False
        po = self.receiving[po_id]
        p = P.p_of_comp[po["component_id"]]
        rate = min(0.5, P.lg["supplier_nonconform_rate"] + self.effects.get("nonconform", 0.0))
        if _rng(P, "fournisseur", po_id, "palette", k).random() < rate:
            po["quarantined"] += P.upps[p]
            self.quar[p] += P.upps[p]
        else:
            po["accepted"] += P.upps[p]
            self.costs["mp"] += P.upps[p] * po.get("unit_price", po["unit_cost"])  # quarantaine : avoir
            if self.staged[p] == 0 and self._places(p) <= P.lg["mp_capacity_pallets"]:
                self.mp[p] += P.upps[p]
            else:
                self.staged[p] += 1
        po["left"] -= 1
        if not po["left"]:
            del self.receiving[po_id]
            self.received["accepted"] += po["accepted"]
            self.received["quarantined"] += po["quarantined"]
            self.totals["received"] += po["accepted"]
            self._ev(now, "livraison_mp", po_id, component_id=po["component_id"], quantity=po["accepted"])
            if po["quarantined"]:
                self._ev(now, "non_conforme", po_id, component_id=po["component_id"], quantity=po["quarantined"])
            self._agent(now, "agent_reception", "disponible", "reception")
        self._kit_try(now)
        self._insp_try(now)

    # -- contrôle, emballage, entrepôt ------------------------------------------------------------------------------

    def _qc_try(self, now: float) -> None:
        if self.qc_busy:
            return
        P = self.P
        best, best_r = -1, INF
        for ln in range(P.nl):
            tbl = self.tables[P.last[ln]]
            if tbl and tbl[0][0] < best_r:
                best, best_r = ln, tbl[0][0]
        if best < 0:
            return
        if best_r > now:
            if self.qc_wake is None or best_r < self.qc_wake:
                self.qc_wake = best_r
                self._push(best_r, "qcw")
            return
        mi = P.last[best]
        _, code = self.tables[mi].popleft()
        self.inline[best] -= 1
        up = self.M[mi]
        if up.phase == BLOCKED:
            self._unblock(up, now)
        self.qc_busy = True
        self._push(self._work_end(now, P.lg["qc_min_per_unit"]), "qc", code, best)

    def _qcw(self, now: float, _a: Any, _b: Any) -> None:
        self.qc_wake = None
        self._qc_try(now)

    def _qc(self, now: float, code: int, ln: int) -> None:
        self.qc_busy = False
        self.qc_count += 1
        if code & 1:
            self.scrap[ln] += 1
            self.scrap_turn += 1
            self.totals["scrap"] += 1
            self._ev(now, "rebut", self.P.line_ids[ln], quantity=1)
        else:
            self.good[ln] += 1
            self.totals["good"] += 1
            self.ofd[self.lot_of[code >> 1]]["good"] += 1
            self.conf[self.P.line_prod[ln]] += 1
            self._pack_try(now)
        self._qc_try(now)

    def _pack_try(self, now: float) -> None:
        if self.pk_busy or self.pk_wait:
            return
        lg = self.P.lg
        if self.pk_cases == lg["cases_per_pallet"]:
            self.pk_busy = "wrap"
            self._push(self._work_end(now, lg["wrap_min_per_pallet"]), "wrap")
            return
        p = (
            self.pk_p
        )  # une palette ne porte qu'un produit : palette vide, le plus gros stock contrôlé (puis le premier)
        if p is None:
            p = max(range(self.P.np), key=lambda q: (self.conf[q], -q))
        if self.conf[p] >= lg["units_per_case"]:
            self.pk_p = p
            self.conf[p] -= lg["units_per_case"]
            self.pk_units += lg["units_per_case"]
            self.pk_busy = "case"
            self._push(self._work_end(now, lg["pack_min_per_case"]), "case")

    def _case(self, now: float, _a: Any, _b: Any) -> None:
        self.pk_busy = None
        self.pk_cases += 1
        self.packed["cases"] += 1
        self._pack_try(now)

    def _wrap(self, now: float, _a: Any, _b: Any) -> None:
        self.pk_busy = None
        self.pk_wait = True
        self._store(now)

    def _store(self, now: float) -> None:
        """La palette filmée entre à l'entrepôt PF s'il y a une place ; sinon l'emballage attend. En campus, le chariot
        la porte : place réservée à la prise (palettes en route comprises), livrée à 1 + t, chariot libre à 1 + 2t."""
        P = self.P
        carried = P.pal_h is not None
        if carried and self.fk_busy >= P.rs["forklifts"]:
            return
        places = sum(-(-u // P.pallet_pf) for u in self.pf) + self.transit + 1  # place réservée, palettes en route
        if not self.pk_wait or places > P.lg["pf_capacity_pallets"]:
            return
        p = self.pk_p or 0
        self.pk_wait = False
        self.pk_units -= P.pallet_pf
        self.pk_cases = 0
        self.pk_p = None
        if carried:
            self.fk_busy += 1
            self.transit += 1
            self.fk_busy_min += P.pal_h + 2 * P.pal_t
            self._push(now + P.pal_h + P.pal_t, "pdel", p)
            self._push(now + P.pal_h + 2 * P.pal_t, "fkfree")
        else:
            self._arrive(now, p)
        self._pack_try(now)

    def _arrive(self, now: float, p: int) -> None:
        self.pf[p] += self.P.pallet_pf
        self.packed["pallets"] += 1
        self.packed_p[p] += 1
        self._ev(now, "palette", "pf", quantity=self.P.pallet_pf, **self._who(p))

    def _who(self, p: int, client: dict[str, Any] | None = None) -> dict[str, Any]:
        """Champs de produit (et de client) ajoutés aux événements d'une partie à plusieurs produits ou clients."""
        if not self.P.multi:
            return {}
        return {"product_id": self.P.pids[p]} | ({"client_id": client["id"]} if client else {})

    def _pdel(self, now: float, p: int, _b: Any) -> None:
        self.transit -= 1
        self._arrive(now, p)

    def _fkfree(self, now: float, _a: Any, _b: Any) -> None:
        self.fk_busy -= 1
        if not self.fk_busy:
            self._agent(now, "agent_stock_mp", "disponible", "stock_mp")
        self._store(now)  # une palette en attente avant les kits
        self._kit_try(now)

    # -- client ------------------------------------------------------------------------------------------------------

    def _day(self, now: float, day: int, _: Any) -> None:
        P = self.P
        for k, cl in enumerate(P.clients):
            rng = _rng(P, "demande", day) if cl["id"] == "c1" else _rng(P, "demande", day, cl["id"])
            base = cl["demand_per_day"] / cl["orders_per_day"] * self.effects.get("demand", 1.0)
            for _k in range(cl["orders_per_day"]):
                self.fs["ids"]["co"] += 1
                q = max(1, round(base * (1 + cl["variability"] * (2 * rng.random() - 1))))
                order = {"id": f"c{self.fs['ids']['co']}", "quantity": q, "day": day,
                         "due_day": day + cl["promised_days"], "shipped_day": None, "status": "ouverte",
                         "on_time": None}  # fmt: skip
                if P.multi:
                    order |= {"client_id": cl["id"], "product_id": P.pids[cl["p"]]}
                self.orders.append(order)
                self._ev(now, "commande_client", order["id"], quantity=q, due_day=order["due_day"],
                         **self._who(cl["p"], cl))  # fmt: skip
            lo, hi = cl["pickup_window_min"]
            self._push(now + lo + rng.random() * (hi - lo), "pick", day, k)

    def _pick(self, now: float, day: int, k: int) -> None:
        """Le camion du client arrive : il emporte, dans l'ordre, les commandes que le stock PF couvre en entier."""
        P, cl = self.P, self.P.clients[k]
        key = day if k == 0 else f"{day}-{k}"
        stock, ship = self.pf[cl["p"]], []
        for o in self.orders:
            if o["shipped_day"] is None and o.get("client_id", cl["id"]) == cl["id"] and o["quantity"] <= stock:
                ship.append([o["id"], o["quantity"]])
                stock -= o["quantity"]
        if not ship:
            return
        self.loading[str(key)] = {"ship": ship}
        if self.dock_busy < P.rs["docks"]:
            self._dock_take(now, "pick", key, now)
        else:
            self.dock_q.append(["pick", key, now])

    def _load(self, now: float, key: Any, _: Any) -> None:
        P = self.P
        self.dock_busy -= 1
        self._truck_ev(now, "camion_part", "pick", key)
        info = self.loading.pop(str(key))
        cl = P.clients[_split(key)[1]]
        today = self.fs["day"] + int(now // P.mpd)
        by_id = {o["id"]: o for o in self.orders}
        for oid, q in info["ship"]:
            o = by_id[oid]
            self.pf[cl["p"]] -= q
            self.shipped_p[cl["p"]] += q
            self.shipped_turn += q
            self.totals["shipped"] += q
            o["shipped_day"], o["status"], o["on_time"] = today, "livree", today <= o["due_day"]
            self._ev(now, "expedition", oid, quantity=q, on_time=o["on_time"], **self._who(cl["p"], cl))
        self._agent(now, "chauffeur_client", "disponible", "client")
        self._store(now)
        self._dock_next(now)

    # -- instantanés -------------------------------------------------------------------------------------------------

    def _counters(self) -> list[int]:
        tables = self.tables
        en_cours, control = sum(self.pool_n), self.qc_busy
        for i in self.not_last:
            en_cours += len(tables[i])
        for i in self.P.last:
            control += len(tables[i])
        for m in self.M:
            if m.cur is not None:
                en_cours += 1
        return [
            sum(self.mp),
            en_cours,
            control,
            sum(self.conf),
            0,
            self.scrap_turn,
            self.pk_units,
            sum(self.pf),
            self.shipped_turn,
        ]

    def _frame(self, now: float, k: int, _: Any) -> None:
        self.frames.append(
            [round(now, 2), [self._vis(m) for m in self.M], [len(t) for t in self.tables], self._counters()]
        )
        if k + 1 < len(self.ftimes):
            self._push(self.ftimes[k + 1], "frame", k + 1, 0, FRAME_PRIO)

    # -- tour --------------------------------------------------------------------------------------------------------

    def _schedule_truck(self, po: dict[str, Any]) -> None:
        """Date d'arrivée du camion (tirée une seule fois) ; il est posé dans ce tour s'il arrive avant sa fin."""
        P, day0 = self.P, self.fs["day"]
        if po["eta_day"] is None and po["due_day"] < day0 + P.days:
            rng = _rng(P, "fournisseur", po["id"])
            delay_risk = self.effects.get("delay_risk", 0.0)
            late = rng.random() >= po["reliability"] / 100 * (1 - delay_risk)
            lo, hi = P.lg["delivery_window_min"]
            po["eta_day"] = po["due_day"] + (SUPPLIER_LATE_DAYS if late else 0)
            po["eta_min"] = lo + rng.random() * (hi - lo)
        if po["eta_day"] is not None and po["eta_day"] < day0 + P.days:
            self._push((po["eta_day"] - day0) * P.mpd + po["eta_min"], "truck", po["id"], 0)

    def _auto(self, now: float, d: int, _: Any) -> None:
        """Décision quotidienne du pilote : la matière d'abord (l'OF compte sur elle), puis les OF."""
        P, fs = self.P, self.fs
        orders = self.auto.get("order") or []
        for order in orders if isinstance(orders, list) else [orders]:
            offer = order["offer"]
            p = P.p_of_comp[offer["component_id"]]
            on_order = sum(po["pallets"] for po in self.pending if po["component_id"] == offer["component_id"])
            position = -(-self.mp[p] // P.upps[p]) + self.staged[p] + on_order  # en palettes
            while position <= order["reorder"]:
                held = sum(-(-self.mp[q] // P.upps[q]) + self.staged[q] for q in range(P.np))
                free = P.lg["mp_capacity_pallets"] - (held + sum(po["pallets"] for po in self.pending))
                pallets = min(order["truck"], free)
                if pallets < offer["min_order"]:
                    break
                price = pallets * P.upps[p] * offer["unit_cost"] * order["cost_index"]
                if price > self.budget:
                    break
                self.budget -= price
                order_mp(P, fs, offer, pallets, order["cost_index"], fs["day"] + d)
                self._schedule_truck(fs["pending"][-1])
                position += pallets
        launch = self.auto.get("launch")
        if launch:
            yields, launched = launch["yields"], False
            for p in range(P.np):  # le stock PF se tient produit par produit
                lines = [ln for ln in range(P.nl) if P.line_prod[ln] == p]
                good_wip = sum((of["quantity"] - of["out"]) * yields[of["line_id"]]
                               for of in fs["ofs"] if P.prod_of_line[of["line_id"]] == p)  # fmt: skip
                pid = P.pids[p]
                open_orders = sum(
                    o["quantity"]
                    for o in self.orders
                    if o["shipped_day"] is None and o.get("product_id", P.pids[0]) == pid
                )
                packing = self.pk_units if (self.pk_p or 0) == p else 0
                need = P.pf_min - (self.pf[p] + good_wip + self.conf[p] + packing - open_orders)
                if need > 0:
                    need = max(need, launch.get("pf_max", P.pf_min) - (P.pf_min - need))  # campagne : jusqu'à pf_max
                    mean_yield = sum(yields[P.line_ids[ln]] for ln in lines) / len(lines)
                    lots = math.ceil(need / (P.lot_size * mean_yield))
                    for ln in lines:
                        share = min(40, math.ceil(lots / len(lines)))
                        if share > 0:
                            launch_of(P, fs, P.line_ids[ln], share)
                            of = fs["ofs"][-1]
                            self.ofd[of["id"]] = of
                            self.ofq[ln].append(of)
                            self.lots_left[ln] += of["lots"]
                    launched = True
            if launched:
                self._kit_try(now)

    def run(self) -> None:
        P, fs = self.P, self.fs
        day0 = fs["day"]
        # pauses
        for s, (b, e) in enumerate(self.slots):
            self._push(b, "bs", s)
            self._push(e, "be", s)
        # jours : commandes du client
        for d in range(P.days):
            self._push(d * P.mpd, "day", day0 + d)
            if self.auto:  # pilote automatique : une décision par jour, une fois les commandes du client arrivées
                self._push(d * P.mpd, "auto", d, 0, AUTO_PRIO)
        # camions des commandes d'achat qui tombent dans ce tour
        for po in self.pending:
            self._schedule_truck(po)
        # préventif : une intervention par machine ciblée, dans l'ordre des créneaux (les plus longs d'abord)
        targets, others = [], []
        for ln, lid in enumerate(P.line_ids):
            mode = self.settings["preventive"].get(lid, "aucune")
            if mode != "aucune":
                targets.append(P.bottleneck[ln])
                if mode == "toutes":
                    others += [i for i in P.line_machines[ln] if i != P.bottleneck[ln]]
        targets += others
        order = sorted(range(len(self.slots)), key=lambda s: (-(self.slots[s][1] - self.slots[s][0]), self.slots[s][0]))
        self.slot_owner = dict(zip(order, targets, strict=False))
        self.prev_skipped += [self.M[i].id for i in targets[len(order) :]]
        self.ftimes = frame_times(P.days, P.mpd, P.frame_min)
        self._push(0.0, "frame", 0, 0, FRAME_PRIO)
        # reprise : tout ce qui peut démarrer démarre
        self._kit_try(0.0)
        for m in self.M:
            self._try(m, 0.0)
        self._qc_try(0.0)
        self._pack_try(0.0)
        self._insp_try(0.0)
        self._tech_try(0.0)
        self._store(0.0)
        if P.spares:
            self._sp_week()
        h, T, disp = self.h, self.T, self.disp
        while h and h[0][0] <= T:
            t, _, _, kind, a, b = heapq.heappop(h)
            self.now = t
            disp[kind](t, a, b)

    def dump(self) -> dict[str, Any]:
        P, fs, T = self.P, self.fs, self.T
        for m in self.M:  # dernière tranche de temps de chaque machine
            m.bk[m.st] += T - m.st_t
        for ln in range(P.nl):
            if self.starve[ln] is not None:
                self._close_starve(ln, T)
                self.starve[ln] = 0.0  # le manque continue au tour suivant (date relative)
        if P.spares:
            self._sp_acc(T)
            self.sp_stat["holding"] = P.hold_rate * P.spares["price"] * sum(self.sp_area.values()) / T
            self.costs["spares"] = self.sp_stat["purchase"] + self.sp_stat["holding"]
            fs["spares"]["waiting"] = {t: [[t0 - T, i] for t0, i in w] for t, w in self.sp["waiting"].items()}
        fs["day"] += P.days
        fs["seq"] = self.seq
        fs["events"] = [
            [t - T, prio, seq, kind, a, b]
            for t, prio, seq, kind, a, b in self.h
            if t > T and (kind not in SPAN_KINDS or b == self.M[a].gen)
        ]
        for m, ms in zip(self.M, fs["machines"], strict=True):
            for key in ("cur", "phase", "rem_setup", "rem_cycle", "gen", "ostop", "down", "age", "hazard", "rsince",
                        "last_lot"):  # fmt: skip
                ms[key] = getattr(m, key)
            ms["seg"] = None if m.seg is None else m.seg - T
            ms["fail_t"] = None if m.fail_t is None else m.fail_t - T
            ms["wake"] = None if m.wake is None else m.wake - T
        fs["tables"] = [[[r - T, c] for r, c in t] for t in self.tables]
        fs["pools"] = [[list(x) for x in p] for p in self.pools]
        keep_lots = sorted(self.lot_of)[-KEPT_LOTS:]
        fs["lot_of"] = {str(k): self.lot_of[k] for k in keep_lots}
        fs["lot_left"] = {str(k): v for k, v in self.lot_left.items()}
        fs["mp"] = {"units": sum(self.mp), "staged": sum(self.staged), "quarantine": sum(self.quar),
                    "reserved": sum(self.res)}  # fmt: skip
        if P.multi:
            fs["mp"]["by"] = {"units": self.mp, "staged": self.staged, "quarantine": self.quar, "reserved": self.res}
        fs["dock"] = {"busy": self.dock_busy, "queue": [[w, k, s - T] for w, k, s in self.dock_q]}
        fs["insp"] = {"busy": self.insp_busy, "queue": [list(x) for x in self.insp_q]}
        fs["pf"] = {"units": sum(self.pf)} | ({"by": self.pf} if P.multi else {})
        fs["qc"] = {"busy": self.qc_busy, "wake": None if self.qc_wake is None else self.qc_wake - T}
        fs["pack"] = {"conf": sum(self.conf), "busy": self.pk_busy, "cases": self.pk_cases, "units": self.pk_units,
                      "wait": self.pk_wait}  # fmt: skip
        if P.multi:
            fs["pack"] |= {"by_conf": self.conf, "p": self.pk_p}
        fs["tech"] = {"busy": self.tech_busy, "queue": [[t - T, i] for t, i in self.repair_q]}
        fs["fk"] = {"busy": self.fk_busy, "transit": self.transit} if P.pal_h is not None else {"busy": self.fk_busy}
        # commandes : statut du jour, puis on ne garde que les ouvertes et les dernières closes
        today = fs["day"]
        day0_ = today - P.days
        for o in self.orders:
            if o["shipped_day"] is None and o["due_day"] < today:
                o["status"] = "en_retard"
        due = [o for o in self.orders if day0_ <= o["due_day"] < today]
        self.otif = {"due": len(due), "on_time": sum(1 for o in due if o["on_time"])}
        self.due_p = [[0, 0] for _ in range(P.np)]  # [dues, à l'heure] par produit
        for o in due:
            row = self.due_p[P.pids.index(o.get("product_id", P.pids[0]))]
            row[0] += 1
            row[1] += bool(o["on_time"])
        closed = [o for o in self.orders if o["shipped_day"] is not None]
        fs["orders"] = [o for o in self.orders if o["shipped_day"] is None] + closed[-KEPT_ORDERS:]
        done = [of for of in fs["ofs"] if of["status"] == "termine"]
        fs["ofs"] = [of for of in fs["ofs"] if of["status"] != "termine"] + done[-KEPT_ORDERS:]
        return fs

    def timeline(self, week: int) -> dict[str, Any]:
        P = self.P
        return {
            "week": week, "days": P.days, "minutes_per_day": P.mpd, "day_start_h": P.start_h,
            "frame_min": P.frame_min, "states": list(STATES), "machines": list(P.mids), "counters": list(COUNTERS),
            "frames": self.frames, "events": self.events,
        }  # fmt: skip

    def report(self, day0: int) -> dict[str, Any]:
        P = self.P
        due, on_time = self.otif["due"], self.otif["on_time"]
        report = {
            "minutes": P.T,
            "day": day0,
            "lines": {
                lid: {"out": self.out[ln], "good": self.good[ln], "scrap": self.scrap[ln], "entered": self.entered[ln],
                      "kits": self.kits[ln], "stockout_min": round(self.starve_min[ln], 2),
                      "stockout_days": len({d for ll, d in self.starve_days if ll == ln}),
                      "expected_h": expected_h(P, ln), "theoretical_h": theoretical_h(P, ln)}
                for ln, lid in enumerate(P.line_ids)
            },
            "machines": {
                m.id: {"produced": m.produced, "defects": m.defects, "failures": m.failures,
                       "minutes": {STATES[s]: round(v, 2) for s, v in enumerate(m.bk)}, "age_min": round(m.age, 2)}
                for m in self.M
            },
            "orders": {"due": due, "on_time": on_time, "late": due - on_time,
                       "otif": 100 * on_time / due if due else None},
            "reception": self.received,
            "technician": self.tech_stats,
            "preventive": {"done": self.prev_done, "skipped": self.prev_skipped},
            "dock": self.dock_stats,
            "forklift_busy_min": round(self.fk_busy_min, 2),
            "relief_min": self.relief_min,
            "consumed_mp": self.consumed,
            "controlled": self.qc_count,
            "packed": self.packed,
            "shipped": self.shipped_turn,
            "costs": self.costs,
        }  # fmt: skip
        if P.spares:
            report["spares"] = {k: self.fs["spares"][k] for k in ("stock", "transit", "target")} | {
                k: round(v, 2) if isinstance(v, float) else v for k, v in self.sp_stat.items()
            }
        if P.multi:  # partie à un produit et un client : rapport inchangé (référence de la tranche T4b)
            report["by_product"] = [  # palettes emballées, unités expédiées, commandes échues et à l'heure du tour
                {"product_id": pid, "shipped": self.shipped_p[p], "pallets": self.packed_p[p],
                 "due": self.due_p[p][0], "on_time": self.due_p[p][1]}
                for p, pid in enumerate(P.pids)
            ]  # fmt: skip
        return report


def simulate(
    plant: Plant,
    fs: dict[str, Any],
    week: int,
    effects: dict[str, float] | None = None,
    auto: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Joue un tour : (nouvel état, chronologie, rapport). L'état d'entrée n'est pas modifié ; le hasard ne dépend
    que de la graine, du numéro de semaine et de l'état. `auto` : règles du pilote automatique, appliquées chaque
    jour simulé (`order` : offre, point de commande en palettes, camion, budget ; `launch` : rendements par ligne)."""
    sim = _Sim(plant, copy.deepcopy(fs), week, effects or {}, auto)
    day0 = sim.fs["day"]
    sim.run()
    new = sim.dump()
    return new, sim.timeline(week), sim.report(day0)
